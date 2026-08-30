# Stack

Six vendored LangFuse v4 services plus one of ours.

```bash
cp .env.example .env      # then fill in every blank with: openssl rand -hex 32
./scripts/stack.sh up
./scripts/stack.sh ps
```

LangFuse UI: <http://localhost:3000>. The `LANGFUSE_INIT_*` values in `.env` seed the org,
project, user and API keys on first boot, so there is no click-through.

| Service | Host port | Owner | Note |
|---|---|---|---|
| `langfuse-web` | 3000 | LangFuse | UI + API |
| `langfuse-worker` | 3030 | LangFuse | async ingestion |
| `clickhouse` | 8123, 9000 | LangFuse | trace OLAP store |
| `minio` | 9090, 9091 | LangFuse | S3-compatible blob store |
| `redis` | **6380** | LangFuse | remapped — host `redis-server` owns 6379 |
| `postgres` | **5434** | LangFuse | remapped — host PostgreSQL 16 owns 5432 |
| `checkpointer-postgres` | **5433** | ours | LangGraph checkpointer |

`docker-compose.yml` is vendored verbatim from upstream — **do not edit it**. Every local
change belongs in `docker-compose.override.yml`, which uses the `!override` YAML tag to
*replace* upstream's `ports` lists rather than concatenate with them.

Always start the stack via `scripts/stack.sh`. Running `docker compose -f
docker/docker-compose.yml up` on its own reinstates upstream's 5432/6379 bindings and fails.

See `DECISIONS.md` ADR-003, ADR-004, ADR-006, ADR-007.
