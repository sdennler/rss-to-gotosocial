import argparse
import os
import time
import logging
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from feedparser import parse
from getpass import getpass
from mastodon import Mastodon
from bs4 import BeautifulSoup
from pprint import pprint


def get_args():
    parser = argparse.ArgumentParser(description='Manage RSS feeds for cross-posting')

    parser.add_argument('--db', required=True, help='Path to SQLite database')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run', action='store_true', help='Process all feeds')
    group.add_argument('--list', action='store_true', help='List all feeds')
    group.add_argument('--save', action='store_true', help='Save a new feed')

    # Feed parameters for save
    parser.add_argument('--feed-id', type=int, help='Feed ID for updates (mandatory for update)')
    parser.add_argument('--feed-url', help='Feed URL')
    parser.add_argument('--instance-url', help='Instance URL')
    parser.add_argument('--access-token', help='Access token')
    parser.add_argument('--access-token-promt', action='store_true', help='Prompt for access token')
    parser.add_argument('--max-age-days', type=int, help='Maximum post age in days. Default 30')
    parser.add_argument('--toot-format', help='Format string. Default: {title}\\n\\n{link}\\n')

    # Feed parameters for run
    parser.add_argument('--max-posts', type=int, help='Maximum post to post. Default all', default=0)
    parser.add_argument('--dry-posts', action='store_true', help='Dry run. Do not actually post.')

    args = parser.parse_args()

    if args.access_token_promt and args.save:
        args.access_token = getpass('Access token (hidden input): ')

    return args


def init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger

def init_db():
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posted_ids (
            eid TEXT PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY,
            url TEXT,
            instance_url TEXT,
            access_token TEXT,
            max_post_age_days INTEGER,
            toot_format TEXT
        )
    """)
    db.commit()


def print_feed_list():
    for row in db.execute("SELECT * FROM feeds"):
        print(f"ID: {row[0]}, URL: {row[1]}, Instance: {row[2]}, Max Age: {row[4]} days, Toot Format: {row[5]}")

def save_feed(args):
    params = {}
    if args.feed_url: params['url'] = args.feed_url
    if args.instance_url: params['instance_url'] = args.instance_url
    if args.access_token: params['access_token'] = args.access_token
    if args.max_age_days: params['max_post_age_days'] = args.max_age_days
    if args.toot_format: params['toot_format'] = args.toot_format

    c = db.cursor()

    if args.feed_id is None: # Add new feed
        c.execute(
            "INSERT INTO feeds (url, instance_url, access_token, max_post_age_days, toot_format) VALUES (?, ?, ?, ?, ?)",
            (params.get('url'), params.get('instance_url'), params.get('access_token'), params.get('max_post_age_days') or 30, params.get('toot_format') or "{title}\\n\\n{link}\\n")
        )
        db.commit()
        logger.info(f"Added new feed: {c.lastrowid}")
    else: # Update existing feed
        c.execute(
            "UPDATE feeds SET url=COALESCE(?, url), instance_url=COALESCE(?, instance_url), "
            "access_token=COALESCE(?, access_token), max_post_age_days=COALESCE(?, max_post_age_days), toot_format=COALESCE(?, toot_format) "
            "WHERE id=?",
            (params.get('url'), params.get('instance_url'), params.get('access_token'), params.get('max_post_age_days'), params.get('toot_format'), args.feed_id)
        )
        db.commit()
        logger.info(f"Updated feed with ID {args.feed_id}")

def run(args):
    db.row_factory = sqlite3.Row
    c = db.execute("SELECT * FROM feeds")
    for row in c:
        logger.info(f"Running feed: {row['id']}, URL: {row['url']}, Instance: {row['instance_url']}, Max Age: {row['max_post_age_days']} days, Toot Format: {row['toot_format']}")
        mastodon = get_mastodon(row['instance_url'], row['access_token'])
        process_feed(args, mastodon, row['url'], row['max_post_age_days'], row['toot_format'])


def get_mastodon(instance_url, access_token):
    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=instance_url
    )

    me = mastodon.me()
    logger.info("My user ID is %s", me['id'])
    return mastodon


def check_id_posted(id):
    c = db.cursor()
    c.execute("SELECT 1 FROM posted_ids WHERE eid = ?", (id,))
    return c.fetchone() is not None

def save_posted_id(eid):
    c = db.cursor()
    c.execute("INSERT OR IGNORE INTO posted_ids (eid) VALUES (?)", (eid,))
    db.commit()

def get_tag_list(tags):
    tag_string = ""
    for tag in tags:
        processed = tag.term.strip()

        processed = re.sub(r'[\s-]', '_', processed)  # Convert spaces/hyphens
        processed = re.sub(r'[^\w_]', '', processed)  # Remove remaining non-word chars (keeps accents)

        if not processed or processed.isdigit(): # Skip if empty or numeric-only
            continue

        tag_string += f" #{processed}"

    return tag_string

def process_feed(args, mastodon, url, max_age, toot_format):
    logger.info("Checking RSS feed: %s", url)
    feed = parse(url)
    if not feed.entries:
        logger.warning("No entries in RSS feed.")
        return
    feed.entries.reverse()

    count_posted = 0
    for entry in feed.entries:
        published = datetime(*entry.published_parsed[:6])
        if check_id_posted(entry.id):
            logger.info("Already posted from %s (RSS ID %s). Skipping: %s", published, entry.id, entry.title)
        elif published < datetime.now() - timedelta(days=max_age):
            logger.info("Old post from %s (RSS ID %s). Skipping: %s", published, entry.id, entry.title)
        elif args.max_posts == 0 or count_posted < args.max_posts:
            post(args, mastodon, entry, toot_format)
            count_posted += 1

def post(args, mastodon, entry, toot_format):
    summary = BeautifulSoup(entry.summary, features="html.parser").get_text().partition('\n')[0]

    content = toot_format.format(
        title=entry.title,
        link=entry.link,
        summary=summary,
    ).replace('\\n', '\n')
    content += get_tag_list(entry.tags)

    try:
        if not args.dry_posts:
            mastodon.toot(content.strip())
        logger.info("Posted new article: %s", entry.title)
        logger.info(content.strip())
        save_posted_id(entry.id)
    except Exception as e:
        logger.error("Failed to post %s: %s", entry.title, e)


if __name__ == "__main__":
    args = get_args()
    logger = init_logger()
    db = sqlite3.connect(args.db)
    init_db()

    if args.list:
        print_feed_list()
    elif args.save:
        save_feed(args)
    elif args.run:
        run(args)

    db.close()
