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
    Download CSV content from a URL.

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
        # Parse DD.MM.YYYY format
        parts = value.split('.')
        if len(parts) == 3:
            day, month, year = parts
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return None
    except:
        return None


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
    supabase.table('stratagems').upsert(data).execute()
    print(f"    Processed {len(data)} stratagems")


def import_abilities(supabase: Client, data):
    """Import Abilities table."""
    print("  Importing Abilities...")
    supabase.table('abilities').upsert(data).execute()
    print(f"    Processed {len(data)} abilities")


def import_enhancements(supabase: Client, data):
    """Import Enhancements table."""
    print("  Importing Enhancements...")
    supabase.table('enhancements').upsert(data).execute()
    print(f"    Processed {len(data)} enhancements")


def import_detachment_abilities(supabase: Client, data):
    """Import Detachment_abilities table."""
    print("  Importing Detachment_abilities...")
    supabase.table('detachment_abilities').upsert(data).execute()
    print(f"    Processed {len(data)} detachment abilities")


def import_datasheets(supabase: Client, data):
    """Import Datasheets table."""
    print("  Importing Datasheets...")
    # Convert boolean fields
    for row in data:
        row['virtual'] = convert_boolean(row.get('virtual'))
    supabase.table('datasheets').upsert(data).execute()
    print(f"    Processed {len(data)} datasheets")


def import_datasheets_abilities(supabase: Client, data):
    """Import Datasheets_abilities table."""
    print("  Importing Datasheets_abilities...")

    # Get unique datasheet IDs
    datasheet_ids = set(row['datasheet_id'] for row in data)

    # Delete existing records for these datasheets
    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_abilities').delete().eq('datasheet_id', datasheet_id).execute()

    # Convert integer fields and insert new records
    for row in data:
        row['line'] = convert_int(row.get('line'))

    supabase.table('datasheets_abilities').insert(data).execute()
    print(f"    Processed {len(data)} datasheet abilities")


def import_datasheets_keywords(supabase: Client, data):
    """Import Datasheets_keywords table."""
    print("  Importing Datasheets_keywords...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_keywords').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['is_faction_keyword'] = convert_boolean(row.get('is_faction_keyword'))

    supabase.table('datasheets_keywords').insert(data).execute()
    print(f"    Processed {len(data)} datasheet keywords")


def import_datasheets_models(supabase: Client, data):
    """Import Datasheets_models table."""
    print("  Importing Datasheets_models...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_models').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['line'] = convert_int(row.get('line'))

    supabase.table('datasheets_models').insert(data).execute()
    print(f"    Processed {len(data)} datasheet models")


def import_datasheets_options(supabase: Client, data):
    """Import Datasheets_options table."""
    print("  Importing Datasheets_options...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_options').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['line'] = convert_int(row.get('line'))

    supabase.table('datasheets_options').insert(data).execute()
    print(f"    Processed {len(data)} datasheet options")


def import_datasheets_wargear(supabase: Client, data):
    """Import Datasheets_wargear table."""
    print("  Importing Datasheets_wargear...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_wargear').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['line'] = convert_int(row.get('line'))
        row['line_in_wargear'] = convert_int(row.get('line_in_wargear'))

    supabase.table('datasheets_wargear').insert(data).execute()
    print(f"    Processed {len(data)} datasheet wargear")


def import_datasheets_unit_composition(supabase: Client, data):
    """Import Datasheets_unit_composition table."""
    print("  Importing Datasheets_unit_composition...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_unit_composition').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['line'] = convert_int(row.get('line'))

    supabase.table('datasheets_unit_composition').insert(data).execute()
    print(f"    Processed {len(data)} unit compositions")


def import_datasheets_models_cost(supabase: Client, data):
    """Import Datasheets_models_cost table."""
    print("  Importing Datasheets_models_cost...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_models_cost').delete().eq('datasheet_id', datasheet_id).execute()

    for row in data:
        row['line'] = convert_int(row.get('line'))

    supabase.table('datasheets_models_cost').insert(data).execute()
    print(f"    Processed {len(data)} model costs")


def import_datasheets_stratagems(supabase: Client, data):
    """Import Datasheets_stratagems junction table."""
    print("  Importing Datasheets_stratagems...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_stratagems').delete().eq('datasheet_id', datasheet_id).execute()

    supabase.table('datasheets_stratagems').insert(data).execute()
    print(f"    Processed {len(data)} datasheet-stratagem links")


def import_datasheets_enhancements(supabase: Client, data):
    """Import Datasheets_enhancements junction table."""
    print("  Importing Datasheets_enhancements...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_enhancements').delete().eq('datasheet_id', datasheet_id).execute()

    supabase.table('datasheets_enhancements').insert(data).execute()
    print(f"    Processed {len(data)} datasheet-enhancement links")


def import_datasheets_detachment_abilities(supabase: Client, data):
    """Import Datasheets_detachment_abilities junction table."""
    print("  Importing Datasheets_detachment_abilities...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_detachment_abilities').delete().eq('datasheet_id', datasheet_id).execute()

    supabase.table('datasheets_detachment_abilities').insert(data).execute()
    print(f"    Processed {len(data)} datasheet-detachment ability links")


def import_datasheets_leader(supabase: Client, data):
    """Import Datasheets_leader junction table."""
    print("  Importing Datasheets_leader...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        for datasheet_id in datasheet_ids:
            supabase.table('datasheets_leader').delete().eq('datasheet_id', datasheet_id).execute()

    supabase.table('datasheets_leader').insert(data).execute()
    print(f"    Processed {len(data)} leader-attachment links")


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
