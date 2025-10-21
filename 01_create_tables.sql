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

-- =====================================================================
-- CORE REFERENCE TABLES
-- These tables store foundational data referenced by other tables
-- =====================================================================

-- Factions table: stores all factions and subfactions
CREATE TABLE Factions (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    link VARCHAR(500),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Source table: stores rulebooks, supplements, and promo datasheets
CREATE TABLE Source (
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
CREATE TABLE Last_update (
    last_update TIMESTAMP PRIMARY KEY,  -- Format: yyyy-MM-dd HH:mm:ss (GMT+3)
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- DATASHEETS AND RELATED TABLES
-- The Datasheets table is the central table with many child tables
-- =====================================================================

-- Datasheets table: core table for all unit datasheets
CREATE TABLE Datasheets (
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
    CONSTRAINT fk_datasheets_faction FOREIGN KEY (faction_id) REFERENCES Factions(id),
    CONSTRAINT fk_datasheets_source FOREIGN KEY (source_id) REFERENCES Source(id)
);

-- Datasheets_abilities: stores abilities for each datasheet
CREATE TABLE Datasheets_abilities (
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
    CONSTRAINT fk_datasheets_abilities_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id),
    CONSTRAINT fk_datasheets_abilities_ability FOREIGN KEY (ability_id) REFERENCES Abilities(id)
);

-- Datasheets_keywords: stores keywords for each datasheet
CREATE TABLE Datasheets_keywords (
    datasheet_id VARCHAR(100) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    model VARCHAR(255),  -- Which model this keyword applies to
    is_faction_keyword BOOLEAN DEFAULT false,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, keyword),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_keywords_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- Datasheets_models: stores model statistics for each datasheet
CREATE TABLE Datasheets_models (
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
    CONSTRAINT fk_datasheets_models_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- Datasheets_options: stores wargear options for each datasheet
CREATE TABLE Datasheets_options (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    button VARCHAR(10),  -- Decorative symbol
    description TEXT,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_options_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- Datasheets_wargear: stores wargear/weapons for each datasheet
CREATE TABLE Datasheets_wargear (
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
    CONSTRAINT fk_datasheets_wargear_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- Datasheets_unit_composition: stores unit composition for each datasheet
CREATE TABLE Datasheets_unit_composition (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    description TEXT,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_unit_composition_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- Datasheets_models_cost: stores model point costs for each datasheet
CREATE TABLE Datasheets_models_cost (
    datasheet_id VARCHAR(100) NOT NULL,
    line INT NOT NULL,
    description TEXT,  -- Model description
    cost VARCHAR(50),  -- Model cost in points
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, line),

    -- Foreign key constraint
    CONSTRAINT fk_datasheets_models_cost_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id)
);

-- =====================================================================
-- JUNCTION TABLES (Many-to-Many Relationships)
-- These tables link datasheets to stratagems, enhancements, etc.
-- =====================================================================

-- Datasheets_stratagems: links datasheets to their available stratagems
CREATE TABLE Datasheets_stratagems (
    datasheet_id VARCHAR(100) NOT NULL,
    stratagem_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, stratagem_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_stratagems_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id),
    CONSTRAINT fk_datasheets_stratagems_stratagem FOREIGN KEY (stratagem_id) REFERENCES Stratagems(id)
);

-- Datasheets_enhancements: links datasheets to their available enhancements
CREATE TABLE Datasheets_enhancements (
    datasheet_id VARCHAR(100) NOT NULL,
    enhancement_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, enhancement_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_enhancements_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id),
    CONSTRAINT fk_datasheets_enhancements_enhancement FOREIGN KEY (enhancement_id) REFERENCES Enhancements(id)
);

-- Datasheets_detachment_abilities: links datasheets to detachment abilities
CREATE TABLE Datasheets_detachment_abilities (
    datasheet_id VARCHAR(100) NOT NULL,
    detachment_ability_id VARCHAR(100) NOT NULL,
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, detachment_ability_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_detachment_abilities_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id),
    CONSTRAINT fk_datasheets_detachment_abilities_ability FOREIGN KEY (detachment_ability_id) REFERENCES Detachment_abilities(id)
);

-- Datasheets_leader: links leader datasheets to units they can be attached to
CREATE TABLE Datasheets_leader (
    datasheet_id VARCHAR(100) NOT NULL,  -- The leader datasheet
    attached_datasheet_id VARCHAR(100) NOT NULL,  -- The unit they can attach to
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    PRIMARY KEY (datasheet_id, attached_datasheet_id),

    -- Foreign key constraints
    CONSTRAINT fk_datasheets_leader_datasheet FOREIGN KEY (datasheet_id) REFERENCES Datasheets(id),
    CONSTRAINT fk_datasheets_leader_attached FOREIGN KEY (attached_datasheet_id) REFERENCES Datasheets(id)
);

-- =====================================================================
-- GAME CONTENT TABLES
-- These tables store stratagems, abilities, enhancements, etc.
-- =====================================================================

-- Stratagems table: stores all stratagems
CREATE TABLE Stratagems (
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
    CONSTRAINT fk_stratagems_faction FOREIGN KEY (faction_id) REFERENCES Factions(id)
);

-- Abilities table: stores all abilities
CREATE TABLE Abilities (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted background
    faction_id VARCHAR(100) NOT NULL,
    description TEXT,  -- HTML formatted
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_abilities_faction FOREIGN KEY (faction_id) REFERENCES Factions(id)
);

-- Enhancements table: stores all enhancements
CREATE TABLE Enhancements (
    id VARCHAR(100) PRIMARY KEY,
    faction_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted
    description TEXT,  -- HTML formatted
    cost VARCHAR(50),  -- Points cost
    detachment VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_enhancements_faction FOREIGN KEY (faction_id) REFERENCES Factions(id)
);

-- Detachment_abilities table: stores all detachment abilities
CREATE TABLE Detachment_abilities (
    id VARCHAR(100) PRIMARY KEY,
    faction_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    legend TEXT,  -- HTML formatted
    description TEXT,  -- HTML formatted
    detachment VARCHAR(255),
    date_imported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_detachment_abilities_faction FOREIGN KEY (faction_id) REFERENCES Factions(id)
);

-- =====================================================================
-- INDEXES FOR PERFORMANCE
-- Create indexes on foreign keys and frequently queried columns
-- =====================================================================

-- Indexes on Datasheets foreign keys
CREATE INDEX idx_datasheets_faction_id ON Datasheets(faction_id);
CREATE INDEX idx_datasheets_source_id ON Datasheets(source_id);

-- Indexes on Datasheets_* tables
CREATE INDEX idx_datasheets_abilities_datasheet ON Datasheets_abilities(datasheet_id);
CREATE INDEX idx_datasheets_abilities_ability ON Datasheets_abilities(ability_id);
CREATE INDEX idx_datasheets_keywords_datasheet ON Datasheets_keywords(datasheet_id);
CREATE INDEX idx_datasheets_models_datasheet ON Datasheets_models(datasheet_id);
CREATE INDEX idx_datasheets_options_datasheet ON Datasheets_options(datasheet_id);
CREATE INDEX idx_datasheets_wargear_datasheet ON Datasheets_wargear(datasheet_id);
CREATE INDEX idx_datasheets_unit_composition_datasheet ON Datasheets_unit_composition(datasheet_id);
CREATE INDEX idx_datasheets_models_cost_datasheet ON Datasheets_models_cost(datasheet_id);

-- Indexes on junction tables
CREATE INDEX idx_datasheets_stratagems_datasheet ON Datasheets_stratagems(datasheet_id);
CREATE INDEX idx_datasheets_stratagems_stratagem ON Datasheets_stratagems(stratagem_id);
CREATE INDEX idx_datasheets_enhancements_datasheet ON Datasheets_enhancements(datasheet_id);
CREATE INDEX idx_datasheets_enhancements_enhancement ON Datasheets_enhancements(enhancement_id);
CREATE INDEX idx_datasheets_detachment_abilities_datasheet ON Datasheets_detachment_abilities(datasheet_id);
CREATE INDEX idx_datasheets_detachment_abilities_ability ON Datasheets_detachment_abilities(detachment_ability_id);
CREATE INDEX idx_datasheets_leader_datasheet ON Datasheets_leader(datasheet_id);
CREATE INDEX idx_datasheets_leader_attached ON Datasheets_leader(attached_datasheet_id);

-- Indexes on game content tables
CREATE INDEX idx_stratagems_faction_id ON Stratagems(faction_id);
CREATE INDEX idx_abilities_faction_id ON Abilities(faction_id);
CREATE INDEX idx_enhancements_faction_id ON Enhancements(faction_id);
CREATE INDEX idx_detachment_abilities_faction_id ON Detachment_abilities(faction_id);

-- Index on date fields for tracking updates
CREATE INDEX idx_source_errata_date ON Source(errata_date);

-- =====================================================================
-- NOTES FOR OTHER SQL DATABASES
-- =====================================================================
--
-- For SQL Server:
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

COMMIT;
