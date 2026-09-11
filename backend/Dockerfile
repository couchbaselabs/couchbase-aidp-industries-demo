# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

WORKDIR /app

# Corporate-proxy CA trust bootstrap (see ../scripts/setup-corporate-ca.sh
# and the reference Couchbase Agent Operations Manager repo's Dockerfiles,
# which this is copied from almost verbatim): append the corporate CA onto
# the trust bundle already baked into the base image *before* touching the
# network, since apt/pip's own HTTPS fetch can fail behind a TLS-inspecting
# proxy the same way it does everywhere else. Harmless no-op when
# certs/corporate-ca.crt is the empty placeholder this repo ships with.
COPY certs/ /usr/local/share/ca-certificates/extra/
RUN if find /usr/local/share/ca-certificates/extra -name '*.crt' 2>/dev/null | grep -q .; then \
      cat /usr/local/share/ca-certificates/extra/*.crt >> /etc/ssl/certs/ca-certificates.crt && \
      apt-get update && \
      apt-get install -y --no-install-recommends ca-certificates && \
      update-ca-certificates && \
      rm -rf /var/lib/apt/lists/*; \
    fi
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=100 --retries 5 -r requirements.txt

# The vendored aom_sdk package (see vendor/aom-sdk/VENDORED.md) — installed
# as a normal pip package so app/aom_gateway.py's `from aom_sdk import
# AOMClient` works exactly as it would against a real pip install.
COPY vendor/aom-sdk ./vendor/aom-sdk
RUN pip install ./vendor/aom-sdk

COPY app ./app

RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --home-dir /home/appuser --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 4100

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=20 \
    CMD curl -fs http://localhost:4100/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4100"]
