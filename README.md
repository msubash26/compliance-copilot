# Regulatory Compliance Copilot

RAG + multi-agent system over MAS / SGX regulatory corpora, running fully local on an
RTX 3090 (air-gapped path), with a Bedrock parity path for cost/quality comparison.

**Status:** Day 0 complete except the corpus (B5). Stack runs locally; first trace is landing in LangFuse.

## Layout

| Package | Role |
|---|---|
| `ingest/` | Parsing, hierarchical chunking, contextual retrieval, corpus manifest |
| `retrieval/` | Hybrid dense + BM25, RRF, cross-encoder rerank, metadata filters |
| `agents/` | LangGraph supervisor, Pydantic AI comparison agent |
| `evals/` | Golden set, retrieval benchmark, agent eval suite |
| `serving/` | vLLM / Ollama serving, model routing, semantic cache |
| `api/` | FastAPI service + thin UI |

The MCP server lives in its own repo: [regdocs-mcp](https://github.com/msubash26/regdocs-mcp),
consumed here as an editable path dependency.

## Quickstart

```bash
uv sync
cp .env.example .env          # fill every blank: openssl rand -hex 32
./scripts/stack.sh up         # LangFuse + ClickHouse + MinIO + Redis + 2x Postgres
uv run python scripts/hello_trace.py
```

LangFuse UI at <http://localhost:3000>. See [docker/README.md](docker/README.md) for the port
map — the host already owns 5432 and 6379, so containers are remapped.
