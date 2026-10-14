# Pinned to the digest of the multi-platform index; Dependabot keeps it current
FROM mirror.gcr.io/library/python:3.15-alpine@sha256:ff4d3c9b1a48f646eedd93182aaea385c7a5452f4c8a8cd7cef686babacf4928
WORKDIR /app
COPY app.py .
COPY static ./static
ENV PORT=8080 MW_LANG=en
EXPOSE 8080
USER nobody
CMD ["python", "-u", "app.py"]
