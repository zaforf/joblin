import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types
import sqlite3

load_dotenv()
GENAI_KEY = os.getenv("GENAI_KEY")
client = genai.Client(api_key=GENAI_KEY)

system_message = """
You are a helpful assistant that extracts information from job descriptions.
"""
extraction_message = """
Given this job description, extract the following fields:
{}
For each field, if it is not present, return "N/A".
Answer each field concisely and clearly, each on a new line.
There should be {} lines in total, with only the value and not the field name.
"""

options = Options()
options.add_argument("--headless")
options.add_argument("user-agent=Mozilla/5.0 (Macintosh;" +
                     " Intel Mac OS X 10_15_7) AppleWebKit/537.36" +
                     " (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)

conn = sqlite3.connect('fields.db')
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_name TEXT UNIQUE
)
""")
default_fields = [
    "Pay",
    "Eligibility (Expected grad date? PhD? etc.)",
    "Dates (When? How long?)",
    "Responsibilities"
]
# Initialize default fields if they don't exist
for field in default_fields:
    cursor.execute("""INSERT OR IGNORE INTO fields
                      (field_name) VALUES (?)""", (field,))


def create_message(default=True):
    # When the bot uses the extractor, fields can't be personalized
    if default:
        fields = default_fields
    else:
        cursor.execute("SELECT field_name FROM fields")
        rows = cursor.fetchall()
        fields = [row[0] for row in rows]

    len_fields = len(fields)
    return extraction_message.format("\n".join(fields), len_fields)


def add_field(field_name):
    cursor.execute("INSERT INTO fields (field_name) VALUES (?)", (field_name,))
    conn.commit()


def get_fields():
    cursor.execute("SELECT id, field_name FROM fields")
    rows = cursor.fetchall()
    return [{"id": row[0], "field_name": row[1]} for row in rows]


def delete_field(field_id):
    cursor.execute("DELETE FROM fields WHERE id = ?", (field_id,))
    conn.commit()


def extract_fields(url, default=True):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listing_text = soup.get_text(separator=' ', strip=True)

    if not listing_text:
        return {"Error!": "We couldn't extract any fields (bot protection?)."}
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=system_message),
        contents=listing_text + "\n" + create_message(default=default)
    )
    extracted_text = response.text.splitlines()
    return_object = {}
    fields = get_fields()

    if len(extracted_text) == 0 or \
       sum(line == "N/A" for line in extracted_text) == len(extracted_text):
        return {"Error!": "We couldn't extract any fields (bot protection?)."}
    for i, field in enumerate(fields):
        field_name = field['field_name'].split(' ')[0]
        if i < len(extracted_text):
            return_object[field_name] = extracted_text[i].strip()
        else:
            return_object[field_name] = "N/A"

    return return_object


if __name__ == "__main__":
    while True:
        print("\n=== Joblin ===")
        print("1. Add field")
        print("2. View saved fields")
        print("3. Delete field")
        print("4. Extract fields from URL")
        print("5. Exit")
        choice = input("Enter your choice (1–5): ").strip()

        if choice == '1':
            field_name = input("Enter field name to add: ").strip()
            add_field(field_name)
            print(f"Field '{field_name}' added.")

        elif choice == '2':
            fields = get_fields()
            print("\nSaved Fields:")
            if fields:
                for field in fields:
                    print(f"  [{field['id']}] {field['field_name']}")
            else:
                print("(No fields saved)")

        elif choice == '3':
            field_id = input("Enter field ID to delete: ").strip()
            if field_id.isdigit():
                delete_field(int(field_id))
                print(f"Field with ID {field_id} deleted.")
            else:
                print("Invalid ID.")

        elif choice == '4':
            url = input("Enter job listing URL: ").strip()
            extracted_fields = extract_fields(url, default=False)
            print("\nExtracted Fields:")
            if extracted_fields:
                for key, value in extracted_fields.items():
                    print(f"  \033[30;47m{key.split(' ')[0]}\033[0m: {value}")
            else:
                print("No fields extracted or URL is invalid.")

        elif choice == '5':
            print("Goodbye!")
            break

        else:
            print("Invalid choice, please try again.")
