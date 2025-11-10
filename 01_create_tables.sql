-- =====================================================================
-- SQL Database Schema for Wahapedia Export Data
-- =====================================================================
-- This script creates all necessary tables for importing Wahapedia data
-- with proper relationships, constraints, and indexes.
--
-- Database Compatibility: PostgreSQL (with notes for SQL Server/MySQL)
-- Encoding: UTF-8
-- CSV Delimiter: | (pipe/vertical bar)
-- =====================================================================

-- Begin transaction: all tables will be created atomically
-- If any error occurs, all changes will be rolled back
BEGIN;

-- =====================================================================
-- CREATE SCHEMA
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS wh40k;

-- =====================================================================
-- DROP EXISTING TABLES (if any)
-- Drops in reverse order of creation to handle foreign key dependencies
-- =====================================================================

-- Drop indexes first
DROP INDEX IF EXISTS wh40k.idx_source_errata_date;
DROP INDEX IF EXISTS wh40k.idx_detachment_abilities_faction_id;
DROP INDEX IF EXISTS wh40k.idx_enhancements_faction_id;
DROP INDEX IF EXISTS wh40k.idx_abilities_faction_id;
DROP INDEX IF EXISTS wh40k.idx_stratagems_faction_id;
DROP INDEX IF EXISTS wh40k.idx_datasheets_leader_attached;
DROP INDEX IF EXISTS wh40k.idx_datasheets_leader_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_detachment_abilities_ability;
DROP INDEX IF EXISTS wh40k.idx_datasheets_detachment_abilities_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_enhancements_enhancement;
DROP INDEX IF EXISTS wh40k.idx_datasheets_enhancements_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_stratagems_stratagem;
DROP INDEX IF EXISTS wh40k.idx_datasheets_stratagems_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_models_cost_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_unit_composition_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_wargear_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_options_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_models_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_keywords_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_abilities_ability;
DROP INDEX IF EXISTS wh40k.idx_datasheets_abilities_datasheet;
DROP INDEX IF EXISTS wh40k.idx_datasheets_source_id;
DROP INDEX IF EXISTS wh40k.idx_datasheets_faction_id;

-- Drop junction tables
DROP TABLE IF EXISTS wh40k.Datasheets_leader;
DROP TABLE IF EXISTS wh40k.Datasheets_detachment_abilities;
DROP TABLE IF EXISTS wh40k.Datasheets_enhancements;
DROP TABLE IF EXISTS wh40k.Datasheets_stratagems;

-- Drop datasheets child tables
DROP TABLE IF EXISTS wh40k.Datasheets_models_cost;
DROP TABLE IF EXISTS wh40k.Datasheets_unit_composition;
DROP TABLE IF EXISTS wh40k.Datasheets_wargear;
DROP TABLE IF EXISTS wh40k.Datasheets_options;
DROP TABLE IF EXISTS wh40k.Datasheets_models;
DROP TABLE IF EXISTS wh40k.Datasheets_keywords;
DROP TABLE IF EXISTS wh40k.Datasheets_abilities;

-- Drop datasheets table
DROP TABLE IF EXISTS wh40k.Datasheets;

-- Drop game content tables
DROP TABLE IF EXISTS wh40k.Detachment_abilities;
DROP TABLE IF EXISTS wh40k.Enhancements;
DROP TABLE IF EXISTS wh40k.Abilities;
DROP TABLE IF EXISTS wh40k.Stratagems;

-- Drop core reference tables
DROP TABLE IF EXISTS wh40k.Last_update;
DROP TABLE IF EXISTS wh40k.Source;
DROP TABLE IF EXISTS wh40k.Factions;

-- =====================================================================
-- CORE REFERENCE TABLES
-- These tables store foundational data referenced by other tables
-- =====================================================================

-- Factions table: stores all factions and subfactions
CREATE TABLE wh40k.Factions (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    link VARCHAR(500),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Source table: stores rulebooks, supplements, and promo datasheets
CREATE TABLE wh40k.Source (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),  -- e.g., "Index", "Supplement"
    edition VARCHAR(50),
    version VARCHAR(50),  -- Errata version number
    errata_date DATE,
    errata_link VARCHAR(500),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Last_update table: tracks when export data was last updated
-- This is used to determine if we need to refresh the entire dataset
CREATE TABLE wh40k.Last_update (
    last_update TIMESTAMP PRIMARY KEY,  -- Format: yyyy-MM-dd HH:mm:ss (GMT+3)
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- GAME CONTENT TABLES
-- These tables store stratagems, abilities, enhancements, etc.
-- Must be created BEFORE Datasheets tables that reference them
-- =====================================================================

-- Stratagems table: stores all stratagems
CREATE TABLE wh40k.Stratagems (
    id VARCHAR(100) PRIMARY KEY,
    faction_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255),  -- e.g., "Shield Host – Strategic Ploy Stratagem"
    cp_cost VARCHAR(50),  -- Command Point cost
    legend TEXT,  -- HTML formatted background
    turn VARCHAR(100),
    phase VARCHAR(100),
    description TEXT,  -- HTML formatted
    detachment VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_stratagems_faction FOREIGN KEY (faction_id) REFERENCES wh40k.Factions(id)
);

-- Abilities table: stores all abilities
CREATE TABLE wh40k.Abilities (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted background
    faction_id VARCHAR(100) NOT NULL,
    description TEXT,  -- HTML formatted
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_abilities_faction FOREIGN KEY (faction_id) REFERENCES wh40k.Factions(id)
);

-- Enhancements table: stores all enhancements
CREATE TABLE wh40k.Enhancements (
    id VARCHAR(100) PRIMARY KEY,
    faction_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted
    description TEXT,  -- HTML formatted
    cost VARCHAR(50),  -- Points cost
    detachment VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_enhancements_faction FOREIGN KEY (faction_id) REFERENCES wh40k.Factions(id)
);

-- Detachment_abilities table: stores all detachment abilities
CREATE TABLE wh40k.Detachment_abilities (
    id VARCHAR(100) PRIMARY KEY,
    faction_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted
    description TEXT,  -- HTML formatted
    detachment VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_detachment_abilities_faction FOREIGN KEY (faction_id) REFERENCES wh40k.Factions(id)
);

-- =====================================================================
-- DATASHEETS AND RELATED TABLES
-- The Datasheets table is the central table with many child tables
-- =====================================================================

-- Datasheets table: core table for all unit datasheets
CREATE TABLE wh40k.Datasheets (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    faction_id VARCHAR(100) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    legend TEXT,  -- HTML formatted background text
    role VARCHAR(100),  -- Battlefield Role
    loadout TEXT,
    transport TEXT,
    virtual BOOLEAN DEFAULT false,  -- Virtual datasheets (e.g., summoned units)
    leader_head TEXT,
    leader_footer TEXT,
    damaged_w VARCHAR(50),  -- Remaining Wounds count for degrading profiles
    damaged_description TEXT,
    link VARCHAR(500),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_faction FOREIGN KEY (faction_id) REFERENCES wh40k.Factions(id),
    CONSTRAINT fk_datasheets_source FOREIGN KEY (source_id) REFERENCES wh40k.Source(id)
);

-- Datasheets_abilities: stores abilities for each datasheet
CREATE TABLE wh40k.Datasheets_abilities (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,  -- Line number in the table (starting from 1)
    ability_id VARCHAR(100),  -- Links to Abilities table if populated
    model VARCHAR(255),  -- Which model this ability applies to
    name VARCHAR(255),
    description TEXT,  -- HTML formatted
    type VARCHAR(100),
    parameter VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_abilities_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id),
    CONSTRAINT fk_datasheets_abilities_ability FOREIGN KEY (ability_id) REFERENCES wh40k.Abilities(id)
);

-- Datasheets_keywords: stores keywords for each datasheet
CREATE TABLE wh40k.Datasheets_keywords (
    datasheet_id VARCHAR(100) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    model VARCHAR(255),  -- Which model this keyword applies to
    is_faction_keyword BOOLEAN DEFAULT false,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, keyword),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_keywords_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- Datasheets_models: stores model statistics for each datasheet
CREATE TABLE wh40k.Datasheets_models (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    name VARCHAR(255),
    M VARCHAR(50),   -- Move characteristic
    T VARCHAR(50),   -- Toughness characteristic
    Sv VARCHAR(50),  -- Save characteristic
    inv_sv VARCHAR(50),  -- Invulnerable Save characteristic
    inv_sv_descr TEXT,
    W VARCHAR(50),   -- Wounds characteristic
    Ld VARCHAR(50),  -- Leadership characteristic
    OC VARCHAR(50),  -- Objective Control characteristic
    base_size VARCHAR(100),
    base_size_descr TEXT,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_models_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- Datasheets_options: stores wargear options for each datasheet
CREATE TABLE wh40k.Datasheets_options (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    button VARCHAR(10),  -- Decorative symbol
    description TEXT,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_options_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- Datasheets_wargear: stores wargear/weapons for each datasheet
CREATE TABLE wh40k.Datasheets_wargear (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    line_in_wargear INT,  -- For sorting: ORDER BY line, line_in_wargear
    dice VARCHAR(50),  -- Dice result required (e.g., Bubblechukka)
    name VARCHAR(255),
    description TEXT,  -- HTML formatted rules
    range VARCHAR(50),
    type VARCHAR(50),  -- "Melee" or "Ranged"
    A VARCHAR(50),     -- Attacks characteristic
    BS_WS VARCHAR(50), -- Ballistic Skill / Weapon Skill characteristic
    S VARCHAR(50),     -- Strength characteristic
    AP VARCHAR(50),    -- Armour Penetration characteristic
    D VARCHAR(50),     -- Damage characteristic
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line, line_in_wargear),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_wargear_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- Datasheets_unit_composition: stores unit composition for each datasheet
CREATE TABLE wh40k.Datasheets_unit_composition (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    description TEXT,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_unit_composition_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- Datasheets_models_cost: stores model point costs for each datasheet
CREATE TABLE wh40k.Datasheets_models_cost (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    description TEXT,  -- Model description
    cost VARCHAR(50),  -- Model cost in points
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_models_cost_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- =====================================================================
-- JUNCTION TABLES (Many-to-Many Relationships)
-- These tables link datasheets to stratagems, enhancements, etc.
-- =====================================================================

-- Datasheets_stratagems: links datasheets to their available stratagems
CREATE TABLE wh40k.Datasheets_stratagems (
    datasheet_id VARCHAR(100) NOT NULL,
    stratagem_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, stratagem_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_stratagems_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id),
    CONSTRAINT fk_datasheets_stratagems_stratagem FOREIGN KEY (stratagem_id) REFERENCES wh40k.Stratagems(id)
);

-- Datasheets_enhancements: links datasheets to their available enhancements
CREATE TABLE wh40k.Datasheets_enhancements (
    datasheet_id VARCHAR(100) NOT NULL,
    enhancement_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, enhancement_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_enhancements_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id),
    CONSTRAINT fk_datasheets_enhancements_enhancement FOREIGN KEY (enhancement_id) REFERENCES wh40k.Enhancements(id)
);

-- Datasheets_detachment_abilities: links datasheets to detachment abilities
CREATE TABLE wh40k.Datasheets_detachment_abilities (
    datasheet_id VARCHAR(100) NOT NULL,
    detachment_ability_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, detachment_ability_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_detachment_abilities_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id),
    CONSTRAINT fk_datasheets_detachment_abilities_ability FOREIGN KEY (detachment_ability_id) REFERENCES wh40k.Detachment_abilities(id)
);

-- Datasheets_leader: links leader datasheets to units they can be attached to
CREATE TABLE wh40k.Datasheets_leader (
    datasheet_id VARCHAR(100) NOT NULL,  -- The leader datasheet
    attached_datasheet_id VARCHAR(100) NOT NULL,  -- The unit they can attach to
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, attached_datasheet_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_leader_datasheet FOREIGN KEY (datasheet_id) REFERENCES wh40k.Datasheets(id),
    CONSTRAINT fk_datasheets_leader_attached FOREIGN KEY (attached_datasheet_id) REFERENCES wh40k.Datasheets(id)
);

-- =====================================================================
-- INDEXES FOR PERFORMANCE
-- Create indexes on foreign keys and frequently queried columns
-- =====================================================================

-- Indexes on Datasheets foreign keys
CREATE INDEX idx_datasheets_faction_id ON wh40k.Datasheets(faction_id);
CREATE INDEX idx_datasheets_source_id ON wh40k.Datasheets(source_id);

-- Indexes on Datasheets_* tables
CREATE INDEX idx_datasheets_abilities_datasheet ON wh40k.Datasheets_abilities(datasheet_id);
CREATE INDEX idx_datasheets_abilities_ability ON wh40k.Datasheets_abilities(ability_id);
CREATE INDEX idx_datasheets_keywords_datasheet ON wh40k.Datasheets_keywords(datasheet_id);
CREATE INDEX idx_datasheets_models_datasheet ON wh40k.Datasheets_models(datasheet_id);
CREATE INDEX idx_datasheets_options_datasheet ON wh40k.Datasheets_options(datasheet_id);
CREATE INDEX idx_datasheets_wargear_datasheet ON wh40k.Datasheets_wargear(datasheet_id);
CREATE INDEX idx_datasheets_unit_composition_datasheet ON wh40k.Datasheets_unit_composition(datasheet_id);
CREATE INDEX idx_datasheets_models_cost_datasheet ON wh40k.Datasheets_models_cost(datasheet_id);

-- Indexes on junction tables
CREATE INDEX idx_datasheets_stratagems_datasheet ON wh40k.Datasheets_stratagems(datasheet_id);
CREATE INDEX idx_datasheets_stratagems_stratagem ON wh40k.Datasheets_stratagems(stratagem_id);
CREATE INDEX idx_datasheets_enhancements_datasheet ON wh40k.Datasheets_enhancements(datasheet_id);
CREATE INDEX idx_datasheets_enhancements_enhancement ON wh40k.Datasheets_enhancements(enhancement_id);
CREATE INDEX idx_datasheets_detachment_abilities_datasheet ON wh40k.Datasheets_detachment_abilities(datasheet_id);
CREATE INDEX idx_datasheets_detachment_abilities_ability ON wh40k.Datasheets_detachment_abilities(detachment_ability_id);
CREATE INDEX idx_datasheets_leader_datasheet ON wh40k.Datasheets_leader(datasheet_id);
CREATE INDEX idx_datasheets_leader_attached ON wh40k.Datasheets_leader(attached_datasheet_id);

-- Indexes on game content tables
CREATE INDEX idx_stratagems_faction_id ON wh40k.Stratagems(faction_id);
CREATE INDEX idx_abilities_faction_id ON wh40k.Abilities(faction_id);
CREATE INDEX idx_enhancements_faction_id ON wh40k.Enhancements(faction_id);
CREATE INDEX idx_detachment_abilities_faction_id ON wh40k.Detachment_abilities(faction_id);

-- Index on date fields for tracking updates
CREATE INDEX idx_source_errata_date ON wh40k.Source(errata_date);

-- =====================================================================
-- NOTES FOR OTHER SQL DATABASES
-- =====================================================================
--
-- For SQL Server:
-- - Replace BEGIN with BEGIN TRANSACTION
-- - Replace TIMESTAMP with DATETIME2
-- - Replace CURRENT_TIMESTAMP with GETDATE()
-- - Replace TEXT with VARCHAR(MAX)
--
-- For MySQL:
-- - Replace TIMESTAMP with DATETIME
-- - TEXT type is fine as-is
-- - Boolean converts to TINYINT(1) automatically
--
-- =====================================================================

-- Commit transaction: all tables created successfully
COMMIT;
