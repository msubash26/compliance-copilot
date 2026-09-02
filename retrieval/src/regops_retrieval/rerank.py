"""The cross-encoder, loaded from the stack Docling already put on this box.

`BAAI/bge-reranker-v2-m3` is 568M parameters and 1.33 GB in fp16, measured on
the 3090, 7.2s to load from the HF cache and 138ms p50 to score 20 real clauses.
It runs on `transformers` + `torch` directly -- `AutoModelForSequenceClassification`
with a pair input -- so no `sentence-transformers` and no `FlagEmbedding` enter
the lockfile for it. A reranker is one forward pass over a pair; a library that
wraps that is a dependency bought for an import statement.

The model is imported lazily and the tests never load it. The pipeline contract
-- reorder by score, truncate to `top_n` -- is exercised against a stub, and the
real weights are exercised once in a test marked `slow` and skipped in CI, where
there is no GPU.
"""

from __future__ import annotations

import os

MODEL_ID = "BAAI/bge-reranker-v2-m3"

# Pair truncation. The median clause is 820 characters (~200 tokens) so 512
# covers question + clause for most of the corpus; the tail is what the context
# budget in `context.py` also exists for. Left at the model card's default and
# recorded as untuned (ADR-020).
MAX_LENGTH = 512
BATCH = 16


class CrossEncoder:
    """Scores (question, passage) pairs. Higher is more relevant."""

    def __init__(self, model_id: str = MODEL_ID, device: str | None = None) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id, dtype=self.dtype)
        self.model.to(self.device).eval()

    def score(self, question: str, passages: list[str]) -> list[float]:
        import torch

        if not passages:
            return []
        out: list[float] = []
        with torch.inference_mode():
            for i in range(0, len(passages), BATCH):
                batch = passages[i : i + BATCH]
                enc = self.tok(
                    [question] * len(batch),
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=MAX_LENGTH,
                    return_tensors="pt",
                ).to(self.device)
                logits = self.model(**enc).logits.view(-1).float()
                out += [float(x) for x in logits.cpu()]
        return out


_CACHED: CrossEncoder | None = None


def load(model_id: str = MODEL_ID) -> CrossEncoder:
    """One instance per process: 7.2s of load time and 1.33 GB of VRAM."""
    global _CACHED
    if _CACHED is None or _CACHED.model_id != model_id:
        if os.getenv("REGOPS_NO_RERANKER"):
            raise RuntimeError("REGOPS_NO_RERANKER is set; refusing to load the cross-encoder")
        _CACHED = CrossEncoder(model_id)
    return _CACHED
