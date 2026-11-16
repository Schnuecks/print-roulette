# Pinned to the digest of the multi-platform index; Dependabot keeps it current
FROM mirror.gcr.io/library/python:3.15-alpine@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd
# pip is not needed at runtime; its vendored packages (urllib3, msgpack, …) only add findings
RUN python -m pip uninstall -y -q pip && rm -rf /usr/local/lib/python3*/ensurepip
WORKDIR /app
COPY app.py .
COPY static ./static
ENV PORT=8080 MW_LANG=en
EXPOSE 8080
USER nobody
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/healthz', timeout=4)"]
CMD ["python", "-u", "app.py"]
