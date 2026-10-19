# Pinned to the digest of the multi-platform index; Dependabot keeps it current
FROM mirror.gcr.io/library/python:3.15-alpine@sha256:2699b90f4d562a22e2dd076c82f964032f64814204bff36d271a54ba4cc2c7e2
WORKDIR /app
COPY app.py .
COPY static ./static
ENV PORT=8080 MW_LANG=en
EXPOSE 8080
USER nobody
CMD ["python", "-u", "app.py"]
