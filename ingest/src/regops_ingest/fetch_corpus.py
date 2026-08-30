"""Fetch the MAS regulatory corpus into a gitignored `corpus/`, emitting a committed manifest.

Design notes that matter downstream:

* **`doc_id` is derived from the canonical URL, never the file bytes.** Re-running after MAS
  reissues a PDF must update the same logical document rather than mint a second one, so Day 3
  re-ingestion is idempotent. Byte-derived IDs would fork on every amendment.
* **The manifest is the committed artifact; the PDFs are not.** They are third-party documents
  and large. `sha256` in the manifest is what makes a re-fetch verifiable.
* **Politeness is not optional on a government site.** MAS publishes `Crawl-delay: 2`; that is
  the default here, robots.txt is parsed and enforced, and the User-Agent identifies the
  project rather than impersonating a browser.
* **Resumable.** Re-running skips documents already downloaded with a matching manifest entry,
  so an interrupted crawl costs only what it had not yet fetched.

Usage:
    uv run python -m regops_ingest.fetch_corpus --limit 5 --dry-run
    uv run python -m regops_ingest.fetch_corpus --sections notices guidelines
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.robotparser
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from selectolax.parser import HTMLParser

BASE = "https://www.mas.gov.sg"
SITEMAP = f"{BASE}/sitemap.xml"
ISSUER = "MAS"

# The `Mozilla/5.0 (compatible; <product>; +<url>)` form is the long-standing convention for
# well-behaved crawlers (Googlebot and bingbot use it). It is required here, not cosmetic: MAS's
# WAF serves an HTML "Maintenance" page — HTTP 200, no XML — to any User-Agent that does not
# begin with `Mozilla/5.0`, which looks like an empty sitemap rather than a refusal. The product
# token and contact URL keep the crawler identifiable; do not reduce this to a bare browser
# string, and do not drop the prefix.
USER_AGENT = (
    "Mozilla/5.0 (compatible; regops-corpus/0.1; +https://github.com/msubash26/compliance-copilot)"
)

# MAS document types worth separating. The Day 5 finding depends on being able to slice
# retrieval quality by document type, and these three genuinely differ in shape: notices are
# prescriptive and clause-numbered, guidelines are advisory prose, circulars are short and
# operational.
SECTIONS: dict[str, str] = {
    "notices": "/regulation/notices/",
    "guidelines": "/regulation/guidelines/",
    "circulars": "/regulation/circulars/",
    "consultations": "/publications/consultations/",
}

DEFAULT_SECTIONS = ("notices", "guidelines")
DEFAULT_DELAY = 2.0  # MAS robots.txt: Crawl-delay: 2


@dataclass(frozen=True)
class Document:
    doc_id: str
    url: str
    source_page: str
    issuer: str
    doc_type: str
    title: str
    filename: str
    sha256: str
    bytes: int
    fetched_at: str


def canonical(url: str) -> str:
    """Normalise a URL so the same document yields the same doc_id across runs.

    Drops the query string and fragment, lowercases the host, and strips a trailing slash.
    MAS serves the same asset under varying cache-busting query strings.
    """
    parts = urlparse(url)
    path = parts.path.rstrip("/") or "/"
    return urlunparse((parts.scheme.lower(), parts.netloc.lower(), path, "", "", ""))


def make_doc_id(url: str) -> str:
    return hashlib.sha256(canonical(url).encode()).hexdigest()[:16]


def slugify(url: str) -> str:
    """Filesystem-safe basename, truncated but keeping the extension.

    MAS uses very long descriptive filenames; a naive truncation drops the `.pdf` suffix, and
    Day 3's parser dispatches on it.
    """
    path = Path(urlparse(url).path)
    suffix = path.suffix if len(path.suffix) <= 8 else ""
    stem = re.sub(r"[^A-Za-z0-9._-]", "-", path.stem or "document")
    return stem[: 120 - len(suffix)] + suffix


class Crawler:
    def __init__(self, client: httpx.Client, delay: float) -> None:
        self.client = client
        self.delay = delay
        self._last = 0.0
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots.set_url(f"{BASE}/robots.txt")
        try:
            self.robots.read()
        except Exception as exc:  # noqa: BLE001 - a missing robots.txt must not be fatal
            print(f"warning: could not read robots.txt ({exc}); proceeding at {delay}s delay")

    def allowed(self, url: str) -> bool:
        try:
            return self.robots.can_fetch(USER_AGENT, url)
        except Exception:  # noqa: BLE001
            return True

    def get(self, url: str) -> httpx.Response | None:
        """One rate-limited GET. Returns None on any non-fatal failure."""
        if not self.allowed(url):
            print(f"  skip (robots.txt disallows): {url}")
            return None
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        try:
            response = self.client.get(url)
        except httpx.HTTPError as exc:
            print(f"  error {type(exc).__name__}: {url}")
            return None
        if response.status_code != 200:
            print(f"  http {response.status_code}: {url}")
            return None
        return response


def sitemap_urls(crawler: Crawler, sections: tuple[str, ...]) -> dict[str, list[str]]:
    response = crawler.get(SITEMAP)
    if response is None:
        sys.exit("error: could not fetch the sitemap")
    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    out: dict[str, list[str]] = {}
    for section in sections:
        prefix = SECTIONS[section]
        index = f"{BASE}{prefix}".rstrip("/")
        pages = sorted({u for u in locs if prefix in u and u.rstrip("/") != index})
        out[section] = pages
    return out


def extract_pdfs(html: str, page_url: str) -> tuple[str, list[str]]:
    """Return (page title, absolute PDF URLs) for one landing page."""
    tree = HTMLParser(html)
    node = tree.css_first("title")
    title = (node.text() if node else "").strip()
    hrefs = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href") or ""
        if ".pdf" in href.lower():
            hrefs.append(urljoin(page_url, href))
    # Preserve first-seen order; MAS lists the current version before historical ones.
    seen: set[str] = set()
    ordered = []
    for h in hrefs:
        key = canonical(h)
        if key not in seen:
            seen.add(key)
            ordered.append(h)
    return title, ordered


def load_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    entries = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            entries[row["doc_id"]] = row
    return entries


def write_manifest(path: Path, entries: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries.values(), key=lambda r: (r["doc_type"], r["url"]))
    with path.open("w") as fh:
        for row in ordered:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def harvest(
    crawler: Crawler,
    pages: dict[str, list[str]],
    per_page: int,
    limit: int | None,
) -> Iterator[tuple[str, str, str, str]]:
    """Yield (doc_type, source_page, title, pdf_url)."""
    count = 0
    for doc_type, urls in pages.items():
        for page_url in urls:
            if limit is not None and count >= limit:
                return
            response = crawler.get(page_url)
            if response is None:
                continue
            title, pdfs = extract_pdfs(response.text, page_url)
            if not pdfs:
                continue
            for pdf_url in pdfs[:per_page]:
                yield doc_type, page_url, title, pdf_url
            count += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sections", nargs="+", choices=sorted(SECTIONS), default=list(DEFAULT_SECTIONS)
    )
    parser.add_argument("--out", type=Path, default=Path("corpus"))
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY, help="seconds between requests"
    )
    parser.add_argument("--limit", type=int, default=None, help="max landing pages to visit")
    parser.add_argument(
        "--per-page",
        type=int,
        default=1,
        help="PDFs per landing page; 1 takes the current version, higher pulls amendment history",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="list what would be fetched, download nothing"
    )
    args = parser.parse_args(argv)

    if args.delay < DEFAULT_DELAY:
        print(f"warning: MAS robots.txt asks for {DEFAULT_DELAY}s; you set {args.delay}s")

    out = args.out
    pdf_dir = out / "mas"
    manifest_path = out / "manifest.jsonl"
    entries = load_manifest(manifest_path)
    print(f"manifest: {len(entries)} existing entries")

    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        crawler = Crawler(client, args.delay)
        pages = sitemap_urls(crawler, tuple(args.sections))
        for section, urls in pages.items():
            print(f"  {section}: {len(urls)} landing pages")

        added = skipped = failed = 0
        harvested = harvest(crawler, pages, args.per_page, args.limit)
        for doc_type, page_url, title, pdf_url in harvested:
            doc_id = make_doc_id(pdf_url)
            target = pdf_dir / f"{doc_id}-{slugify(pdf_url)}"
            if doc_id in entries and target.exists():
                skipped += 1
                continue
            if args.dry_run:
                print(f"  [dry-run] {doc_type:14s} {title[:48]:48s} {pdf_url}")
                added += 1
                continue
            response = crawler.get(pdf_url)
            if response is None:
                failed += 1
                continue
            body = response.content
            if not body.startswith(b"%PDF"):
                print(f"  not a pdf, skipping: {pdf_url}")
                failed += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            entries[doc_id] = asdict(
                Document(
                    doc_id=doc_id,
                    url=canonical(pdf_url),
                    source_page=canonical(page_url),
                    issuer=ISSUER,
                    doc_type=doc_type,
                    title=title,
                    filename=str(target.relative_to(out)),
                    sha256=hashlib.sha256(body).hexdigest(),
                    bytes=len(body),
                    fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
                )
            )
            added += 1
            if added % 10 == 0:
                write_manifest(manifest_path, entries)
                print(f"  ... {added} fetched, {skipped} skipped, {failed} failed")

    if not args.dry_run:
        write_manifest(manifest_path, entries)
    print(f"done: +{added} new, {skipped} already present, {failed} failed → {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
