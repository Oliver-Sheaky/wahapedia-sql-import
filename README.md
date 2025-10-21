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
2. **02_upsert_data.sql** - Imports CSV data from local files without duplication
3. **03_import_from_web.py** - Python script to download and import CSVs from web URLs
4. **README.md** - This documentation file

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

There are two methods to import data: **from web URLs** (recommended for Supabase) or **from local CSV files**.

### Method 1: Import from Web URLs (Recommended for Supabase)

This method downloads CSVs directly from web URLs and imports them into your local Supabase database.

#### Prerequisites

Install required Python packages:
```bash
pip install psycopg2-binary requests python-dotenv
```

#### Step 1: Create the Database Schema

Run the table creation script first:

```bash
# For local Supabase (default port 54322)
psql -h localhost -p 54322 -U postgres -d postgres -f 01_create_tables.sql
```

#### Step 2: Configure the Python Script

Edit [03_import_from_web.py](C:\Users\Ollie\Downloads\03_import_from_web.py) and update:

1. **CSV_BASE_URL** - The base URL where CSV files are hosted
   ```python
   CSV_BASE_URL = "https://wahapedia.ru/wh40k10ed/Export/"
   ```

2. **DATABASE_CONFIG** - Your local Supabase connection details
   ```python
   DATABASE_CONFIG = {
       "host": "localhost",
       "port": 54322,  # Default Supabase local port
       "database": "postgres",
       "user": "postgres",
       "password": "your_password_here",
   }
   ```

Alternatively, create a `.env` file:
```env
DB_HOST=localhost
DB_PORT=54322
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password_here
```

#### Step 3: Run the Import Script

```bash
python 03_import_from_web.py
```

The script will:
1. Download `Last_update.csv` and check if new data is available
2. Skip import if data is already up-to-date
3. Download all CSV files from the web
4. Import data in the correct order respecting foreign keys
5. Handle duplicates intelligently with UPSERT logic
6. Display a summary of imported records

**Features:**
- ✅ Downloads directly from web URLs (no local CSV files needed)
- ✅ Automatic update checking via timestamp comparison
- ✅ Handles missing or failed downloads gracefully
- ✅ Converts boolean and integer fields properly
- ✅ Transaction-based (rolls back on errors)

---

### Method 2: Import from Local CSV Files

If you already have CSV files downloaded locally, use this method.

#### Step 1: Create the Database Schema

```bash
# For PostgreSQL/Supabase
psql -h localhost -p 54322 -U postgres -d postgres -f 01_create_tables.sql

# For SQL Server
sqlcmd -S your_server -d your_database -i 01_create_tables.sql

# For MySQL
mysql -u your_username -p your_database < 01_create_tables.sql
```

#### Step 2: Configure CSV File Paths

Edit [02_upsert_data.sql](C:\Users\Ollie\Downloads\02_upsert_data.sql) and replace all instances of `'path/to/csv/'` with your actual CSV directory path.

**Example:**
```sql
-- Change this:
COPY temp_factions FROM 'path/to/csv/Factions.csv'

-- To this (Windows):
COPY temp_factions FROM 'C:/Users/YourName/Downloads/Wahapedia_CSV/Factions.csv'

-- Or this (Linux/Mac):
COPY temp_factions FROM '/home/username/wahapedia/Factions.csv'
```

#### Step 3: Run the Data Ingestion Script

```bash
# For PostgreSQL/Supabase
psql -h localhost -p 54322 -U postgres -d postgres -f 02_upsert_data.sql
```

The script will:
1. Check if new data is available by comparing timestamps
2. Skip import if data is already up-to-date
3. Import all CSV files in the correct order
4. Handle duplicates intelligently with UPSERT logic

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

The `02_upsert_data.sql` script follows this order automatically.

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

### PostgreSQL (Primary Target)
The scripts are written for PostgreSQL but include notes for other databases.

**Features used:**
- COPY command for CSV import
- TEMP TABLE for staging
- MERGE statements for UPSERT
- BOOLEAN data type
- TEXT data type

### SQL Server Adaptation
Replace the following:

```sql
-- Data Types
TIMESTAMP → DATETIME2
TEXT → VARCHAR(MAX)
CURRENT_TIMESTAMP → GETDATE()

-- CSV Import
COPY → BULK INSERT
TEMP TABLE → #temp_table

-- Example:
BULK INSERT #temp_factions
FROM 'C:\path\to\Factions.csv'
WITH (
    FIELDTERMINATOR = '|',
    ROWTERMINATOR = '\n',
    FIRSTROW = 2,
    CODEPAGE = '65001'  -- UTF-8
);
```

### MySQL Adaptation
Replace the following:

```sql
-- Data Types
TIMESTAMP → DATETIME
(TEXT is compatible)
(BOOLEAN converts to TINYINT automatically)

-- CSV Import
COPY → LOAD DATA INFILE
TEMP TABLE → TEMPORARY TABLE
MERGE → INSERT ... ON DUPLICATE KEY UPDATE

-- Example:
LOAD DATA INFILE '/path/to/Factions.csv'
INTO TABLE temp_factions
FIELDS TERMINATED BY '|'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(id, name, link);
```

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

### Foreign Key Constraint Errors
**Problem**: Import fails due to missing parent records

**Solution**: Ensure CSVs are complete and reference data exists
```sql
-- Check for orphaned references
SELECT DISTINCT faction_id FROM Datasheets
WHERE faction_id NOT IN (SELECT id FROM Factions);
```

### Duplicate Key Errors
**Problem**: Primary key violations

**Solution**: This shouldn't happen with MERGE statements, but if it does:
```sql
-- Find duplicates in CSV before import
SELECT id, COUNT(*) FROM temp_factions GROUP BY id HAVING COUNT(*) > 1;
```

### CSV Import Errors
**Problem**: COPY command fails

**Solution**: Check file permissions and encoding
```sql
-- Verify file path and permissions
-- Ensure UTF-8 encoding (no BOM)
-- Confirm pipe delimiter
```

### Boolean Conversion Issues
**Problem**: "true"/"false" strings not converting

**Solution**: The script handles this with CASE statements:
```sql
CASE WHEN LOWER(virtual) = 'true' THEN true ELSE false END
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
Simply run `02_upsert_data.sql` again. The script will:
1. Check if data is newer
2. Update only changed records
3. Skip if already current

## License & Credits

This system is designed for use with Wahapedia export data. All game content is © Games Workshop.

The SQL schema and ingestion scripts are provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify your CSV files match the expected format
3. Ensure your SQL database supports the required features
4. Review the database-specific adaptation notes

## Version History

- **v1.0** - Initial release with full schema and UPSERT logic
