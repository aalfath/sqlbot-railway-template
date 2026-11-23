# Deploy and Host SQLBot on Railway

SQLBot is an open-source text-to-SQL chat app from the DataEase team. You connect a database, ask questions in plain language, and an LLM writes the SQL, runs it read-only and shows the answer as a table or chart. It supports MySQL, PostgreSQL, SQL Server, ClickHouse, Oracle and more, and includes an MCP server for AI assistants.

## About Hosting SQLBot

This template runs SQLBot 1.10.3 (official image `dataease/sqlbot`, pinned by digest) with a Railway PostgreSQL database, which stores users, datasources, chats and pgvector embeddings. On first boot the start script runs the migrations under a lock, replaces upstream's default admin password with a generated `ADMIN_PASSWORD`, and registers your OpenAI-compatible key as the default AI model. The web app, the API and the MCP server (SSE) share one public port, and uploads and chart pictures live on a volume. The image is built from our GitHub repo, so Railway offers you an update when we bump the version. The first build takes about 5 minutes.

## Common Use Cases

* Let business users ask questions of a production replica or a data warehouse in plain language and get tables and charts back
* Give Claude Desktop, Cursor or another MCP client a tool that answers data questions against your databases
* Build a shared team workspace with curated datasources, business terminology and SQL examples that improve answers

## Dependencies for SQLBot Hosting

* An LLM API key: OpenAI, or any OpenAI-compatible endpoint (DeepSeek, Qwen/DashScope, OpenRouter, a vLLM or Ollama server)
* PostgreSQL with pgvector (included: Railway Postgres)

### Deployment Dependencies

* SQLBot on GitHub: https://github.com/dataease/SQLBot
* SQLBot 1.10.3 release: https://github.com/dataease/SQLBot/releases/tag/v1.10.3
* Template repo: https://github.com/aalfath/sqlbot-railway-template
* OpenAI API keys: https://platform.openai.com/api-keys

### Implementation Details

Services:

* **SQLBot**: web UI, REST API, MCP server at `/mcp` and chart pictures at `/images/`, all on one public domain. Health check: `/healthz`. Volume: `/opt/sqlbot/data` (Excel/CSV uploads, files, chart pictures).
* **Postgres**: SQLBot's own database (Railway PostgreSQL with pgvector), on its own volume.

After deploy:

1. Open the SQLBot domain and sign in as `admin`. The password is the `ADMIN_PASSWORD` variable on the SQLBot service. Change it under your profile if you like.
2. Your model is already set up as "Default LLM" under System settings > AI models. Variables: `LLM_API_KEY` (required), `LLM_BASE_URL` (default `https://api.openai.com/v1`) and `LLM_MODEL` (default `gpt-4.1-mini`). Changing them and redeploying updates that model. Other providers can be added in the UI.
3. Add a datasource (your database or an Excel/CSV upload), pick the tables, and start a chat.

MCP client config (SSE). Then call `mcp_start` with your SQLBot username and password to get a token and a chat id, and `mcp_question` to ask:

```json
{ "mcpServers": { "sqlbot": { "url": "https://YOUR-DOMAIN/mcp" } } }
```

Memory: SQLBot fits Railway's 0.5 GB limit (about 360 MB in use). The optional local embedding model that ranks tables, terminology and SQL examples (RAG) needs about 1 GB more, so the start script turns it off when the service has less than 1.5 GB RAM. With 2 GB or more, set `EMBEDDING_ENABLED=true` and `TABLE_EMBEDDING_ENABLED=true` to use it.

Security: every API route needs a login. Upstream's `/api/v1/mcp/mcp_assistant`, which needs no login, spends the default LLM and fetches a URL the caller supplies, is disabled. SQLBot runs the generated SQL with the credentials you give it, so connect read-only database users.

Updates: when we publish a new SQLBot version, Railway shows an update on your project. `CHANGELOG.md` in the template repo lists the changes, with breaking ones first.

## Why Deploy SQLBot on Railway?

<!-- Recommended: Keep this section as shown below -->
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying SQLBot on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
<!-- End recommended section -->
