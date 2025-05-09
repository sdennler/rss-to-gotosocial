import os
import time
import logging
import sqlite3
from feedparser import parse
from mastodon import Mastodon

# --- Configuration via environment variables ---
FEED_URL       = os.environ['FEED_URL']
INSTANCE_URL   = os.environ['INSTANCE_URL']
ACCESS_TOKEN   = os.environ['ACCESS_TOKEN']
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 300))

# --- Initialize logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# --- Initialize Mastodon client ---
mastodon = Mastodon(
    access_token=ACCESS_TOKEN,
    api_base_url=INSTANCE_URL
)

# --- Get own user ID ---
me = mastodon.me()
my_id = me['id']
logger.info("My user ID is %s", my_id)

DB_PATH = "/data/posted_ids.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posted_ids (
            eid TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def load_posted_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT eid FROM posted_ids")
    ids = set(row[0] for row in c.fetchall())
    conn.close()
    return ids

def save_posted_id(eid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO posted_ids (eid) VALUES (?)", (eid,))
    conn.commit()
    conn.close()

def fetch_and_post():
    logger.info("Checking RSS feed: %s", FEED_URL)
    feed = parse(FEED_URL)
    if not feed.entries:
        logger.warning("No entries in RSS feed.")
        return

    newest = feed.entries[0]
    eid    = newest.id

    posted_ids = load_posted_ids()

    if eid in posted_ids:
        logger.info(
            "Already posted (RSS ID %s). Skipping: %s", eid, newest.title
        )
        return

    content = f"{newest.title}\n\n{newest.link}"
    try:
        mastodon.toot(content)
        logger.info("Posted new article: %s", newest.title)
        save_posted_id(eid)
    except Exception as e:
        logger.error("Failed to post %s: %s", newest.title, e)

if __name__ == "__main__":
    init_db()
    while True:
        try:
            fetch_and_post()
        except Exception as e:
            logger.exception("Unexpected error in main loop")
        time.sleep(CHECK_INTERVAL)
