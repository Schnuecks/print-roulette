# Pinned to the digest of the multi-platform index; Dependabot keeps it current
FROM mirror.gcr.io/library/python:3.15-alpine@sha256:d44b1254cb92329418d164b22b20d86bbd3869d48e80e09e476531a409a728bb
WORKDIR /app
COPY app.py .
COPY static ./static
ENV PORT=8080 MW_LANG=en
EXPOSE 8080
USER nobody
CMD ["python", "-u", "app.py"]
