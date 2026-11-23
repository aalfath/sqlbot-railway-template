# Changelog

## 1.10.3 (2026-11-23)

First release of the Railway template.

- SQLBot 1.10.3, official image `dataease/sqlbot:v1.10.3@sha256:ff9012a95e6ac0e7921aa74e96c73de33550af61615fe850edb27b322c342288`, slimmed to fit Railway's 4 GB image cap.
- Uses the Railway Postgres service (pgvector) instead of the PostgreSQL bundled in the upstream container.
- Generated admin password, your OpenAI-compatible model registered on first boot, one port for web, API and MCP, health check `/healthz`.
- `/api/v1/mcp/mcp_assistant` (no login, spends the default LLM) is disabled.
