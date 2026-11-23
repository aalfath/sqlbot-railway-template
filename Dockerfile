# SQLBot for Railway: the official image, slimmed and flattened.
# Upstream image: dataease/sqlbot (Docker Hub), pinned by version and digest.
FROM dataease/sqlbot:v1.10.3@sha256:ff9012a95e6ac0e7921aa74e96c73de33550af61615fe850edb27b322c342288 AS upstream

# The upstream image is 4.6 GB unpacked, above Railway's 4 GB image cap on the
# Free and Trial plans. Remove what SQLBot never uses at runtime when it talks to
# an external PostgreSQL: the bundled PostgreSQL server (and its LLVM JIT), the
# ONNX copy of the embedding model (sentence-transformers loads the PyTorch
# weights), compilers and headers, and dev-only Python tools.
RUN set -eux; \
    rm -r /opt/sqlbot/models/embedding/shibing624_text2vec-base-chinese/onnx \
          /usr/lib/postgresql \
          /usr/lib/x86_64-linux-gnu/libLLVM.so.19.1 \
          /usr/lib/gcc \
          /usr/include \
          /usr/bin/x86_64-linux-gnu-lto-dump-12 \
          /usr/bin/uv /usr/bin/uvx \
          /opt/sqlbot/app/.venv/lib/python3.11/site-packages/torch/include \
          /opt/sqlbot/app/.venv/lib/python3.11/site-packages/torch/test \
          /opt/sqlbot/app/.venv/lib/python3.11/site-packages/mypy \
          /opt/sqlbot/app/.venv/lib/python3.11/site-packages/mypyc \
          /opt/sqlbot/app/.venv/bin/ruff; \
    rm /opt/sqlbot/app/.venv/lib/python3.11/site-packages/*__mypyc.cpython-311-x86_64-linux-gnu.so; \
    rm /usr/local/bin/docker-entrypoint.sh; \
    ln -sf /usr/share/zoneinfo/UTC /etc/localtime; echo UTC > /etc/timezone; \
    mkdir -p /opt/sqlbot/data

COPY railway/ /opt/sqlbot/railway/

# Flatten so the removed files really leave the image.
FROM scratch
COPY --from=upstream / /

ENV PATH=/opt/sqlbot/app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=en_US.utf8 \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    SQLBOT_HOME=/opt/sqlbot \
    PYTHONPATH=/opt/sqlbot/app \
    DB_CLIENT=/opt/sqlbot/db_client \
    DM_HOME=/opt/dmdbms \
    LD_LIBRARY_PATH=/opt/dmdbms/bin:/opt/sqlbot/db_client/oracle_instant_client \
    TOKENIZERS_PARALLELISM=false \
    HF_HUB_OFFLINE=1 \
    PORT=8000

WORKDIR /opt/sqlbot/app
EXPOSE 8000
CMD ["sh", "/opt/sqlbot/railway/start.sh"]
