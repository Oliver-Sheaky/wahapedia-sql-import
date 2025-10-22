#!/usr/bin/env python3
"""
Wahapedia CSV Importer for Supabase (PostgreSQL)
=================================================
This script downloads CSV files from web URLs and imports them into
a local Supabase database with smart update detection and duplicate prevention.

Requirements:
    pip install supabase requests python-dotenv

Usage:
    python 03_import_from_web.py

Configuration:
    Copy example.env to .env and update with your database credentials.
    The script will automatically load configuration from .env file.
"""

import os
import sys
import requests
import time
from datetime import datetime
from io import StringIO
import csv
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Fix Windows console encoding issues
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# CONFIGURATION
# =====================================================================

# Rate limiting to avoid HTTP 429 "Too Many Requests" errors
DOWNLOAD_DELAY_SECONDS = 0.5

# Base URL where CSV files are hosted
# Can be overridden by CSV_BASE_URL environment variable
CSV_BASE_URL = os.getenv("CSV_BASE_URL", "http://wahapedia.ru/wh40k10ed/")

# List of all CSV files to download and import
CSV_FILES = [
    "Last_update.csv",
    "Factions.csv",
    "Source.csv",
    "Stratagems.csv",
    "Abilities.csv",
    "Enhancements.csv",
    "Detachment_abilities.csv",
    "Datasheets.csv",
    "Datasheets_abilities.csv",
    "Datasheets_keywords.csv",
    "Datasheets_models.csv",
    "Datasheets_options.csv",
    "Datasheets_wargear.csv",
    "Datasheets_unit_composition.csv",
    "Datasheets_models_cost.csv",
    "Datasheets_stratagems.csv",
    "Datasheets_enhancements.csv",
    "Datasheets_detachment_abilities.csv",
    "Datasheets_leader.csv",
]

# Supabase client configuration
# Loaded from .env file or environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def download_csv(url):
    """
    Download CSV content from a URL with rate limiting.

    Args:
        url: Full URL to the CSV file

    Returns:
        String content of the CSV file

    Raises:
        requests.RequestException: If download fails
    """
    print(f"  Downloading {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    # Ensure UTF-8 encoding
    response.encoding = 'utf-8'
    # Rate limiting to avoid HTTP 429 errors
    time.sleep(DOWNLOAD_DELAY_SECONDS)
    return response.text


def parse_csv_content(content, delimiter='|'):
    """
    Parse CSV content into a list of dictionaries.
    Handles UTF-8 BOM and strips whitespace from column names.

    Args:
        content: CSV content as string
        delimiter: CSV delimiter character (default: |)

    Returns:
        List of dictionaries representing CSV rows
    """
    csv_file = StringIO(content)
    reader = csv.DictReader(csv_file, delimiter=delimiter)

    # Strip BOM and whitespace from column names, filter empty keys
    rows = []
    for row in reader:
        cleaned_row = {}
        for key, value in row.items():
            # Remove UTF-8 BOM (\ufeff), strip whitespace, and skip empty keys
            clean_key = key.replace('\ufeff', '').strip()
            if clean_key:  # Skip empty column names (trailing delimiters)
                cleaned_row[clean_key] = value
        rows.append(cleaned_row)

    return rows


def convert_boolean(value):
    """
    Convert string boolean values to Python boolean.

    Args:
        value: String value ("true"/"false" or empty)

    Returns:
        Boolean value or None
    """
    if value is None or value == '':
        return None
    return value.lower() == 'true'


def convert_int(value):
    """
    Convert string to integer, handling empty values.

    Args:
        value: String value or empty

    Returns:
        Integer value or None
    """
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def convert_date(value):
    """
    Convert DD.MM.YYYY date string to YYYY-MM-DD format for PostgreSQL.

    Args:
        value: Date string in DD.MM.YYYY format or empty

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if value is None or value == '':
        return None
    try:
        # Parse DD.MM.YYYY format - handle both date and datetime strings
        # Remove time portion if present (e.g., "17.09.2024 0:00:00")
        date_part = value.split(' ')[0]
        parts = date_part.split('.')
        if len(parts) == 3:
            day, month, year = parts
            # Ensure proper padding for day and month
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return None
    except Exception as e:
        print(f"  WARNING: Could not convert date '{value}': {e}")
        return None


def get_valid_datasheet_ids(supabase: Client):
    """Helper to get valid datasheet IDs for child table validation."""
    response = supabase.table('datasheets').select('id').execute()
    return set(row['id'] for row in response.data)


def connect_to_database():
    """
    Establish connection to Supabase using the Python client.

    Returns:
        Supabase Client object

    Raises:
        Exception: If connection fails
    """
    print("Connecting to Supabase...")
    if not SUPABASE_KEY:
        raise Exception("SUPABASE_KEY environment variable is required")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  Connected successfully!")
    return supabase


# =====================================================================
# UPDATE CHECKING
# =====================================================================

def check_if_update_needed(supabase: Client, new_update_time):
    """
    Check if data needs to be updated based on Last_update timestamp.

    Args:
        supabase: Supabase client
        new_update_time: New timestamp from Last_update.csv

    Returns:
        Boolean indicating if update is needed
    """
    try:
        response = supabase.table('last_update').select('last_update').order('last_update', desc=True).limit(1).execute()
        existing_update_time = None

        if response.data and len(response.data) > 0:
            existing_update_time_str = response.data[0]['last_update']
            # Parse the timestamp string from Supabase
            existing_update_time = datetime.fromisoformat(existing_update_time_str.replace('Z', '+00:00'))

        if existing_update_time is None:
            print(f"  No existing data found. Proceeding with import.")
            return True

        # Parse timestamps
        new_ts = datetime.strptime(new_update_time, '%Y-%m-%d %H:%M:%S')

        if new_ts <= existing_update_time:
            print(f"  Data is already up to date.")
            print(f"  Existing: {existing_update_time}")
            print(f"  New:      {new_ts}")
            return False
        else:
            print(f"  New data available!")
            print(f"  Existing: {existing_update_time}")
            print(f"  New:      {new_ts}")
            return True
    except Exception as e:
        print(f"  Error checking updates: {e}")
        print(f"  Proceeding with import...")
        return True


# =====================================================================
# IMPORT FUNCTIONS
# =====================================================================

def import_factions(supabase: Client, data):
    """Import Factions table."""
    print("  Importing Factions...")
    supabase.table('factions').upsert(data).execute()
    print(f"    Processed {len(data)} factions")


def import_source(supabase: Client, data):
    """Import Source table."""
    print("  Importing Source...")
    # Convert date fields to proper format
    for row in data:
        row['errata_date'] = convert_date(row.get('errata_date'))
    supabase.table('source').upsert(data).execute()
    print(f"    Processed {len(data)} sources")


def import_last_update(supabase: Client, data):
    """Import Last_update table."""
    print("  Importing Last_update...")
    supabase.table('last_update').upsert(data, on_conflict='last_update').execute()
    print(f"    Processed {len(data)} timestamp(s)")


def import_stratagems(supabase: Client, data):
    """Import Stratagems table."""
    print("  Importing Stratagems...")
    # Convert empty faction_id to 'UN' (Unaligned Forces) for universal stratagems
    for row in data:
        if row.get('faction_id') == '':
            row['faction_id'] = 'UN'

    # Deduplicate by id (keep last occurrence)
    seen_ids = {}
    for row in data:
        seen_ids[row['id']] = row
    deduplicated_data = list(seen_ids.values())

    supabase.table('stratagems').upsert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} stratagems")


def import_abilities(supabase: Client, data):
    """Import Abilities table."""
    print("  Importing Abilities...")
    # Convert empty faction_id to 'UN' (Unaligned Forces) for universal abilities
    for row in data:
        if row.get('faction_id') == '':
            row['faction_id'] = 'UN'

    # Deduplicate by id (keep last occurrence)
    seen_ids = {}
    for row in data:
        seen_ids[row['id']] = row
    deduplicated_data = list(seen_ids.values())

    supabase.table('abilities').upsert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} abilities (from {len(data)} total records)")


def import_enhancements(supabase: Client, data):
    """Import Enhancements table."""
    print("  Importing Enhancements...")
    # Convert empty faction_id to 'UN' (Unaligned Forces) for universal enhancements
    for row in data:
        if row.get('faction_id') == '':
            row['faction_id'] = 'UN'

    # Deduplicate by id (keep last occurrence)
    seen_ids = {}
    for row in data:
        seen_ids[row['id']] = row
    deduplicated_data = list(seen_ids.values())

    supabase.table('enhancements').upsert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} enhancements")


def import_detachment_abilities(supabase: Client, data):
    """Import Detachment_abilities table."""
    print("  Importing Detachment_abilities...")
    # Convert empty faction_id to 'UN' (Unaligned Forces) for universal detachment abilities
    for row in data:
        if row.get('faction_id') == '':
            row['faction_id'] = 'UN'

    # Deduplicate by id (keep last occurrence)
    seen_ids = {}
    for row in data:
        seen_ids[row['id']] = row
    deduplicated_data = list(seen_ids.values())

    supabase.table('detachment_abilities').upsert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} detachment abilities")


def import_datasheets(supabase: Client, data):
    """Import Datasheets table."""
    print("  Importing Datasheets...")
    # Convert boolean and foreign key fields
    for row in data:
        row['virtual'] = convert_boolean(row.get('virtual'))
        # Convert empty faction_id to 'UN' (Unaligned Forces) for universal datasheets
        if row.get('faction_id') == '':
            row['faction_id'] = 'UN'
        # source_id is required - use first source if empty
        if row.get('source_id') == '':
            row['source_id'] = '000000012'  # Default to first source

    # Deduplicate by id (keep last occurrence)
    seen_ids = {}
    for row in data:
        seen_ids[row['id']] = row
    deduplicated_data = list(seen_ids.values())

    supabase.table('datasheets').upsert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} datasheets")


def import_datasheets_abilities(supabase: Client, data):
    """Import Datasheets_abilities table."""
    print("  Importing Datasheets_abilities...")

    # Get unique datasheet IDs
    datasheet_ids = set(row['datasheet_id'] for row in data)

    # Delete existing records for these datasheets
    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_abilities').delete().eq('datasheet_id', datasheet_id).execute()

    # Get existing IDs to validate foreign keys
    abilities_response = supabase.table('abilities').select('id').execute()
    valid_ability_ids = set(row['id'] for row in abilities_response.data)

    datasheets_response = supabase.table('datasheets').select('id').execute()
    valid_datasheet_ids = set(row['id'] for row in datasheets_response.data)

    # Convert integer and foreign key fields, filter invalid references
    valid_data = []
    skipped_count = 0
    for row in data:
        row['line'] = convert_int(row.get('line'))
        # Convert empty ability_id to NULL
        if row.get('ability_id') == '':
            row['ability_id'] = None

        # Skip if datasheet_id or ability_id references non-existent records
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        if row['ability_id'] is not None and row['ability_id'] not in valid_ability_ids:
            skipped_count += 1
            continue

        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_abilities').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet abilities (skipped {skipped_count} with invalid ability references)")


def import_datasheets_keywords(supabase: Client, data):
    """Import Datasheets_keywords table."""
    print("  Importing Datasheets_keywords...")

    # Get valid datasheet IDs
    datasheets_response = supabase.table('datasheets').select('id').execute()
    valid_datasheet_ids = set(row['id'] for row in datasheets_response.data)

    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_keywords').delete().eq('datasheet_id', datasheet_id).execute()

    # Filter and convert data
    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['is_faction_keyword'] = convert_boolean(row.get('is_faction_keyword'))
        valid_data.append(row)

    # Deduplicate by composite key (datasheet_id, keyword)
    seen_keys = {}
    for row in valid_data:
        key = (row['datasheet_id'], row['keyword'])
        seen_keys[key] = row
    deduplicated_data = list(seen_keys.values())

    if deduplicated_data:
        supabase.table('datasheets_keywords').insert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} datasheet keywords (skipped {skipped_count} orphaned)")


def import_datasheets_models(supabase: Client, data):
    """Import Datasheets_models table."""
    print("  Importing Datasheets_models...")

    # Get valid datasheet IDs
    datasheets_response = supabase.table('datasheets').select('id').execute()
    valid_datasheet_ids = set(row['id'] for row in datasheets_response.data)

    # Filter valid datasheets and delete their existing records
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)
    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_models').delete().eq('datasheet_id', datasheet_id).execute()

    # Filter and convert data, map uppercase column names to lowercase
    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['line'] = convert_int(row.get('line'))
        # Map uppercase stat names to lowercase for database compatibility
        if 'M' in row:
            row['m'] = row.pop('M')
        if 'T' in row:
            row['t'] = row.pop('T')
        if 'Sv' in row:
            row['sv'] = row.pop('Sv')
        if 'W' in row:
            row['w'] = row.pop('W')
        if 'Ld' in row:
            row['ld'] = row.pop('Ld')
        if 'OC' in row:
            row['oc'] = row.pop('OC')
        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_models').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet models (skipped {skipped_count} orphaned)")


def import_datasheets_options(supabase: Client, data):
    """Import Datasheets_options table."""
    print("  Importing Datasheets_options...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_options').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['line'] = convert_int(row.get('line'))
        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_options').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet options (skipped {skipped_count} orphaned)")


def import_datasheets_wargear(supabase: Client, data):
    """Import Datasheets_wargear table."""
    print("  Importing Datasheets_wargear...")

    # Get valid datasheet IDs
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_wargear').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['line'] = convert_int(row.get('line'))
        row['line_in_wargear'] = convert_int(row.get('line_in_wargear'))
        # Map uppercase stat names to lowercase for database compatibility
        if 'A' in row:
            row['a'] = row.pop('A')
        if 'BS_WS' in row:
            row['bs_ws'] = row.pop('BS_WS')
        if 'S' in row:
            row['s'] = row.pop('S')
        if 'AP' in row:
            row['ap'] = row.pop('AP')
        if 'D' in row:
            row['d'] = row.pop('D')
        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_wargear').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet wargear (skipped {skipped_count} orphaned)")


def import_datasheets_unit_composition(supabase: Client, data):
    """Import Datasheets_unit_composition table."""
    print("  Importing Datasheets_unit_composition...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_unit_composition').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['line'] = convert_int(row.get('line'))
        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_unit_composition').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} unit compositions (skipped {skipped_count} orphaned)")


def import_datasheets_models_cost(supabase: Client, data):
    """Import Datasheets_models_cost table."""
    print("  Importing Datasheets_models_cost...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_models_cost').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = []
    skipped_count = 0
    for row in data:
        if row['datasheet_id'] not in valid_datasheet_ids:
            skipped_count += 1
            continue
        row['line'] = convert_int(row.get('line'))
        valid_data.append(row)

    if valid_data:
        supabase.table('datasheets_models_cost').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} model costs (skipped {skipped_count} orphaned)")


def import_datasheets_stratagems(supabase: Client, data):
    """Import Datasheets_stratagems junction table."""
    print("  Importing Datasheets_stratagems...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_stratagems').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = [row for row in data if row['datasheet_id'] in valid_datasheet_ids]
    skipped_count = len(data) - len(valid_data)

    if valid_data:
        supabase.table('datasheets_stratagems').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet-stratagem links (skipped {skipped_count} orphaned)")


def import_datasheets_enhancements(supabase: Client, data):
    """Import Datasheets_enhancements junction table."""
    print("  Importing Datasheets_enhancements...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_enhancements').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = [row for row in data if row['datasheet_id'] in valid_datasheet_ids]
    skipped_count = len(data) - len(valid_data)

    if valid_data:
        supabase.table('datasheets_enhancements').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet-enhancement links (skipped {skipped_count} orphaned)")


def import_datasheets_detachment_abilities(supabase: Client, data):
    """Import Datasheets_detachment_abilities junction table."""
    print("  Importing Datasheets_detachment_abilities...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)
    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_detachment_abilities').delete().eq('datasheet_id', datasheet_id).execute()

    valid_data = [row for row in data if row['datasheet_id'] in valid_datasheet_ids]
    skipped_count = len(data) - len(valid_data)

    if valid_data:
        supabase.table('datasheets_detachment_abilities').insert(valid_data).execute()
    print(f"    Processed {len(valid_data)} datasheet-detachment ability links (skipped {skipped_count} orphaned)")


def import_datasheets_leader(supabase: Client, data):
    """Import Datasheets_leader junction table."""
    print("  Importing Datasheets_leader...")
    valid_datasheet_ids = get_valid_datasheet_ids(supabase)

    # Map CSV column names to database column names
    for row in data:
        if 'leader_id' in row:
            row['datasheet_id'] = row.pop('leader_id')
        if 'attached_id' in row:
            row['attached_datasheet_id'] = row.pop('attached_id')

    datasheet_ids = set(row['datasheet_id'] for row in data if row['datasheet_id'] in valid_datasheet_ids)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_leader').delete().eq('datasheet_id', datasheet_id).execute()

    # Both datasheet_id and attached_datasheet_id must be valid
    valid_data = [row for row in data if row['datasheet_id'] in valid_datasheet_ids and row.get('attached_datasheet_id') in valid_datasheet_ids]

    # Deduplicate by composite key (datasheet_id, attached_datasheet_id)
    seen_keys = {}
    for row in valid_data:
        key = (row['datasheet_id'], row['attached_datasheet_id'])
        seen_keys[key] = row
    deduplicated_data = list(seen_keys.values())

    skipped_count = len(data) - len(deduplicated_data)

    if deduplicated_data:
        supabase.table('datasheets_leader').insert(deduplicated_data).execute()
    print(f"    Processed {len(deduplicated_data)} leader-attachment links (skipped {skipped_count} orphaned/duplicates)")


# =====================================================================
# MAIN IMPORT ORCHESTRATION
# =====================================================================

# Map CSV files to their import functions
IMPORT_FUNCTIONS = {
    "Factions.csv": import_factions,
    "Source.csv": import_source,
    "Last_update.csv": import_last_update,
    "Stratagems.csv": import_stratagems,
    "Abilities.csv": import_abilities,
    "Enhancements.csv": import_enhancements,
    "Detachment_abilities.csv": import_detachment_abilities,
    "Datasheets.csv": import_datasheets,
    "Datasheets_abilities.csv": import_datasheets_abilities,
    "Datasheets_keywords.csv": import_datasheets_keywords,
    "Datasheets_models.csv": import_datasheets_models,
    "Datasheets_options.csv": import_datasheets_options,
    "Datasheets_wargear.csv": import_datasheets_wargear,
    "Datasheets_unit_composition.csv": import_datasheets_unit_composition,
    "Datasheets_models_cost.csv": import_datasheets_models_cost,
    "Datasheets_stratagems.csv": import_datasheets_stratagems,
    "Datasheets_enhancements.csv": import_datasheets_enhancements,
    "Datasheets_detachment_abilities.csv": import_datasheets_detachment_abilities,
    "Datasheets_leader.csv": import_datasheets_leader,
}


def main():
    """Main execution function."""
    print("=" * 70)
    print("Wahapedia CSV Importer for Supabase")
    print("=" * 70)

    supabase = None

    try:
        # Step 1: Download and check Last_update.csv first
        print("\n[1/3] Checking for updates...")
        last_update_url = CSV_BASE_URL + "Last_update.csv"
        last_update_content = download_csv(last_update_url)
        last_update_data = parse_csv_content(last_update_content)

        if not last_update_data:
            print("  ERROR: Last_update.csv is empty!")
            sys.exit(1)

        new_timestamp = last_update_data[0]['last_update']

        # Connect to Supabase
        supabase = connect_to_database()

        # Check if update is needed
        if not check_if_update_needed(supabase, new_timestamp):
            print("\n  Skipping import - data is already current.")
            return

        # Step 2: Download all CSV files
        print("\n[2/3] Downloading CSV files...")
        csv_data = {}

        for csv_file in CSV_FILES:
            try:
                url = CSV_BASE_URL + csv_file
                content = download_csv(url)
                csv_data[csv_file] = parse_csv_content(content)
            except requests.RequestException as e:
                print(f"  WARNING: Failed to download {csv_file}: {e}")
                print(f"  Skipping this file...")
                csv_data[csv_file] = []

        # Step 3: Import data in correct order
        print("\n[3/3] Importing data into database...")

        for csv_file in CSV_FILES:
            if csv_file in csv_data and csv_data[csv_file]:
                import_func = IMPORT_FUNCTIONS.get(csv_file)
                if import_func:
                    import_func(supabase, csv_data[csv_file])
                else:
                    print(f"  WARNING: No import function for {csv_file}")

        # Display summary
        print("\n" + "=" * 70)
        print("Import completed successfully!")
        print("=" * 70)

        factions_count = supabase.table('factions').select('*', count='exact').execute()
        print(f"  Factions: {factions_count.count}")

        datasheets_count = supabase.table('datasheets').select('*', count='exact').execute()
        print(f"  Datasheets: {datasheets_count.count}")

        stratagems_count = supabase.table('stratagems').select('*', count='exact').execute()
        print(f"  Stratagems: {stratagems_count.count}")

        abilities_count = supabase.table('abilities').select('*', count='exact').execute()
        print(f"  Abilities: {abilities_count.count}")

        last_update = supabase.table('last_update').select('last_update').order('last_update', desc=True).limit(1).execute()
        if last_update.data and len(last_update.data) > 0:
            print(f"  Last update: {last_update.data[0]['last_update']}")

        print("=" * 70)

    except requests.RequestException as e:
        print(f"\n  DOWNLOAD ERROR: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n  UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
