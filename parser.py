import os
import sqlite3
import re
from bs4 import BeautifulSoup

DATA_DIR = "data"
DB_PATH = "regsearch.db"


def init_database():
    """
    Create the SQLite database and tables if they don't exist yet.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regulations (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            url      TEXT,
            filename TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            regulation_id   INTEGER NOT NULL,
            section_number  TEXT,
            section_text    TEXT NOT NULL,
            embedding       BLOB,
            FOREIGN KEY (regulation_id) REFERENCES regulations(id)
        )
    """)

    conn.commit()
    return conn


def extract_title(soup):
    """
    Try to find the regulation title from the HTML.
    NS regulation pages usually put the title in an <h1> or <title> tag.
    """
    # Try <h1> first
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    # Fall back to <title> tag
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    return "Unknown Regulation"


def extract_sections(soup):
    """
    Parse regulation HTML and return a list of (section_number, section_text) tuples.

    NS regulations are structured as paragraphs with section numbers like:
    "1  This regulation applies to..."
    "2  In this regulation..."
    "2(1) The minister may..."

    We look for paragraph tags and try to detect section boundaries.
    """
    sections = []

    # Get all paragraph text from the main content
    # NS pages usually put content in <p> tags or <div class="Section">
    paragraphs = soup.find_all(["p", "div"], class_=re.compile(r"[Ss]ection|[Cc]ontent|[Bb]ody"))

    if not paragraphs:
        # Fall back: just grab all <p> tags
        paragraphs = soup.find_all("p")

    # Regex pattern for section numbers like: 1, 2(1), 3A, Schedule A, etc.
    section_pattern = re.compile(r"^(\d+[A-Za-z]?(\(\d+\))?|Schedule\s+[A-Z]|PART\s+[IVX]+)")

    current_section_num = None
    current_text_parts = []

    for p in paragraphs:
        text = p.get_text(separator=" ", strip=True)

        # Skip very short or empty paragraphs (navigation, headers, etc.)
        if len(text) < 10:
            continue

        # Check if this paragraph starts a new section
        match = section_pattern.match(text)
        if match:
            # Save the previous section before starting the new one
            if current_text_parts:
                full_text = " ".join(current_text_parts).strip()
                if len(full_text) > 20:  # skip trivially short sections
                    sections.append((current_section_num, full_text))

            current_section_num = match.group(0)
            # The rest of the line after the section number is the start of the text
            rest = text[len(current_section_num):].strip()
            current_text_parts = [rest] if rest else []

        else:
            # This paragraph is a continuation of the current section
            current_text_parts.append(text)

    # Don't forget the last section
    if current_text_parts:
        full_text = " ".join(current_text_parts).strip()
        if len(full_text) > 20:
            sections.append((current_section_num, full_text))

    # If we found nothing structured, treat the whole page as one chunk
    if not sections:
        all_text = soup.get_text(separator=" ", strip=True)
        # Split into ~500-character chunks so embeddings stay manageable
        chunks = [all_text[i:i+500] for i in range(0, len(all_text), 500)]
        sections = [(f"chunk_{i+1}", chunk) for i, chunk in enumerate(chunks) if len(chunk) > 30]

    return sections


def parse_file(filepath, url=""):
    """
    Open one HTML file, extract title and sections.
    Returns (title, sections_list) where sections_list is [(num, text), ...]
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)
    sections = extract_sections(soup)

    return title, sections


def run_parser():
    conn = init_database()
    cursor = conn.cursor()

    # Get all HTML files in data/
    html_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".htm")]
    print(f"Parsing {len(html_files)} regulation files...\n")

    total_sections = 0

    for filename in html_files:
        filepath = os.path.join(DATA_DIR, filename)

        title, sections = parse_file(filepath)

        if not sections:
            print(f"  No sections found in {filename}, skipping.")
            continue

        # Insert the regulation record
        cursor.execute(
            "INSERT INTO regulations (title, url, filename) VALUES (?, ?, ?)",
            (title, "", filename)
        )
        regulation_id = cursor.lastrowid

        # Insert each section
        for section_number, section_text in sections:
            cursor.execute(
                "INSERT INTO sections (regulation_id, section_number, section_text) VALUES (?, ?, ?)",
                (regulation_id, section_number, section_text)
            )

        print(f"  {filename}: '{title}' -> {len(sections)} sections".encode('ascii', errors='replace').decode('ascii'))
        total_sections += len(sections)

    conn.commit()
    conn.close()

    print(f"\nDone. Stored {total_sections} sections across {len(html_files)} regulations.")
    print(f"Database saved to: {DB_PATH}")


if __name__ == "__main__":
    run_parser()
