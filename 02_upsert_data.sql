-- =====================================================================
-- SQL Data Ingestion Script for Wahapedia Export Data
-- =====================================================================
-- This script provides UPSERT (INSERT or UPDATE) logic for all tables
-- to prevent duplication and ensure data integrity.
--
-- Features:
-- - Checks Last_update.csv to determine if new data is available
-- - Uses MERGE statements to handle existing records intelligently
-- - Respects foreign key constraints by loading in correct order
-- - Idempotent: can be run multiple times without creating duplicates
--
-- IMPORTANT: Replace 'path/to/csv/' with your actual CSV file directory
-- CSV Format: Pipe-delimited (|), UTF-8 encoded
-- =====================================================================

-- =====================================================================
-- STEP 1: CHECK IF UPDATE IS NEEDED
-- =====================================================================
-- First, load the new Last_update timestamp to compare with existing data

-- Create temporary table for the new update timestamp
CREATE TEMP TABLE temp_last_update (
    last_update TIMESTAMP
);

-- Load the Last_update.csv file
-- NOTE: Adjust the file path to match your CSV directory
COPY temp_last_update FROM 'path/to/csv/Last_update.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

-- Check if we need to update by comparing timestamps
DO $$
DECLARE
    new_update_time TIMESTAMP;
    existing_update_time TIMESTAMP;
BEGIN
    -- Get the new update timestamp
    SELECT last_update INTO new_update_time FROM temp_last_update LIMIT 1;

    -- Get the most recent existing update timestamp
    SELECT MAX(last_update) INTO existing_update_time FROM Last_update;

    -- If data is not newer, exit early
    IF existing_update_time IS NOT NULL AND new_update_time <= existing_update_time THEN
        RAISE NOTICE 'Data is already up to date. Last update: %', existing_update_time;
        RAISE EXCEPTION 'SKIP_UPDATE'; -- This will rollback the transaction
    ELSE
        RAISE NOTICE 'Proceeding with data update. New timestamp: %', new_update_time;
    END IF;
END $$;

-- =====================================================================
-- STEP 2: LOAD REFERENCE TABLES
-- These tables must be loaded first due to foreign key dependencies
-- =====================================================================

-- ---------------------------------------------------------------------
-- FACTIONS TABLE
-- ---------------------------------------------------------------------
-- Load factions data into temporary table
CREATE TEMP TABLE temp_factions (
    id VARCHAR(100),
    name VARCHAR(255),
    link VARCHAR(500)
);

COPY temp_factions FROM 'path/to/csv/Factions.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

-- Upsert into Factions table
MERGE INTO Factions AS target
USING temp_factions AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        name = source.name,
        link = source.link,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, name, link)
    VALUES (source.id, source.name, source.link);

DROP TABLE temp_factions;

-- ---------------------------------------------------------------------
-- SOURCE TABLE
-- ---------------------------------------------------------------------
-- Load source data into temporary table
CREATE TEMP TABLE temp_source (
    id VARCHAR(100),
    name VARCHAR(255),
    type VARCHAR(100),
    edition VARCHAR(50),
    version VARCHAR(50),
    errata_date DATE,
    errata_link VARCHAR(500)
);

COPY temp_source FROM 'path/to/csv/Source.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

-- Upsert into Source table
MERGE INTO Source AS target
USING temp_source AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        name = source.name,
        type = source.type,
        edition = source.edition,
        version = source.version,
        errata_date = source.errata_date,
        errata_link = source.errata_link,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, name, type, edition, version, errata_date, errata_link)
    VALUES (source.id, source.name, source.type, source.edition, source.version,
            source.errata_date, source.errata_link);

DROP TABLE temp_source;

-- ---------------------------------------------------------------------
-- LAST_UPDATE TABLE
-- ---------------------------------------------------------------------
-- Insert the new update timestamp (we already loaded it in temp_last_update)
INSERT INTO Last_update (last_update)
SELECT last_update FROM temp_last_update
ON CONFLICT (last_update) DO NOTHING;

DROP TABLE temp_last_update;

-- =====================================================================
-- STEP 3: LOAD GAME CONTENT TABLES
-- These must be loaded before their junction tables
-- =====================================================================

-- ---------------------------------------------------------------------
-- STRATAGEMS TABLE
-- ---------------------------------------------------------------------
CREATE TEMP TABLE temp_stratagems (
    id VARCHAR(100),
    faction_id VARCHAR(100),
    name VARCHAR(255),
    type VARCHAR(255),
    cp_cost VARCHAR(50),
    legend TEXT,
    turn VARCHAR(100),
    phase VARCHAR(100),
    description TEXT,
    detachment VARCHAR(255)
);

COPY temp_stratagems FROM 'path/to/csv/Stratagems.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

MERGE INTO Stratagems AS target
USING temp_stratagems AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        faction_id = source.faction_id,
        name = source.name,
        type = source.type,
        cp_cost = source.cp_cost,
        legend = source.legend,
        turn = source.turn,
        phase = source.phase,
        description = source.description,
        detachment = source.detachment,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, faction_id, name, type, cp_cost, legend, turn, phase, description, detachment)
    VALUES (source.id, source.faction_id, source.name, source.type, source.cp_cost,
            source.legend, source.turn, source.phase, source.description, source.detachment);

DROP TABLE temp_stratagems;

-- ---------------------------------------------------------------------
-- ABILITIES TABLE
-- ---------------------------------------------------------------------
CREATE TEMP TABLE temp_abilities (
    id VARCHAR(100),
    name VARCHAR(255),
    legend TEXT,
    faction_id VARCHAR(100),
    description TEXT
);

COPY temp_abilities FROM 'path/to/csv/Abilities.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

MERGE INTO Abilities AS target
USING temp_abilities AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        name = source.name,
        legend = source.legend,
        faction_id = source.faction_id,
        description = source.description,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, name, legend, faction_id, description)
    VALUES (source.id, source.name, source.legend, source.faction_id, source.description);

DROP TABLE temp_abilities;

-- ---------------------------------------------------------------------
-- ENHANCEMENTS TABLE
-- ---------------------------------------------------------------------
CREATE TEMP TABLE temp_enhancements (
    id VARCHAR(100),
    faction_id VARCHAR(100),
    name VARCHAR(255),
    legend TEXT,
    description TEXT,
    cost VARCHAR(50),
    detachment VARCHAR(255)
);

COPY temp_enhancements FROM 'path/to/csv/Enhancements.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

MERGE INTO Enhancements AS target
USING temp_enhancements AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        faction_id = source.faction_id,
        name = source.name,
        legend = source.legend,
        description = source.description,
        cost = source.cost,
        detachment = source.detachment,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, faction_id, name, legend, description, cost, detachment)
    VALUES (source.id, source.faction_id, source.name, source.legend, source.description,
            source.cost, source.detachment);

DROP TABLE temp_enhancements;

-- ---------------------------------------------------------------------
-- DETACHMENT_ABILITIES TABLE
-- ---------------------------------------------------------------------
CREATE TEMP TABLE temp_detachment_abilities (
    id VARCHAR(100),
    faction_id VARCHAR(100),
    name VARCHAR(255),
    legend TEXT,
    description TEXT,
    detachment VARCHAR(255)
);

COPY temp_detachment_abilities FROM 'path/to/csv/Detachment_abilities.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

MERGE INTO Detachment_abilities AS target
USING temp_detachment_abilities AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        faction_id = source.faction_id,
        name = source.name,
        legend = source.legend,
        description = source.description,
        detachment = source.detachment,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, faction_id, name, legend, description, detachment)
    VALUES (source.id, source.faction_id, source.name, source.legend, source.description,
            source.detachment);

DROP TABLE temp_detachment_abilities;

-- =====================================================================
-- STEP 4: LOAD DATASHEETS TABLE
-- This is the central table that many other tables reference
-- =====================================================================

CREATE TEMP TABLE temp_datasheets (
    id VARCHAR(100),
    name VARCHAR(255),
    faction_id VARCHAR(100),
    source_id VARCHAR(100),
    legend TEXT,
    role VARCHAR(100),
    loadout TEXT,
    transport TEXT,
    virtual VARCHAR(10),  -- Will be converted to boolean
    leader_head TEXT,
    leader_footer TEXT,
    damaged_w VARCHAR(50),
    damaged_description TEXT,
    link VARCHAR(500)
);

COPY temp_datasheets FROM 'path/to/csv/Datasheets.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

-- Convert "true"/"false" strings to boolean and upsert
MERGE INTO Datasheets AS target
USING (
    SELECT
        id, name, faction_id, source_id, legend, role, loadout, transport,
        CASE WHEN LOWER(virtual) = 'true' THEN true ELSE false END as virtual,
        leader_head, leader_footer, damaged_w, damaged_description, link
    FROM temp_datasheets
) AS source
ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        name = source.name,
        faction_id = source.faction_id,
        source_id = source.source_id,
        legend = source.legend,
        role = source.role,
        loadout = source.loadout,
        transport = source.transport,
        virtual = source.virtual,
        leader_head = source.leader_head,
        leader_footer = source.leader_footer,
        damaged_w = source.damaged_w,
        damaged_description = source.damaged_description,
        link = source.link,
        date_imported = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (id, name, faction_id, source_id, legend, role, loadout, transport, virtual,
            leader_head, leader_footer, damaged_w, damaged_description, link)
    VALUES (source.id, source.name, source.faction_id, source.source_id, source.legend,
            source.role, source.loadout, source.transport, source.virtual, source.leader_head,
            source.leader_footer, source.damaged_w, source.damaged_description, source.link);

DROP TABLE temp_datasheets;

-- =====================================================================
-- STEP 5: LOAD DATASHEETS CHILD TABLES
-- These tables depend on Datasheets table
-- =====================================================================

-- ---------------------------------------------------------------------
-- DATASHEETS_ABILITIES TABLE
-- ---------------------------------------------------------------------
-- First, delete existing records for datasheets we're updating
-- This ensures we don't have orphaned records
DELETE FROM Datasheets_abilities WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_abilities
);

CREATE TEMP TABLE temp_datasheets_abilities (
    datasheet_id VARCHAR(100),
    line INT,
    ability_id VARCHAR(100),
    model VARCHAR(255),
    name VARCHAR(255),
    description TEXT,
    type VARCHAR(100),
    parameter VARCHAR(255)
);

COPY temp_datasheets_abilities FROM 'path/to/csv/Datasheets_abilities.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_abilities
    (datasheet_id, line, ability_id, model, name, description, type, parameter)
SELECT datasheet_id, line, ability_id, model, name, description, type, parameter
FROM temp_datasheets_abilities;

DROP TABLE temp_datasheets_abilities;

-- ---------------------------------------------------------------------
-- DATASHEETS_KEYWORDS TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_keywords WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_keywords
);

CREATE TEMP TABLE temp_datasheets_keywords (
    datasheet_id VARCHAR(100),
    keyword VARCHAR(100),
    model VARCHAR(255),
    is_faction_keyword VARCHAR(10)
);

COPY temp_datasheets_keywords FROM 'path/to/csv/Datasheets_keywords.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_keywords (datasheet_id, keyword, model, is_faction_keyword)
SELECT
    datasheet_id,
    keyword,
    model,
    CASE WHEN LOWER(is_faction_keyword) = 'true' THEN true ELSE false END
FROM temp_datasheets_keywords;

DROP TABLE temp_datasheets_keywords;

-- ---------------------------------------------------------------------
-- DATASHEETS_MODELS TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_models WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_models
);

CREATE TEMP TABLE temp_datasheets_models (
    datasheet_id VARCHAR(100),
    line INT,
    name VARCHAR(255),
    M VARCHAR(50),
    T VARCHAR(50),
    Sv VARCHAR(50),
    inv_sv VARCHAR(50),
    inv_sv_descr TEXT,
    W VARCHAR(50),
    Ld VARCHAR(50),
    OC VARCHAR(50),
    base_size VARCHAR(100),
    base_size_descr TEXT
);

COPY temp_datasheets_models FROM 'path/to/csv/Datasheets_models.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_models
    (datasheet_id, line, name, M, T, Sv, inv_sv, inv_sv_descr, W, Ld, OC, base_size, base_size_descr)
SELECT datasheet_id, line, name, M, T, Sv, inv_sv, inv_sv_descr, W, Ld, OC, base_size, base_size_descr
FROM temp_datasheets_models;

DROP TABLE temp_datasheets_models;

-- ---------------------------------------------------------------------
-- DATASHEETS_OPTIONS TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_options WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_options
);

CREATE TEMP TABLE temp_datasheets_options (
    datasheet_id VARCHAR(100),
    line INT,
    button VARCHAR(10),
    description TEXT
);

COPY temp_datasheets_options FROM 'path/to/csv/Datasheets_options.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_options (datasheet_id, line, button, description)
SELECT datasheet_id, line, button, description
FROM temp_datasheets_options;

DROP TABLE temp_datasheets_options;

-- ---------------------------------------------------------------------
-- DATASHEETS_WARGEAR TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_wargear WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_wargear
);

CREATE TEMP TABLE temp_datasheets_wargear (
    datasheet_id VARCHAR(100),
    line INT,
    line_in_wargear INT,
    dice VARCHAR(50),
    name VARCHAR(255),
    description TEXT,
    range VARCHAR(50),
    type VARCHAR(50),
    A VARCHAR(50),
    BS_WS VARCHAR(50),
    S VARCHAR(50),
    AP VARCHAR(50),
    D VARCHAR(50)
);

COPY temp_datasheets_wargear FROM 'path/to/csv/Datasheets_wargear.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_wargear
    (datasheet_id, line, line_in_wargear, dice, name, description, range, type, A, BS_WS, S, AP, D)
SELECT datasheet_id, line, line_in_wargear, dice, name, description, range, type, A, BS_WS, S, AP, D
FROM temp_datasheets_wargear;

DROP TABLE temp_datasheets_wargear;

-- ---------------------------------------------------------------------
-- DATASHEETS_UNIT_COMPOSITION TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_unit_composition WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_unit_composition
);

CREATE TEMP TABLE temp_datasheets_unit_composition (
    datasheet_id VARCHAR(100),
    line INT,
    description TEXT
);

COPY temp_datasheets_unit_composition FROM 'path/to/csv/Datasheets_unit_composition.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_unit_composition (datasheet_id, line, description)
SELECT datasheet_id, line, description
FROM temp_datasheets_unit_composition;

DROP TABLE temp_datasheets_unit_composition;

-- ---------------------------------------------------------------------
-- DATASHEETS_MODELS_COST TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_models_cost WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_models_cost
);

CREATE TEMP TABLE temp_datasheets_models_cost (
    datasheet_id VARCHAR(100),
    line INT,
    description TEXT,
    cost VARCHAR(50)
);

COPY temp_datasheets_models_cost FROM 'path/to/csv/Datasheets_models_cost.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_models_cost (datasheet_id, line, description, cost)
SELECT datasheet_id, line, description, cost
FROM temp_datasheets_models_cost;

DROP TABLE temp_datasheets_models_cost;

-- =====================================================================
-- STEP 6: LOAD JUNCTION TABLES
-- These handle many-to-many relationships
-- =====================================================================

-- ---------------------------------------------------------------------
-- DATASHEETS_STRATAGEMS TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_stratagems WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_stratagems
);

CREATE TEMP TABLE temp_datasheets_stratagems (
    datasheet_id VARCHAR(100),
    stratagem_id VARCHAR(100)
);

COPY temp_datasheets_stratagems FROM 'path/to/csv/Datasheets_stratagems.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_stratagems (datasheet_id, stratagem_id)
SELECT datasheet_id, stratagem_id
FROM temp_datasheets_stratagems;

DROP TABLE temp_datasheets_stratagems;

-- ---------------------------------------------------------------------
-- DATASHEETS_ENHANCEMENTS TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_enhancements WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_enhancements
);

CREATE TEMP TABLE temp_datasheets_enhancements (
    datasheet_id VARCHAR(100),
    enhancement_id VARCHAR(100)
);

COPY temp_datasheets_enhancements FROM 'path/to/csv/Datasheets_enhancements.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_enhancements (datasheet_id, enhancement_id)
SELECT datasheet_id, enhancement_id
FROM temp_datasheets_enhancements;

DROP TABLE temp_datasheets_enhancements;

-- ---------------------------------------------------------------------
-- DATASHEETS_DETACHMENT_ABILITIES TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_detachment_abilities WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_detachment_abilities
);

CREATE TEMP TABLE temp_datasheets_detachment_abilities (
    datasheet_id VARCHAR(100),
    detachment_ability_id VARCHAR(100)
);

COPY temp_datasheets_detachment_abilities FROM 'path/to/csv/Datasheets_detachment_abilities.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_detachment_abilities (datasheet_id, detachment_ability_id)
SELECT datasheet_id, detachment_ability_id
FROM temp_datasheets_detachment_abilities;

DROP TABLE temp_datasheets_detachment_abilities;

-- ---------------------------------------------------------------------
-- DATASHEETS_LEADER TABLE
-- ---------------------------------------------------------------------
DELETE FROM Datasheets_leader WHERE datasheet_id IN (
    SELECT DISTINCT datasheet_id FROM temp_datasheets_leader
);

CREATE TEMP TABLE temp_datasheets_leader (
    datasheet_id VARCHAR(100),
    attached_datasheet_id VARCHAR(100)
);

COPY temp_datasheets_leader FROM 'path/to/csv/Datasheets_leader.csv'
    DELIMITER '|'
    CSV HEADER
    ENCODING 'UTF8';

INSERT INTO Datasheets_leader (datasheet_id, attached_datasheet_id)
SELECT datasheet_id, attached_datasheet_id
FROM temp_datasheets_leader;

DROP TABLE temp_datasheets_leader;

-- =====================================================================
-- COMPLETION
-- =====================================================================

COMMIT;

-- Display summary of imported data
SELECT 'Data import completed successfully!' AS status;
SELECT 'Factions loaded: ' || COUNT(*) FROM Factions;
SELECT 'Datasheets loaded: ' || COUNT(*) FROM Datasheets;
SELECT 'Stratagems loaded: ' || COUNT(*) FROM Stratagems;
SELECT 'Abilities loaded: ' || COUNT(*) FROM Abilities;
SELECT 'Enhancements loaded: ' || COUNT(*) FROM Enhancements;
SELECT 'Detachment abilities loaded: ' || COUNT(*) FROM Detachment_abilities;

-- =====================================================================
-- NOTES FOR OTHER SQL DATABASES
-- =====================================================================
--
-- For SQL Server:
-- - Replace COPY with BULK INSERT or use SQL Server Import/Export Wizard
-- - Replace TEMP TABLE with #temp_table_name syntax
-- - Replace DO $$ blocks with stored procedures
-- - Example BULK INSERT:
--   BULK INSERT temp_factions
--   FROM 'path\to\csv\Factions.csv'
--   WITH (FIELDTERMINATOR = '|', ROWTERMINATOR = '\n', FIRSTROW = 2)
--
-- For MySQL:
-- - Replace COPY with LOAD DATA INFILE
-- - Replace TEMP TABLE with TEMPORARY TABLE
-- - Replace MERGE with INSERT ... ON DUPLICATE KEY UPDATE
-- - Example LOAD DATA:
--   LOAD DATA INFILE 'path/to/csv/Factions.csv'
--   INTO TABLE temp_factions
--   FIELDS TERMINATED BY '|'
--   LINES TERMINATED BY '\n'
--   IGNORE 1 ROWS
--
-- =====================================================================
