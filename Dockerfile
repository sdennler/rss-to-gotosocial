FROM python:3.11-slim

RUN pip install --no-cache-dir Mastodon.py feedparser

# Create /data and set permissions
RUN mkdir -p /data && chmod 777 /data

WORKDIR /app
COPY poster.py /app/poster.py

ENTRYPOINT ["python", "/app/poster.py"]
