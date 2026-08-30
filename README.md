# Regulatory Compliance Copilot

RAG + multi-agent system over MAS / SGX regulatory corpora, running fully local on an
RTX 3090 (air-gapped path), with a Bedrock parity path for cost/quality comparison.

**Status:** Day 0 — scaffold.

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
uv run python scripts/hello_trace.py
```
