[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/sqlbot?utm_medium=integration&utm_source=button&utm_campaign=sqlbot)

# SQLBot on Railway

One-click [SQLBot](https://github.com/dataease/SQLBot) (text-to-SQL chat over your databases, by the DataEase team) for Railway.

- **Version:** SQLBot 1.10.3, from the official image `dataease/sqlbot:v1.10.3@sha256:ff9012a95e6ac0e7921aa74e96c73de33550af61615fe850edb27b322c342288`
- **Services:** `SQLBot` (this repo, public, health check `/healthz`, volume `/opt/sqlbot/data`) and `Postgres` (Railway PostgreSQL with pgvector)
- **RAM:** runs in 0.5 GB (about 360 MB in use). The optional local embedding model (RAG) needs about 1.5 GB in total and switches itself off below that.

## What this repo changes

- **Smaller image.** Upstream's image is 4.6 GB, above Railway's 4 GB cap on the Free and Trial plans. The Dockerfile removes the bundled PostgreSQL server, the unused ONNX copy of the embedding model, compilers and dev tools, then flattens the image to about 3.6 GB.
- **External database.** SQLBot uses the Railway Postgres service instead of the PostgreSQL that upstream bundles in the app container.
- **No default password.** Upstream's first migration creates `admin` with the password `SQLBot@123456`. `railway/railway_init.py` replaces it with the generated `ADMIN_PASSWORD` on first boot. A password you change later in the UI is left alone.
- **Your model, ready to use.** `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` become the default AI model ("Default LLM"). SQLBot encrypts the key in its database.
- **One port.** The web app, the API, the MCP server (`/mcp`, SSE) and chart pictures (`/images/`) are served together on `$PORT`.
- **Locked down.** `/api/v1/mcp/mcp_assistant`, an upstream endpoint that needs no login and spends the default LLM, returns 403.
- **Restarts on failure.** Setup errors exit non-zero, so Railway's restart policy applies. Migrations run under a PostgreSQL advisory lock.

## Variables (SQLBot service)

| Variable | Default | Notes |
|---|---|---|
| `LLM_API_KEY` | *(you enter it)* | API key for OpenAI or any OpenAI-compatible endpoint |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL (DeepSeek, DashScope, OpenRouter, vLLM, Ollama…) |
| `LLM_MODEL` | `gpt-4.1-mini` | Model name sent to that endpoint |
| `ADMIN_PASSWORD` | generated | Password of the `admin` account |
| `SECRET_KEY` | generated | Signs login tokens |
| `POSTGRES_*` | references to `Postgres` | Database connection |
| `PORT` | `8000` | Port SQLBot listens on |

Optional, add them yourself: `EMBEDDING_ENABLED=true` and `TABLE_EMBEDDING_ENABLED=true` (local RAG, needs about 1.5 GB RAM), `LOG_LEVEL`, and the other settings in upstream's [`config.py`](https://github.com/dataease/SQLBot/blob/v1.10.3/backend/common/core/config.py).

## After deploy

1. Open the public domain and sign in as `admin` with `ADMIN_PASSWORD`.
2. Add a datasource (use a read-only database user), choose the tables and ask a question.
3. MCP clients: `{"mcpServers": {"sqlbot": {"url": "https://YOUR-DOMAIN/mcp"}}}`. Call `mcp_start` with your SQLBot username and password, then `mcp_question`.

## Updates

Railway offers deployers an update when this repo's `main` changes. Each version is listed in [CHANGELOG.md](CHANGELOG.md), breaking changes first. Your data stays in the Postgres service and the volume.

## Licence

SQLBot is licensed by FIT2CLOUD under GPLv3 with extra conditions (keep the logo and copyright in the UI); see [upstream's LICENSE](https://github.com/dataease/SQLBot/blob/v1.10.3/LICENSE). This wrapper keeps the UI unchanged.
