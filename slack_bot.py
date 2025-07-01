import os
import sqlite3
import requests
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime

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

def fetch_listings():
    url = "https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/dev/.github/scripts/listings.json"
    response = requests.get(url)
    return response.json()

def is_posted(listing_id):
    cursor.execute("SELECT 1 FROM posted WHERE id = ?", (listing_id,))
    return cursor.fetchone() is not None

def mark_posted(listing_id):
    cursor.execute("INSERT INTO posted (id) VALUES (?)", (listing_id,))
    conn.commit()

def format_message(listing):
    return (
        f"*{listing['company_name']}* – {listing['title']}\n"
        f"{', '.join(listing['locations'])} | {listing['season']} Internship\n"
        f"<{listing['url']}|Apply here>"
    )

def post_to_slack():
    listings = fetch_listings()
    now = time.time()
    cutoff = now - (60 * 60 * 24) 

    for listing in listings:
        if (
            not listing.get("active", False) or
            is_posted(listing["id"]) or
            listing.get("date_updated", 0) < cutoff
        ):
            continue
        try:
            message = format_message(listing)
            slack_client.chat_postMessage(channel=CHANNEL_ID, text=message)
            print(f"Posted: {listing['title']}")
            mark_posted(listing["id"])
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")

def run_forever():
    while True:
        print(f"🔍 Checking for new listings at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        post_to_slack()
        print("⏳ Waiting 5 minutes...\n")
        time.sleep(60 * 5)

if __name__ == "__main__":
    run_forever()