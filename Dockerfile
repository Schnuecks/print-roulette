# Pinned to the digest of the multi-platform index; Dependabot keeps it current
FROM mirror.gcr.io/library/python:3.15-alpine@sha256:d44b1254cb92329418d164b22b20d86bbd3869d48e80e09e476531a409a728bb
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
