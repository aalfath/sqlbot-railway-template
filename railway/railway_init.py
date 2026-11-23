"""First-boot and every-boot setup for SQLBot on Railway.

1. Wait for PostgreSQL.
2. Run SQLBot's migrations under a PostgreSQL advisory lock, so overlapping
   deploys never migrate at the same time.
3. Replace the admin password that upstream's first migration hard-codes
   (SQLBot@123456) with ADMIN_PASSWORD. A password changed later in the UI is
   left alone.
4. Register the deployer's OpenAI-compatible model (LLM_API_KEY, LLM_BASE_URL,
   LLM_MODEL) as the default AI model, and keep it in step with those
   variables. SQLBot encrypts the key in the database when it starts.
Exits non-zero on any failure so Railway restarts the service.
"""
import hashlib
import json
import os
import sys
import time

import psycopg

LOCK_ID = 2993_0001
UPSTREAM_DEFAULT_ADMIN_MD5 = hashlib.md5(b"SQLBot@123456").hexdigest()
MARKER = "/opt/sqlbot/data/.railway-llm.json"


def log(msg):
    print(f"railway-init: {msg}", flush=True)


def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def connect():
    params = dict(
        host=os.environ.get("POSTGRES_SERVER", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "root"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        dbname=os.environ.get("POSTGRES_DB", "sqlbot"),
        connect_timeout=5,
    )
    deadline = time.time() + int(os.environ.get("SQLBOT_DB_WAIT_SECONDS", "180"))
    while True:
        try:
            return psycopg.connect(**params, autocommit=True)
        except psycopg.OperationalError as e:
            if time.time() > deadline:
                log(f"PostgreSQL is not reachable: {e}")
                sys.exit(1)
            log("waiting for PostgreSQL ...")
            time.sleep(3)


def migrate():
    # SQLBot's migrations use pgvector.sqlalchemy without importing it; the app
    # imports it as a side effect of loading its models, so do the same here.
    import pgvector.sqlalchemy  # noqa: F401
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


def secure_admin(cur):
    pwd = os.environ.get("ADMIN_PASSWORD", "")
    if len(pwd) < 8:
        log("ADMIN_PASSWORD must be set (8+ characters); refusing to start with the upstream default password")
        sys.exit(1)
    cur.execute("SELECT password FROM sys_user WHERE id = 1 AND account = 'admin'")
    row = cur.fetchone()
    if row is None:
        return
    weak = {UPSTREAM_DEFAULT_ADMIN_MD5, md5(os.environ.get("DEFAULT_PWD", "SQLBot@123456"))}
    if row[0] in weak and row[0] != md5(pwd):
        cur.execute(
            "UPDATE sys_user SET password = %s, language = 'en' WHERE id = 1 AND account = 'admin'",
            (md5(pwd),),
        )
        log("admin password set from ADMIN_PASSWORD")


def seed_llm(cur):
    key = os.environ.get("LLM_API_KEY", "").strip()
    base = (os.environ.get("LLM_BASE_URL", "").strip() or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "").strip() or "gpt-4.1-mini"
    if not key:
        log("LLM_API_KEY is empty: add a model under System settings > AI models")
        return
    fingerprint = hashlib.sha256(f"{key}\n{base}\n{model}".encode()).hexdigest()
    state = {}
    if os.path.exists(MARKER):
        with open(MARKER) as f:
            state = json.load(f)
    if state.get("fingerprint") == fingerprint:
        return
    config = json.dumps([{"key": "temperature", "val": 0.6, "name": "temperature"}])
    if state.get("model_id"):
        cur.execute(
            "UPDATE ai_model SET api_key = %s, api_domain = %s, base_model = %s WHERE id = %s",
            (key, base, model, state["model_id"]),
        )
        if cur.rowcount == 0:
            log("the model this template added was deleted in the UI; not adding it again")
        else:
            log(f"default AI model updated from the LLM_* variables ({model})")
        model_id = state["model_id"]
    else:
        cur.execute("SELECT count(*) FROM ai_model WHERE default_model")
        has_default = cur.fetchone()[0] > 0
        cur.execute(
            """INSERT INTO ai_model (supplier, name, model_type, base_model, default_model,
                                     api_key, api_domain, protocol, config, status, create_time)
               VALUES (15, %s, 0, %s, %s, %s, %s, 1, %s, 1, %s) RETURNING id""",
            ("Default LLM", model, not has_default, key, base, config, int(time.time() * 1000)),
        )
        model_id = cur.fetchone()[0]
        log(f"AI model 'Default LLM' ({model}) added from the LLM_* variables")
    os.makedirs(os.path.dirname(MARKER), exist_ok=True)
    tmp = MARKER + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"model_id": model_id, "fingerprint": fingerprint}, f)
    os.replace(tmp, MARKER)


def main():
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        try:
            log("running database migrations ...")
            migrate()
            secure_admin(cur)
            seed_llm(cur)
        finally:
            cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    conn.close()
    log("ready")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        log(f"setup failed: {e!r}")
        sys.exit(1)
