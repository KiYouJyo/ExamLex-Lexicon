# Data model (schema v1)

## Entity relationships

\`\`\`text
sources ───────────────┐
                       │ provenance (source_id)
entries                │
 ├─ pronunciations     │
 ├─ inflections        │
 ├─ exam_tags          │
 ├─ senses             │
 │   ├─ sense_translations (zh / ja)
 │   ├─ semantic_relations
 │   ├─ expressions (collocations / valency / phrases)
 │   └─ examples
 │       └─ example_translations (zh / ja)
 └─ source_links ──────┘  (upstream entry + sense identifiers)
\`\`\`

**Entries** are English headwords, distinguished by normalized spelling and optional homograph number. The display headword is preserved; the normalized string is produced by the importer, usually with Python's \`strip().casefold()\`.

**Senses** are attached to entries and distinguished by part of speech and sense number. Keep the original English meaning separate from localized translations. Do not append all Chinese / Japanese meanings to the word without sense matching.

**Sources** store dataset-level metadata and licensing. A source's exact data version and any distribution conditions belong in its attribution or redistribution notes until version-specific import tracking is implemented.

**Source links** keep upstream identifiers and the alignment status. A candidate alignment must never silently replace a reviewed one. All initial links are unverified unless explicitly reviewed.

## CEFR and examinations

CEFR is intentionally **entry-level only**: \`entries.cefr_level\` is \`A1\`, \`A2\`, \`B1\`, \`B2\`, \`C1\`, \`C2\` or \`NULL\`; \`entries.cefr_source\` records a short reference note (e.g. \`Oxford\`, \`EVP\`, \`editorial\`). If Oxford and EVP differ, the editorial import policy may prefer Oxford. Do not infer a level from the absence of one.

Exam indicators are stored separately in \`exam_tags\` and are not authoritative frequency statistics. Include only evidence-backed priorities; absence is preferable to invented labels. TOEFL, IELTS and TOEIC can be tagged independently.

## Empty fields, deduplication and quality

- Incomplete data is normal: use SQL \`NULL\` or no child row, never fabricated placeholders such as \`N/A\` or a guessed CEFR level.
- Identity keys: word = \`(language, normalized_headword, homograph_number)\`; meaning = \`(entry_id, part_of_speech, sense_number)\`. These are internal keys, not promises that every source splits meanings identically.
- Translations, examples, patterns and semantic relations are attached to a specific meaning. Normalize/match before merging. Unmatched foreign senses stay candidates in a staging pipeline, not in the published database.
- Source attribution attaches to content rows and upstream mappings. If a translated example comes from another source than its English sentence, use its own \`example_translations.source_id\`.
- \`review_status\` can be \`draft\`, \`imported\`, \`generated\` or \`reviewed\`. Generated content is **not** automatically trustworthy or available for publication.
- The database enforces source-link foreign keys and the CLI validator additionally checks that a mapped sense actually belongs to its mapped entry.
- A future importer should use transactions, staging tables, stable source IDs and idempotent upserts. Do not overwrite reviewed records with raw imports.

## Sample queries

Find B2 words:

\`\`\`sql
SELECT headword FROM entries WHERE cefr_level = 'B2'
ORDER BY normalized_headword;
\`\`\`

Find English meanings and attached Chinese translations for one word:

\`\`\`sql
SELECT e.headword, s.part_of_speech, s.sense_number,
       s.definition_en, t.text AS gloss_zh
FROM entries e
JOIN senses s ON s.entry_id = e.id
LEFT JOIN sense_translations t
    ON t.sense_id = s.id AND t.language = 'zh'
WHERE e.normalized_headword = 'address'
ORDER BY s.part_of_speech, s.sense_number;
\`\`\`

Filter TOEFL-tagged B2 words:

\`\`\`sql
SELECT e.headword, x.priority
FROM entries e
JOIN exam_tags x ON x.entry_id = e.id
WHERE e.cefr_level = 'B2' AND x.exam = 'TOEFL';
\`\`\`

## Production considerations

SQLite is the portable published format. Large raw JSONL dumps belong in temporary build folders, not Git. The build pipeline should create a new database, run \`PRAGMA integrity_check\` and \`PRAGMA foreign_key_check\`, and only then publish an atomic versioned artifact. Upgrades beyond schema v1 will require explicit migration scripts rather than silently rewriting an existing database.
