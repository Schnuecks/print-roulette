FROM python:3.12-alpine
WORKDIR /app
COPY app.py .
COPY static ./static
ENV PORT=8080 MW_LANG=en
EXPOSE 8080
USER nobody
CMD ["python", "-u", "app.py"]
