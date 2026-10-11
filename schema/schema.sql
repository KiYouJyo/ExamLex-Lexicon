-- ExamLex Lexicon: SQLite schema v1
-- Canonical source for all database files. UTF-8 encoding.
-- Run using the repository CLI (which enables SQLite foreign keys).
PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    url TEXT,
    license_id TEXT,
    license_url TEXT,
    attribution TEXT,
    redistribution_notes TEXT
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    headword TEXT NOT NULL,
    normalized_headword TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    homograph_number INTEGER NOT NULL DEFAULT 1 CHECK (homograph_number > 0),
    cefr_level TEXT CHECK (cefr_level IS NULL OR cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    cefr_source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (language, normalized_headword, homograph_number)
);

CREATE INDEX IF NOT EXISTS idx_entries_cefr ON entries(cefr_level, normalized_headword);

CREATE TABLE IF NOT EXISTS pronunciations (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    part_of_speech TEXT,
    accent TEXT,
    ipa TEXT NOT NULL,
    audio_url TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_pronunciations_entry ON pronunciations(entry_id);

CREATE TABLE IF NOT EXISTS inflections (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    part_of_speech TEXT NOT NULL,
    form_type TEXT NOT NULL,
    form TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    UNIQUE(entry_id, part_of_speech, form_type, form)
);
CREATE INDEX IF NOT EXISTS idx_inflections_entry ON inflections(entry_id);

CREATE TABLE IF NOT EXISTS senses (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    part_of_speech TEXT NOT NULL,
    sense_number INTEGER NOT NULL CHECK(sense_number > 0),
    definition_en TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','imported','generated','reviewed')),
    UNIQUE(entry_id, part_of_speech, sense_number)
);
CREATE INDEX IF NOT EXISTS idx_senses_entry ON senses(entry_id, part_of_speech, sense_number);

CREATE TABLE IF NOT EXISTS sense_translations (
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
    language TEXT NOT NULL CHECK(language IN ('zh','ja')),
    text TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','imported','generated','reviewed')),
    UNIQUE(sense_id, language, text)
);
CREATE INDEX IF NOT EXISTS idx_translations_sense ON sense_translations(sense_id, language);

CREATE TABLE IF NOT EXISTS semantic_relations (
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK(relation_type IN ('synonym','antonym','related','derived')),
    related_word TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    UNIQUE(sense_id, relation_type, related_word)
);
CREATE INDEX IF NOT EXISTS idx_relations_sense ON semantic_relations(sense_id);

CREATE TABLE IF NOT EXISTS expressions (
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
    expression_type TEXT NOT NULL
        CHECK(expression_type IN ('collocation','valency','phrasal_verb','idiom','phrase','chunk')),
    text_en TEXT NOT NULL,
    meaning_zh TEXT,
    meaning_ja TEXT,
    notes TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','imported','generated','reviewed')),
    UNIQUE(sense_id, expression_type, text_en)
);
CREATE INDEX IF NOT EXISTS idx_expressions_sense ON expressions(sense_id, expression_type);

CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
    text_en TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','imported','generated','reviewed')),
    UNIQUE(sense_id, text_en)
);
CREATE INDEX IF NOT EXISTS idx_examples_sense ON examples(sense_id);

CREATE TABLE IF NOT EXISTS example_translations (
    id INTEGER PRIMARY KEY,
    example_id INTEGER NOT NULL REFERENCES examples(id) ON DELETE CASCADE,
    language TEXT NOT NULL CHECK(language IN ('zh','ja')),
    text TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    review_status TEXT NOT NULL DEFAULT 'draft'
        CHECK(review_status IN ('draft','imported','generated','reviewed')),
    UNIQUE(example_id, language, text)
);
CREATE INDEX IF NOT EXISTS idx_example_translations_example ON example_translations(example_id, language);

CREATE TABLE IF NOT EXISTS exam_tags (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    exam TEXT NOT NULL CHECK(exam IN ('TOEFL','IELTS','TOEIC','OTHER')),
    priority TEXT CHECK(priority IS NULL OR priority IN ('core','high','medium','low')),
    notes TEXT,
    source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
    UNIQUE(entry_id, exam)
);
CREATE INDEX IF NOT EXISTS idx_exam_tags_exam ON exam_tags(exam, priority);

-- Preserve upstream IDs for repeatable imports and later sense alignment.
-- Empty source_sense_key denotes a word-level mapping.
CREATE TABLE IF NOT EXISTS source_links (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    source_entry_key TEXT NOT NULL,
    source_sense_key TEXT NOT NULL DEFAULT '',
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    sense_id INTEGER REFERENCES senses(id) ON DELETE CASCADE,
    match_status TEXT NOT NULL DEFAULT 'unmatched'
        CHECK(match_status IN ('unmatched','candidate','matched','reviewed')),
    UNIQUE(source_id, source_entry_key, source_sense_key)
);
CREATE INDEX IF NOT EXISTS idx_source_links_entry ON source_links(entry_id);
CREATE INDEX IF NOT EXISTS idx_source_links_sense ON source_links(sense_id);

PRAGMA user_version = 1;
COMMIT;
