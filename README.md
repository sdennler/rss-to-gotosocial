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

To add a feed:

```sh
python poster.py --db poster.sqlite --save --feed-url "https://example.com/feed.rss" --instance-url "https://social.example.com" --access-token-promt
```

To process the feed(s):

```sh
python poster.py --db poster.sqlite --run
```

## Database

The application stores posted entry IDs in a SQLite database at the given path.
The access tokens are stored unencrypted. Keep the database save... At least `chmod go-rw poster.sqlite`

## Get access token from GoToSocial
- Create a new Application
  - Any name
  - Redirect URL shown above the form
  - Scopes: read write
- Save and open the Application Details
- Request Access Tocken

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE) license.

---

Feel free to modify this template as needed!
