#!/usr/bin/env python3
"""
CSV Download Tester for Wahapedia Data
======================================
This script tests CSV file downloads from web URLs WITHOUT connecting
to the database. Use this to validate your CSV_BASE_URL before importing.

Requirements:
    pip install requests

Usage:
    python 03_test_csv_download.py
"""

import requests
import csv
from io import StringIO
from datetime import datetime
import sys
import os

# Fix Windows console encoding issues
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# CONFIGURATION
# =====================================================================

# PASTE YOUR CSV_BASE_URL HERE
# Example: "https://wahapedia.ru/wh40k10ed/Export/"
CSV_BASE_URL = "http://wahapedia.ru/wh40k10ed/"

# List of all CSV files to test
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

# Expected columns for each CSV file (for validation)
EXPECTED_COLUMNS = {
    "Last_update.csv": ["last_update"],
    "Factions.csv": ["id", "name", "link"],
    "Source.csv": ["id", "name", "type", "edition", "version", "errata_date", "errata_link"],
    "Stratagems.csv": ["id", "faction_id", "name", "type", "cp_cost", "legend", "turn", "phase", "description", "detachment"],
    "Abilities.csv": ["id", "name", "legend", "faction_id", "description"],
    "Enhancements.csv": ["id", "faction_id", "name", "legend", "description", "cost", "detachment"],
    "Detachment_abilities.csv": ["id", "faction_id", "name", "legend", "description", "detachment"],
    "Datasheets.csv": ["id", "name", "faction_id", "source_id", "legend", "role", "loadout", "transport", "virtual", "leader_head", "leader_footer", "damaged_w", "damaged_description", "link"],
    "Datasheets_abilities.csv": ["datasheet_id", "line", "ability_id", "model", "name", "description", "type", "parameter"],
    "Datasheets_keywords.csv": ["datasheet_id", "keyword", "model", "is_faction_keyword"],
    "Datasheets_models.csv": ["datasheet_id", "line", "name", "M", "T", "Sv", "inv_sv", "inv_sv_descr", "W", "Ld", "OC", "base_size", "base_size_descr"],
    "Datasheets_options.csv": ["datasheet_id", "line", "button", "description"],
    "Datasheets_wargear.csv": ["datasheet_id", "line", "line_in_wargear", "dice", "name", "description", "range", "type", "A", "BS_WS", "S", "AP", "D"],
    "Datasheets_unit_composition.csv": ["datasheet_id", "line", "description"],
    "Datasheets_models_cost.csv": ["datasheet_id", "line", "description", "cost"],
    "Datasheets_stratagems.csv": ["datasheet_id", "stratagem_id"],
    "Datasheets_enhancements.csv": ["datasheet_id", "enhancement_id"],
    "Datasheets_detachment_abilities.csv": ["datasheet_id", "detachment_ability_id"],
    "Datasheets_leader.csv": ["datasheet_id", "attached_datasheet_id"],
}

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_success(text):
    """Print success message."""
    print(f"  [OK] {text}")


def print_error(text):
    """Print error message."""
    print(f"  [ERROR] {text}")


def print_warning(text):
    """Print warning message."""
    print(f"  [WARN] {text}")


def print_info(text):
    """Print info message."""
    print(f"  [INFO] {text}")


def test_base_url():
    """Test if base URL is accessible."""
    print_header("Testing Base URL")
    print_info(f"URL: {CSV_BASE_URL}")

    try:
        # Try to access the base URL
        response = requests.head(CSV_BASE_URL, timeout=10, allow_redirects=True)

        if response.status_code == 200:
            print_success("Base URL is accessible (200 OK)")
            return True
        elif response.status_code == 403:
            print_warning("Base URL returned 403 Forbidden (may still work for files)")
            return True  # Some servers block directory listing but allow file access
        elif response.status_code == 404:
            print_error("Base URL not found (404)")
            return False
        else:
            print_warning(f"Base URL returned status code: {response.status_code}")
            return True  # Try to continue anyway

    except requests.RequestException as e:
        print_error(f"Failed to access base URL: {e}")
        return False


def download_and_test_csv(filename):
    """
    Download and test a single CSV file.

    Returns:
        dict with test results
    """
    url = CSV_BASE_URL + filename
    result = {
        "filename": filename,
        "success": False,
        "error": None,
        "row_count": 0,
        "file_size": 0,
        "columns": [],
        "sample_rows": [],
        "validation_issues": []
    }

    try:
        # Download the file
        print(f"\n  Downloading {filename}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Ensure UTF-8 encoding
        response.encoding = 'utf-8'
        content = response.text

        result["file_size"] = len(content.encode('utf-8'))
        print_success(f"Downloaded {len(content.encode('utf-8')):,} bytes")

        # Parse CSV
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file, delimiter='|')

        # Get column names
        result["columns"] = reader.fieldnames
        print_info(f"Columns: {', '.join(result['columns'])}")

        # Validate columns
        if filename in EXPECTED_COLUMNS:
            expected = set(EXPECTED_COLUMNS[filename])
            actual = set(result["columns"])

            missing = expected - actual
            extra = actual - expected

            if missing:
                issue = f"Missing columns: {', '.join(missing)}"
                result["validation_issues"].append(issue)
                print_error(issue)

            if extra:
                issue = f"Extra columns: {', '.join(extra)}"
                result["validation_issues"].append(issue)
                print_warning(issue)

            if not missing and not extra:
                print_success("All expected columns present")

        # Read rows
        rows = list(reader)
        result["row_count"] = len(rows)
        print_success(f"Parsed {result['row_count']:,} rows")

        # Store sample rows (first 3)
        result["sample_rows"] = rows[:3]

        # Check for empty file
        if result["row_count"] == 0:
            issue = "File contains no data rows"
            result["validation_issues"].append(issue)
            print_warning(issue)

        result["success"] = True

    except requests.HTTPError as e:
        result["error"] = f"HTTP Error {e.response.status_code}: {e}"
        print_error(result["error"])

    except requests.RequestException as e:
        result["error"] = f"Download failed: {e}"
        print_error(result["error"])

    except csv.Error as e:
        result["error"] = f"CSV parsing error: {e}"
        print_error(result["error"])

    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
        print_error(result["error"])

    return result


def display_sample_data(results):
    """Display sample data from successful downloads."""
    print_header("Sample Data Preview")

    for result in results:
        if result["success"] and result["sample_rows"]:
            print(f"\n  {result['filename']} (showing first {len(result['sample_rows'])} rows):")
            print("  " + "-" * 66)

            for i, row in enumerate(result["sample_rows"], 1):
                print(f"\n  Row {i}:")
                for key, value in row.items():
                    # Truncate long values
                    display_value = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                    print(f"    {key}: {display_value}")


def display_summary(results):
    """Display summary of all tests."""
    print_header("Summary")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    with_issues = [r for r in results if r["success"] and r["validation_issues"]]

    print(f"\n  Total files tested: {len(results)}")
    print(f"  Successful downloads: {len(successful)}")
    print(f"  Failed downloads: {len(failed)}")
    print(f"  Files with validation issues: {len(with_issues)}")

    if successful:
        total_rows = sum(r["row_count"] for r in successful)
        total_size = sum(r["file_size"] for r in successful)
        print(f"\n  Total rows across all files: {total_rows:,}")
        print(f"  Total download size: {total_size:,} bytes ({total_size/1024:.1f} KB)")

    # Show successful files
    if successful:
        print("\n  [OK] Successfully downloaded:")
        for result in successful:
            status = ""
            if result["validation_issues"]:
                status = " (with warnings)"
            print(f"    - {result['filename']}: {result['row_count']:,} rows{status}")

    # Show failed files
    if failed:
        print("\n  [ERROR] Failed downloads:")
        for result in failed:
            print(f"    - {result['filename']}: {result['error']}")

    # Show validation issues
    if with_issues:
        print("\n  [WARN] Validation issues:")
        for result in with_issues:
            print(f"    - {result['filename']}:")
            for issue in result["validation_issues"]:
                print(f"      > {issue}")

    # Check Last_update.csv specifically
    last_update_result = next((r for r in results if r["filename"] == "Last_update.csv"), None)
    if last_update_result and last_update_result["success"] and last_update_result["sample_rows"]:
        last_update_time = last_update_result["sample_rows"][0].get("last_update")
        if last_update_time:
            print(f"\n  [INFO] Data last updated: {last_update_time} (GMT+3)")

    # Final verdict
    print("\n" + "=" * 70)
    if len(successful) == len(results) and not with_issues:
        print("  ALL TESTS PASSED - Ready to import!")
        print("=" * 70)
        return True
    elif len(successful) == len(results):
        print("  All files downloaded (with some warnings)")
        print("  Review warnings above before importing")
        print("=" * 70)
        return True
    else:
        print("  SOME TESTS FAILED - Fix issues before importing")
        print("=" * 70)
        return False


def main():
    """Main execution function."""
    print_header("Wahapedia CSV Download Tester")
    print_info(f"Testing {len(CSV_FILES)} CSV files")
    print_info(f"Base URL: {CSV_BASE_URL}")

    # Test base URL first
    if not test_base_url():
        print_error("\nBase URL test failed. Please check your CSV_BASE_URL.")
        print_info("Edit this script and update the CSV_BASE_URL variable.")
        sys.exit(1)

    # Test each CSV file
    print_header("Testing Individual CSV Files")
    results = []

    for filename in CSV_FILES:
        result = download_and_test_csv(filename)
        results.append(result)

    # Display sample data
    display_sample_data(results)

    # Display summary
    success = display_summary(results)

    # Exit with appropriate code
    if success:
        print("\n[OK] Testing complete! You can now run 03_import_from_web.py")
        sys.exit(0)
    else:
        print("\n[ERROR] Testing failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
