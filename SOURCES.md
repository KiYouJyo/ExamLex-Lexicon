# Lexical data sources and licensing

**Important:** this repository's source code and database schema do **not** grant permission to redistribute third-party dictionary datasets. There are no third-party lexical dumps in v0.1.

| Candidate source | Potential use | Terms to verify before publication |
|---|---|---|
| [Kaikki / English Wiktionary](https://kaikki.org/dictionary/English/) | Primary English definitions, IPA, inflections, meanings, usage examples, relations | Wiktionary dump license(s), attribution, share-alike obligations and compatibility with shipped data |
| [ECDICT](https://github.com/skywind3000/ECDICT) | Chinese gloss candidates, English headword metadata | Repository's MIT terms **and** provenance / redistribution rights of included definitions |
| [EJDict](https://github.com/kujirahand/EJDict) | Japanese gloss candidates | Verify individual repository edition, upstream provenance, CC0 scope and attribution rules |
| [Open English WordNet](https://en-word.net/) | Sense-based semantic relations | CC BY 4.0 attribution, edition and downstream license conditions |
| [Tatoeba](https://tatoeba.org/en/downloads) | Examples and multilingual example translations | Per-dataset / per-sentence terms, attribution metadata and download conditions |
| English Vocabulary Profile (EVP) | Reference for a simple CEFR level | **Do not scrape, bulk reproduce or redistribute** absent explicit authorization |
| Oxford 3000 / Oxford 5000 | Reference for a simple CEFR level | **Do not scrape, bulk reproduce or redistribute** absent explicit authorization |

Before integrating a source:
1. Record its exact URL, snapshot/version/date, license, attribution requirements and any restrictions.
2. Decide whether importing, modifying, displaying and **redistributing** the derived database are allowed; these are not always the same right.
3. Keep its records in an intermediate import process; align by meaning where possible and do not override reviewed data.
4. Avoid publishing an entire combined SQLite database until all included source licenses have been checked.
5. Preserve separate provenance identifiers for definitions, localized meanings, examples and generated content.

The \`local-demo\` source used by \`seed-demo\` is hand-authored illustrative content, not an imported dictionary and not an authoritative CEFR or exam-frequency source. No CEFR or exam tags are populated for the demo.
