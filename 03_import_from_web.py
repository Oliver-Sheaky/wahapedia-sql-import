#!/usr/bin/env python3
"""
Wahapedia CSV Importer for Supabase (PostgreSQL)
=================================================
This script downloads CSV files from web URLs and imports them into
a local Supabase database with smart update detection and duplicate prevention.

Requirements:
    pip install psycopg2-binary requests python-dotenv

Usage:
    python 03_import_from_web.py

Configuration:
    Copy example.env to .env and update with your database credentials.
    The script will automatically load configuration from .env file.
"""

import os
import sys
import requests
import psycopg2
from psycopg2 import sql, extras
from datetime import datetime
from io import StringIO
import csv
from dotenv import load_dotenv

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

# Database connection configuration
# Loaded from .env file or environment variables
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "54322")),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

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


def connect_to_database():
    """
    Establish connection to PostgreSQL database.

    Returns:
        psycopg2 connection object

    Raises:
        psycopg2.Error: If connection fails
    """
    print("Connecting to database...")
    conn = psycopg2.connect(**DATABASE_CONFIG)
    print("  Connected successfully!")
    return conn


# =====================================================================
# UPDATE CHECKING
# =====================================================================

def check_if_update_needed(cursor, new_update_time):
    """
    Check if data needs to be updated based on Last_update timestamp.

    Args:
        cursor: Database cursor
        new_update_time: New timestamp from Last_update.csv

    Returns:
        Boolean indicating if update is needed
    """
    cursor.execute("SELECT MAX(last_update) FROM Last_update")
    result = cursor.fetchone()
    existing_update_time = result[0] if result else None

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


# =====================================================================
# IMPORT FUNCTIONS
# =====================================================================

def import_factions(cursor, data):
    """Import Factions table."""
    print("  Importing Factions...")
    for row in data:
        cursor.execute("""
            INSERT INTO Factions (id, name, link)
            VALUES (%(id)s, %(name)s, %(link)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                link = EXCLUDED.link,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} factions")


def import_source(cursor, data):
    """Import Source table."""
    print("  Importing Source...")
    for row in data:
        cursor.execute("""
            INSERT INTO Source (id, name, type, edition, version, errata_date, errata_link)
            VALUES (%(id)s, %(name)s, %(type)s, %(edition)s, %(version)s, %(errata_date)s, %(errata_link)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                edition = EXCLUDED.edition,
                version = EXCLUDED.version,
                errata_date = EXCLUDED.errata_date,
                errata_link = EXCLUDED.errata_link,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} sources")


def import_last_update(cursor, data):
    """Import Last_update table."""
    print("  Importing Last_update...")
    for row in data:
        cursor.execute("""
            INSERT INTO Last_update (last_update)
            VALUES (%(last_update)s)
            ON CONFLICT (last_update) DO NOTHING
        """, row)
    print(f"    Processed {len(data)} timestamp(s)")


def import_stratagems(cursor, data):
    """Import Stratagems table."""
    print("  Importing Stratagems...")
    for row in data:
        cursor.execute("""
            INSERT INTO Stratagems (id, faction_id, name, type, cp_cost, legend, turn, phase, description, detachment)
            VALUES (%(id)s, %(faction_id)s, %(name)s, %(type)s, %(cp_cost)s, %(legend)s, %(turn)s, %(phase)s, %(description)s, %(detachment)s)
            ON CONFLICT (id) DO UPDATE SET
                faction_id = EXCLUDED.faction_id,
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                cp_cost = EXCLUDED.cp_cost,
                legend = EXCLUDED.legend,
                turn = EXCLUDED.turn,
                phase = EXCLUDED.phase,
                description = EXCLUDED.description,
                detachment = EXCLUDED.detachment,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} stratagems")


def import_abilities(cursor, data):
    """Import Abilities table."""
    print("  Importing Abilities...")
    for row in data:
        cursor.execute("""
            INSERT INTO Abilities (id, name, legend, faction_id, description)
            VALUES (%(id)s, %(name)s, %(legend)s, %(faction_id)s, %(description)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                legend = EXCLUDED.legend,
                faction_id = EXCLUDED.faction_id,
                description = EXCLUDED.description,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} abilities")


def import_enhancements(cursor, data):
    """Import Enhancements table."""
    print("  Importing Enhancements...")
    for row in data:
        cursor.execute("""
            INSERT INTO Enhancements (id, faction_id, name, legend, description, cost, detachment)
            VALUES (%(id)s, %(faction_id)s, %(name)s, %(legend)s, %(description)s, %(cost)s, %(detachment)s)
            ON CONFLICT (id) DO UPDATE SET
                faction_id = EXCLUDED.faction_id,
                name = EXCLUDED.name,
                legend = EXCLUDED.legend,
                description = EXCLUDED.description,
                cost = EXCLUDED.cost,
                detachment = EXCLUDED.detachment,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} enhancements")


def import_detachment_abilities(cursor, data):
    """Import Detachment_abilities table."""
    print("  Importing Detachment_abilities...")
    for row in data:
        cursor.execute("""
            INSERT INTO Detachment_abilities (id, faction_id, name, legend, description, detachment)
            VALUES (%(id)s, %(faction_id)s, %(name)s, %(legend)s, %(description)s, %(detachment)s)
            ON CONFLICT (id) DO UPDATE SET
                faction_id = EXCLUDED.faction_id,
                name = EXCLUDED.name,
                legend = EXCLUDED.legend,
                description = EXCLUDED.description,
                detachment = EXCLUDED.detachment,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} detachment abilities")


def import_datasheets(cursor, data):
    """Import Datasheets table."""
    print("  Importing Datasheets...")
    for row in data:
        # Convert boolean field
        row['virtual'] = convert_boolean(row.get('virtual'))

        cursor.execute("""
            INSERT INTO Datasheets (id, name, faction_id, source_id, legend, role, loadout, transport, virtual,
                                    leader_head, leader_footer, damaged_w, damaged_description, link)
            VALUES (%(id)s, %(name)s, %(faction_id)s, %(source_id)s, %(legend)s, %(role)s, %(loadout)s, %(transport)s, %(virtual)s,
                    %(leader_head)s, %(leader_footer)s, %(damaged_w)s, %(damaged_description)s, %(link)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                faction_id = EXCLUDED.faction_id,
                source_id = EXCLUDED.source_id,
                legend = EXCLUDED.legend,
                role = EXCLUDED.role,
                loadout = EXCLUDED.loadout,
                transport = EXCLUDED.transport,
                virtual = EXCLUDED.virtual,
                leader_head = EXCLUDED.leader_head,
                leader_footer = EXCLUDED.leader_footer,
                damaged_w = EXCLUDED.damaged_w,
                damaged_description = EXCLUDED.damaged_description,
                link = EXCLUDED.link,
                date_imported = CURRENT_TIMESTAMP
        """, row)
    print(f"    Processed {len(data)} datasheets")


def import_datasheets_abilities(cursor, data):
    """Import Datasheets_abilities table."""
    print("  Importing Datasheets_abilities...")

    # Get unique datasheet IDs
    datasheet_ids = set(row['datasheet_id'] for row in data)

    # Delete existing records for these datasheets
    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_abilities WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    # Insert new records
    for row in data:
        row['line'] = convert_int(row.get('line'))
        cursor.execute("""
            INSERT INTO Datasheets_abilities (datasheet_id, line, ability_id, model, name, description, type, parameter)
            VALUES (%(datasheet_id)s, %(line)s, %(ability_id)s, %(model)s, %(name)s, %(description)s, %(type)s, %(parameter)s)
        """, row)
    print(f"    Processed {len(data)} datasheet abilities")


def import_datasheets_keywords(cursor, data):
    """Import Datasheets_keywords table."""
    print("  Importing Datasheets_keywords...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_keywords WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['is_faction_keyword'] = convert_boolean(row.get('is_faction_keyword'))
        cursor.execute("""
            INSERT INTO Datasheets_keywords (datasheet_id, keyword, model, is_faction_keyword)
            VALUES (%(datasheet_id)s, %(keyword)s, %(model)s, %(is_faction_keyword)s)
        """, row)
    print(f"    Processed {len(data)} datasheet keywords")


def import_datasheets_models(cursor, data):
    """Import Datasheets_models table."""
    print("  Importing Datasheets_models...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_models WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['line'] = convert_int(row.get('line'))
        cursor.execute("""
            INSERT INTO Datasheets_models (datasheet_id, line, name, M, T, Sv, inv_sv, inv_sv_descr, W, Ld, OC, base_size, base_size_descr)
            VALUES (%(datasheet_id)s, %(line)s, %(name)s, %(M)s, %(T)s, %(Sv)s, %(inv_sv)s, %(inv_sv_descr)s, %(W)s, %(Ld)s, %(OC)s, %(base_size)s, %(base_size_descr)s)
        """, row)
    print(f"    Processed {len(data)} datasheet models")


def import_datasheets_options(cursor, data):
    """Import Datasheets_options table."""
    print("  Importing Datasheets_options...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_options WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['line'] = convert_int(row.get('line'))
        cursor.execute("""
            INSERT INTO Datasheets_options (datasheet_id, line, button, description)
            VALUES (%(datasheet_id)s, %(line)s, %(button)s, %(description)s)
        """, row)
    print(f"    Processed {len(data)} datasheet options")


def import_datasheets_wargear(cursor, data):
    """Import Datasheets_wargear table."""
    print("  Importing Datasheets_wargear...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_wargear WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['line'] = convert_int(row.get('line'))
        row['line_in_wargear'] = convert_int(row.get('line_in_wargear'))
        cursor.execute("""
            INSERT INTO Datasheets_wargear (datasheet_id, line, line_in_wargear, dice, name, description, range, type, A, BS_WS, S, AP, D)
            VALUES (%(datasheet_id)s, %(line)s, %(line_in_wargear)s, %(dice)s, %(name)s, %(description)s, %(range)s, %(type)s, %(A)s, %(BS_WS)s, %(S)s, %(AP)s, %(D)s)
        """, row)
    print(f"    Processed {len(data)} datasheet wargear")


def import_datasheets_unit_composition(cursor, data):
    """Import Datasheets_unit_composition table."""
    print("  Importing Datasheets_unit_composition...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_unit_composition WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['line'] = convert_int(row.get('line'))
        cursor.execute("""
            INSERT INTO Datasheets_unit_composition (datasheet_id, line, description)
            VALUES (%(datasheet_id)s, %(line)s, %(description)s)
        """, row)
    print(f"    Processed {len(data)} unit compositions")


def import_datasheets_models_cost(cursor, data):
    """Import Datasheets_models_cost table."""
    print("  Importing Datasheets_models_cost...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_models_cost WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        row['line'] = convert_int(row.get('line'))
        cursor.execute("""
            INSERT INTO Datasheets_models_cost (datasheet_id, line, description, cost)
            VALUES (%(datasheet_id)s, %(line)s, %(description)s, %(cost)s)
        """, row)
    print(f"    Processed {len(data)} model costs")


def import_datasheets_stratagems(cursor, data):
    """Import Datasheets_stratagems junction table."""
    print("  Importing Datasheets_stratagems...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_stratagems WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        cursor.execute("""
            INSERT INTO Datasheets_stratagems (datasheet_id, stratagem_id)
            VALUES (%(datasheet_id)s, %(stratagem_id)s)
        """, row)
    print(f"    Processed {len(data)} datasheet-stratagem links")


def import_datasheets_enhancements(cursor, data):
    """Import Datasheets_enhancements junction table."""
    print("  Importing Datasheets_enhancements...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_enhancements WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        cursor.execute("""
            INSERT INTO Datasheets_enhancements (datasheet_id, enhancement_id)
            VALUES (%(datasheet_id)s, %(enhancement_id)s)
        """, row)
    print(f"    Processed {len(data)} datasheet-enhancement links")


def import_datasheets_detachment_abilities(cursor, data):
    """Import Datasheets_detachment_abilities junction table."""
    print("  Importing Datasheets_detachment_abilities...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_detachment_abilities WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        cursor.execute("""
            INSERT INTO Datasheets_detachment_abilities (datasheet_id, detachment_ability_id)
            VALUES (%(datasheet_id)s, %(detachment_ability_id)s)
        """, row)
    print(f"    Processed {len(data)} datasheet-detachment ability links")


def import_datasheets_leader(cursor, data):
    """Import Datasheets_leader junction table."""
    print("  Importing Datasheets_leader...")

    datasheet_ids = set(row['datasheet_id'] for row in data)

    if datasheet_ids:
        cursor.execute(
            "DELETE FROM Datasheets_leader WHERE datasheet_id = ANY(%s)",
            (list(datasheet_ids),)
        )

    for row in data:
        cursor.execute("""
            INSERT INTO Datasheets_leader (datasheet_id, attached_datasheet_id)
            VALUES (%(datasheet_id)s, %(attached_datasheet_id)s)
        """, row)
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

    conn = None
    cursor = None

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

        # Connect to database
        conn = connect_to_database()
        cursor = conn.cursor()

        # Check if update is needed
        if not check_if_update_needed(cursor, new_timestamp):
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
                    import_func(cursor, csv_data[csv_file])
                else:
                    print(f"  WARNING: No import function for {csv_file}")

        # Commit all changes
        conn.commit()

        # Display summary
        print("\n" + "=" * 70)
        print("Import completed successfully!")
        print("=" * 70)

        cursor.execute("SELECT COUNT(*) FROM Factions")
        print(f"  Factions: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM Datasheets")
        print(f"  Datasheets: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM Stratagems")
        print(f"  Stratagems: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM Abilities")
        print(f"  Abilities: {cursor.fetchone()[0]}")

        cursor.execute("SELECT MAX(last_update) FROM Last_update")
        print(f"  Last update: {cursor.fetchone()[0]}")

        print("=" * 70)

    except psycopg2.Error as e:
        print(f"\n  DATABASE ERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    except requests.RequestException as e:
        print(f"\n  DOWNLOAD ERROR: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n  UNEXPECTED ERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("\n  Database connection closed.")


if __name__ == "__main__":
    main()
