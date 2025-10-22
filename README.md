# Wahapedia Export Data SQL Ingestion System

A comprehensive SQL database system for importing and managing Wahapedia export data with smart update detection and duplicate prevention.

## Overview

This system provides a robust solution for importing Warhammer 40K data from Wahapedia CSV exports into a relational SQL database. It includes:

- **Normalized database schema** with proper foreign key relationships
- **Smart update detection** using timestamp comparison
- **Duplicate prevention** through UPSERT logic
- **Data integrity** with foreign key constraints and indexes

## Files Included

1. **01_create_tables.sql** - Creates the complete database schema
2. **02_import_from_web.py** - Python script to download and import CSVs from web URLs
3. **03_test_csv_download.py** - Test script to validate CSV downloads without database
4. **README.md** - This documentation file
5. **example.env** - Configuration template

## Database Schema

### Core Reference Tables

- **Factions** - All factions and subfactions
- **Source** - Rulebooks, supplements, and errata information
- **Last_update** - Timestamp tracking for update detection

### Datasheets and Related Tables

The central `Datasheets` table stores all unit datasheets, with several child tables:

- **Datasheets_abilities** - Unit abilities
- **Datasheets_keywords** - Unit keywords (including faction keywords)
- **Datasheets_models** - Model statistics (M, T, Sv, W, Ld, OC, etc.)
- **Datasheets_options** - Wargear options
- **Datasheets_wargear** - Weapons and wargear with full profiles
- **Datasheets_unit_composition** - Unit composition rules
- **Datasheets_models_cost** - Point costs

### Junction Tables (Many-to-Many)

- **Datasheets_stratagems** - Links datasheets to available stratagems
- **Datasheets_enhancements** - Links datasheets to available enhancements
- **Datasheets_detachment_abilities** - Links datasheets to detachment abilities
- **Datasheets_leader** - Links leader units to units they can attach to

### Game Content Tables

- **Stratagems** - All stratagems with costs and phases
- **Abilities** - Faction and universal abilities
- **Enhancements** - Character enhancements with costs
- **Detachment_abilities** - Detachment-specific abilities

## Entity Relationship Diagram

```
Factions
   ├─→ Datasheets
   │     ├─→ Datasheets_abilities
   │     ├─→ Datasheets_keywords
   │     ├─→ Datasheets_models
   │     ├─→ Datasheets_options
   │     ├─→ Datasheets_wargear
   │     ├─→ Datasheets_unit_composition
   │     ├─→ Datasheets_models_cost
   │     ├─→ Datasheets_stratagems ←─┐
   │     ├─→ Datasheets_enhancements ←─┤
   │     ├─→ Datasheets_detachment_abilities ←─┤
   │     └─→ Datasheets_leader (self-referential)
   │
   ├─→ Stratagems ←──────────────┘
   ├─→ Abilities
   ├─→ Enhancements ←────────────┘
   └─→ Detachment_abilities ←────┘

Source
   └─→ Datasheets
```

## Installation & Usage

### Prerequisites

Install required Python packages:
```bash
pip install supabase requests python-dotenv
```

### Step 1: Create the Database Schema

Run the table creation script to set up your Supabase database:

```bash
# For local Supabase - run from your Supabase project directory
cd path/to/your/supabase-project
supabase db reset  # If needed to start fresh

# Or manually via psql
psql -h localhost -p 54322 -U postgres -d postgres -f 01_create_tables.sql
```

### Step 2: Configure Environment Variables

Copy `example.env` to `.env` and update with your Supabase credentials:

```env
# CSV Base URL - Where the CSV files are hosted
CSV_BASE_URL=http://wahapedia.ru/wh40k10ed/

# Supabase Configuration
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=your-service-role-key-here
```

**Finding your Supabase credentials:**
- `SUPABASE_URL`: For local Supabase, use `http://localhost:8000` (Kong API gateway)
- `SUPABASE_KEY`: Find in your Supabase project's `.env` file as `SERVICE_ROLE_KEY`

### Step 3: Run the Import Script

```bash
python 02_import_from_web.py
```

The script will:
1. ✅ Download `Last_update.csv` and check if new data is available
2. ✅ Skip import if data is already up-to-date
3. ✅ Download all CSV files from the web (with rate limiting)
4. ✅ Import data in the correct order respecting foreign keys
5. ✅ Handle duplicates, orphaned records, and schema mismatches automatically
6. ✅ Display a detailed summary of imported records

**Import Statistics (typical run):**
- 26 factions
- 1,656 datasheets
- 1,272 stratagems
- 120,000+ total records across 19 tables

### Step 4: (Optional) Test CSV Downloads

Before running the full import, you can test that CSV downloads work:

```bash
python 03_test_csv_download.py
```

This validates the CSV_BASE_URL and checks file accessibility without touching the database

## Error Handling & Automatic Workarounds

The import script includes comprehensive error handling that automatically resolves common data quality issues:

### 1. Date Format Conversion

**Issue**: CSV files contain dates in DD.MM.YYYY format, but PostgreSQL expects YYYY-MM-DD

**Automatic Fix**: The script automatically converts date formats:
```python
# Example: "09.07.2025" → "2025-07-09"
def convert_date(value):
    date_part = value.split(' ')[0]  # Remove time portion
    parts = date_part.split('.')
    if len(parts) == 3:
        day, month, year = parts
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
```

**Impact**: Errata dates are automatically formatted correctly during import.

### 2. Foreign Key Validation

**Issue**: CSV files may reference IDs that don't exist in parent tables (orphaned records)

**Automatic Fix**: The script validates all foreign keys before insertion:
```python
# Example: Skip abilities that reference non-existent ability_id
abilities_response = supabase.table('abilities').select('id').execute()
valid_ability_ids = set(row['id'] for row in abilities_response.data)

if row['ability_id'] not in valid_ability_ids:
    # Skip this record
    continue
```

**Impact**: Orphaned records are automatically filtered out, preventing foreign key constraint violations.

### 3. Duplicate Record Handling

**Issue**: CSV files may contain duplicate IDs

**Automatic Fix**: The script deduplicates records before insertion:
```python
# Keep only the last occurrence of each ID
seen_ids = {}
for row in data:
    seen_ids[row['id']] = row
deduplicated_data = list(seen_ids.values())
```

**Impact**: Prevents "ON CONFLICT DO UPDATE command cannot affect row a second time" errors.

### 4. Empty Foreign Key Defaults

**Issue**: Some records have empty strings for required foreign key fields

**Automatic Fix**: The script applies sensible defaults:
```python
# Default to 'UN' (Unaligned Forces) for empty faction_id
if row.get('faction_id') == '':
    row['faction_id'] = 'UN'

# Default to generic source for empty source_id
if row.get('source_id') == '':
    row['source_id'] = '000000012'
```

**Impact**: Records with missing foreign keys are assigned to default categories.

### 5. Schema Column Mapping

**Issue**: CSV column names don't always match database schema (uppercase vs lowercase, different names)

**Automatic Fix**: The script maps CSV columns to database columns:
```python
# Uppercase to lowercase mapping
if 'M' in row: row['m'] = row.pop('M')
if 'T' in row: row['t'] = row.pop('T')
if 'Ld' in row: row['ld'] = row.pop('Ld')

# Different column names
if 'leader_id' in row: row['datasheet_id'] = row.pop('leader_id')
if 'attached_id' in row: row['attached_datasheet_id'] = row.pop('attached_id')
```

**Impact**: No manual CSV editing required - schema differences are handled automatically.

### 6. Rate Limiting

**Issue**: Downloading too many CSV files too quickly may trigger HTTP 429 "Too Many Requests" errors

**Automatic Fix**: The script includes a 0.5-second delay between downloads:
```python
DOWNLOAD_DELAY_SECONDS = 0.5

def download_csv(url):
    # ... download logic ...
    time.sleep(DOWNLOAD_DELAY_SECONDS)  # Rate limiting
```

**Impact**: Prevents overwhelming the Wahapedia server with requests.

### 7. Composite Key Deduplication

**Issue**: Child tables with composite primary keys may have duplicate combinations

**Automatic Fix**: The script deduplicates by composite key:
```python
# Example: Datasheets_keywords uses (datasheet_id, keyword) as primary key
seen_keys = {}
for row in data:
    key = (row['datasheet_id'], row['keyword'])
    seen_keys[key] = row
deduplicated_data = list(seen_keys.values())
```

**Impact**: Prevents composite primary key violations in junction tables.

### Summary of Automatic Fixes

All these workarounds are applied automatically during import - no manual intervention required:

- ✅ Date format conversion (DD.MM.YYYY → YYYY-MM-DD)
- ✅ Orphaned foreign key filtering
- ✅ Duplicate record deduplication
- ✅ Empty foreign key defaults ('UN' for factions, '000000012' for sources)
- ✅ Schema column name mapping (M→m, leader_id→datasheet_id, etc.)
- ✅ HTTP rate limiting (0.5s delay between downloads)
- ✅ Composite key deduplication for junction tables

The script reports skipped/modified records during import so you can track what data quality issues were encountered.

## Smart Update Detection

### How It Works

The system uses the `Last_update.csv` file to determine if new data should be imported:

1. **First Import**: When the database is empty, all data is imported
2. **Subsequent Runs**: The script compares the new timestamp with the existing one
3. **Skip if Current**: If the data hasn't changed, the import is skipped
4. **Update if Newer**: Only proceeds if new data is available

### Benefits

- **Saves time**: No unnecessary re-imports
- **Preserves data**: Avoids overwriting unchanged data
- **Automatic**: No manual intervention required

## Duplicate Prevention

### UPSERT Logic

The ingestion script uses MERGE statements (PostgreSQL) to handle existing records:

- **INSERT**: New records are added
- **UPDATE**: Existing records are updated with new values
- **NO DUPLICATES**: Primary key constraints prevent duplicate entries

### Child Table Strategy

For child tables (like `Datasheets_abilities`), the script:
1. Deletes existing records for updated datasheets
2. Inserts fresh data
3. Ensures complete consistency

This approach handles scenarios where:
- Abilities are added to a unit
- Abilities are removed from a unit
- Ability details are modified

## Data Types & Formats

### CSV Format
- **Delimiter**: `|` (pipe/vertical bar)
- **Encoding**: UTF-8
- **Header Row**: First row contains column names

### Boolean Fields
- Stored as strings "true" or "false" in CSV
- Converted to SQL BOOLEAN type during import

### HTML Fields
Fields like `description`, `legend`, and `abilities` contain HTML markup:
- Stored as TEXT type
- Use website stylesheets for proper rendering

### Date/Time Fields
- **errata_date**: DATE format
- **last_update**: TIMESTAMP format (yyyy-MM-dd HH:mm:ss, GMT+3)

## Foreign Key Relationships

The database enforces referential integrity through foreign keys:

### Datasheets References
```sql
Datasheets.faction_id → Factions.id
Datasheets.source_id → Source.id
```

### Child Table References
```sql
Datasheets_*.datasheet_id → Datasheets.id
```

### Game Content References
```sql
Stratagems.faction_id → Factions.id
Abilities.faction_id → Factions.id
Enhancements.faction_id → Factions.id
Detachment_abilities.faction_id → Factions.id
```

### Junction Table References
```sql
Datasheets_stratagems.datasheet_id → Datasheets.id
Datasheets_stratagems.stratagem_id → Stratagems.id
```

## Load Order

**Critical**: Data must be loaded in this order to satisfy foreign key constraints:

1. **Factions** (no dependencies)
2. **Source** (no dependencies)
3. **Last_update** (no dependencies)
4. **Stratagems, Abilities, Enhancements, Detachment_abilities** (depend on Factions)
5. **Datasheets** (depends on Factions and Source)
6. **Datasheets_* child tables** (depend on Datasheets)
7. **Junction tables** (depend on both parent tables)

The [02_import_from_web.py](02_import_from_web.py) script follows this order automatically.

## Performance Optimizations

### Indexes
The schema includes indexes on:
- All foreign key columns
- Date fields (for time-based queries)
- Frequently queried columns

### Composite Primary Keys
Child tables use composite primary keys (e.g., `datasheet_id + line`) for:
- Data integrity
- Efficient lookups
- Proper ordering

## Database Compatibility

### Supabase / PostgreSQL (Primary Target)

This system is designed for **Supabase** (PostgreSQL-based) using the official Supabase Python client.

**Connection Method:**
- Uses Supabase Python client (`supabase-py`) instead of direct PostgreSQL connection
- Connects via Kong API gateway (port 8000) which bypasses Supavisor tenant authentication
- Requires `SUPABASE_URL` and `SUPABASE_KEY` (service role key) from your Supabase project

**Features used:**
- Supabase table operations (`.select()`, `.upsert()`, `.insert()`, `.delete()`)
- BOOLEAN data type
- TEXT data type
- DATE and TIMESTAMP data types
- Foreign key constraints
- Composite primary keys

**Local Supabase Setup:**
- Install Supabase CLI: `npm install -g supabase`
- Initialize project: `supabase init`
- Start services: `supabase start`
- Apply schema: `supabase db reset` or `psql -h localhost -p 54322 -U postgres -d postgres -f 01_create_tables.sql`

**Cloud Supabase:**
- Update `SUPABASE_URL` to your project URL (e.g., `https://xxxx.supabase.co`)
- Use the service role key from your project settings

## Example Queries

### Get all datasheets for a faction
```sql
SELECT d.name, d.role, f.name as faction
FROM Datasheets d
JOIN Factions f ON d.faction_id = f.id
WHERE f.name = 'Adeptus Custodes'
ORDER BY d.name;
```

### Get a unit's complete wargear profile
```sql
SELECT w.name, w.range, w.type, w.A, w.BS_WS, w.S, w.AP, w.D
FROM Datasheets_wargear w
WHERE w.datasheet_id = 'your_datasheet_id'
ORDER BY w.line, w.line_in_wargear;
```

### Get all stratagems for a datasheet
```sql
SELECT s.name, s.type, s.cp_cost, s.phase
FROM Stratagems s
JOIN Datasheets_stratagems ds ON s.id = ds.stratagem_id
WHERE ds.datasheet_id = 'your_datasheet_id';
```

### Find which units a leader can attach to
```sql
SELECT d1.name as leader, d2.name as can_attach_to
FROM Datasheets_leader dl
JOIN Datasheets d1 ON dl.datasheet_id = d1.id
JOIN Datasheets d2 ON dl.attached_datasheet_id = d2.id
WHERE d1.name = 'Captain';
```

### Check last update timestamp
```sql
SELECT MAX(last_update) as latest_data_version
FROM Last_update;
```

## Troubleshooting

### Connection Issues

**Problem**: "Tenant or user not found" errors when connecting

**Solution**: Ensure you're using the Supabase Python client (not direct PostgreSQL connection):
- Use `SUPABASE_URL=http://localhost:8000` (Kong gateway, not direct Postgres port)
- Use service role key from your Supabase project's `.env` file
- Verify Supabase is running: `supabase status`

### Import Script Errors

**Problem**: Missing Python modules

**Solution**: Install required packages:
```bash
pip install supabase requests python-dotenv
```

**Problem**: HTTP 429 "Too Many Requests" errors

**Solution**: The script includes automatic rate limiting (0.5s delay). If you still encounter issues, increase `DOWNLOAD_DELAY_SECONDS` in [02_import_from_web.py](02_import_from_web.py).

**Problem**: Foreign key constraint errors

**Solution**: These are handled automatically by the script - it validates all foreign keys before insertion and skips orphaned records. Check the import summary for "skipped" record counts.

**Problem**: Date format errors

**Solution**: Handled automatically - the script converts DD.MM.YYYY to YYYY-MM-DD format.

### Database Queries

**Problem**: Finding orphaned references after import

**Solution**: Check for data quality issues:
```sql
-- Check for orphaned datasheets (shouldn't happen with automatic validation)
SELECT DISTINCT faction_id FROM Datasheets
WHERE faction_id NOT IN (SELECT id FROM Factions);

-- Verify all foreign key relationships
SELECT COUNT(*) as orphaned_datasheets
FROM Datasheets d
WHERE NOT EXISTS (SELECT 1 FROM Factions f WHERE f.id = d.faction_id);
```

## Maintenance

### Backing Up Data
```sql
-- PostgreSQL
pg_dump -U username -d database_name > wahapedia_backup.sql

-- SQL Server
BACKUP DATABASE database_name TO DISK = 'C:\backup\wahapedia.bak';

-- MySQL
mysqldump -u username -p database_name > wahapedia_backup.sql
```

### Checking Data Integrity
```sql
-- Count records in each table
SELECT 'Factions' as table_name, COUNT(*) FROM Factions
UNION ALL
SELECT 'Datasheets', COUNT(*) FROM Datasheets
UNION ALL
SELECT 'Stratagems', COUNT(*) FROM Stratagems;

-- Verify foreign key relationships
SELECT COUNT(*) as orphaned_datasheets
FROM Datasheets d
WHERE NOT EXISTS (SELECT 1 FROM Factions f WHERE f.id = d.faction_id);
```

### Re-importing Data
Simply run [02_import_from_web.py](02_import_from_web.py) again. The script will:
1. Check if data is newer (via `Last_update.csv` timestamp comparison)
2. Update only changed records (using `.upsert()` for parent tables)
3. Skip import entirely if data hasn't changed

**Manual re-import**: To force a full re-import even if timestamps match, delete all records from the `Last_update` table first:
```sql
DELETE FROM Last_update;
```

## License & Credits

This system is designed for use with Wahapedia export data. All game content is © Games Workshop.

The SQL schema and ingestion scripts are provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the [Error Handling & Automatic Workarounds](#error-handling--automatic-workarounds) section
2. Review the [Troubleshooting](#troubleshooting) section
3. Verify your Supabase connection settings in `.env`
4. Check that Supabase is running: `supabase status`
5. Review import logs for skipped/modified record counts

## Version History

- **v2.0** - Major refactor to use Supabase Python client
  - Switched from psycopg2 to supabase-py library
  - Added comprehensive error handling and automatic workarounds
  - Added rate limiting for CSV downloads
  - Simplified workflow (removed SQL-based import method)
  - Added automatic data quality fixes (date conversion, deduplication, foreign key validation)

- **v1.0** - Initial release with full schema and SQL-based UPSERT logic
