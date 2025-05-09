# RSS to GoToSocial Poster

This project is a simple Python application that reads an RSS feed and automatically posts new entries to a Mastodon-compatible server (such as GoToSocial). It uses SQLite to keep track of which entries have already been posted.

## Features

- Periodically checks an RSS feed for new entries
- Posts new entries to a Mastodon/GoToSocial account
- Remembers posted entries using a SQLite database
- Runs easily in Docker

## Requirements

- Python 3.11 (or compatible)
- Docker (optional, recommended)
- A Mastodon or GoToSocial account and access token

## Usage

### Environment Variables

Set the following environment variables:

- `FEED_URL` – The URL of the RSS feed to monitor
- `INSTANCE_URL` – The base URL of your Mastodon/GoToSocial instance (e.g., `https://social.example.com`)
- `ACCESS_TOKEN` – Your Mastodon/GoToSocial access token
- `CHECK_INTERVAL` – (Optional) How often to check the feed, in seconds (default: 300)

### Running with Docker

```sh
docker build -t rss-to-gotosocial .
docker run -d \
  -e FEED_URL="https://example.com/rss.xml" \
  -e INSTANCE_URL="https://social.example.com" \
  -e ACCESS_TOKEN="your-access-token" \
  -v $(pwd)/data:/data \
  rss-to-gotosocial
```

### Running with Docker Compose

Create a `docker-compose.yml` file like this:

```yaml
services:
  rss-to-gotosocial:
    image: ghcr.io/maxbengtzen/rss-to-gotosocial:latest
    environment:
      - FEED_URL=https://example.com/rss.xml
      - INSTANCE_URL=https://social.example.com
      - ACCESS_TOKEN=your-access-token
      # - CHECK_INTERVAL=300  # Optional
    volumes:
      - ./data:/data
    restart: unless-stopped
```

Then start the service:

```sh
docker compose up -d
```

### Running Locally

Install dependencies:

```sh
pip install Mastodon.py feedparser
```

Then run:

```sh
python poster.py
```

## Database

The application stores posted entry IDs in a SQLite database at `/data/posted_ids.db`.  
If you use Docker, map a local directory to `/data` to persist the database.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE) license.

---

Feel free to modify this template as needed!