import os
import sqlite3
import requests
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime
from joblin import extract_fields

load_dotenv()
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

slack_client = WebClient(token=SLACK_TOKEN)

conn = sqlite3.connect("internships.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS posted (
    id TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("INSERT OR IGNORE INTO meta" +
               "(key, value) VALUES ('last_seen', '0')")
conn.commit()


def get_last_seen():
    cursor.execute("SELECT value FROM meta WHERE key = 'last_seen'")
    return float(cursor.fetchone()[0])


def set_last_seen(timestamp):
    cursor.execute("UPDATE meta SET value = ?" +
                   "WHERE key = 'last_seen'", (str(timestamp),))
    conn.commit()


def fetch_listings():
    url = "https://raw.githubusercontent.com/vanshb03/" + \
          "Summer2026-Internships/dev/.github/scripts/listings.json"
    response = requests.get(url)
    return response.json()


def is_posted(listing_id):
    cursor.execute("SELECT 1 FROM posted WHERE id = ?", (listing_id,))
    return cursor.fetchone() is not None


def mark_posted(listing_id):
    cursor.execute("INSERT INTO posted (id) VALUES (?)", (listing_id,))
    conn.commit()


def format_message(listing):
    extracted = extract_fields(listing["url"])
    field_lines = [
        f"*{key}*: {value}"
        for key, value in extracted.items()
        if value != "N/A"
    ]
    field_info = "\n".join(field_lines)

    return (
        f"*{listing['company_name']}* – {listing['title']}\n"
        f"{', '.join(listing['locations'])} | {listing['season']} Internship\n"
        f"<{listing['url']}|Apply here>\n\n"
        f"{field_info}"
    )


def post_to_slack():
    listings = fetch_listings()
    last_seen = get_last_seen()

    new_listings = [
        item for item in listings
        if item.get("date_updated", 0) > last_seen
        and item.get("active", False)
        and not is_posted(item["id"])
    ]
    new_listings.sort(key=lambda item: item.get("date_updated", 0))

    if not new_listings:
        print("No new listings to post.")
        return

    for listing in new_listings:
        try:
            message = format_message(listing)
            slack_client.chat_postMessage(
                channel=CHANNEL_ID,
                text=message,
                unfurl_links=False,
                unfurl_media=False
            )
            print(f"Posted: {listing['title']}")
            mark_posted(listing["id"])
            set_last_seen(listing["date_updated"])
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")


def run_forever():
    while True:
        print("Checking for new listings at " +
              f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        post_to_slack()
        print("Waiting 5 minutes...\n")
        time.sleep(60 * 5)


if __name__ == "__main__":
    run_forever()
