# IELTS Corpus Lab public mirror

Static public mirror of the IELTS Corpus Lab aggregate dataset and study interface.

- No Cambridge IELTS passages, audio, images, answer keys, or third-party model answers are republished. Cambridge IELTS Academic 4-21 is processed only into private local section caches and public aggregate statistics.
- The public dataset contains four-skill word statistics, Reading/Listening chunks, writing facets, merged speaking topics, deduplicated attributed source questions, and original practice content.
- Four-skill word lists contain every lemma that passes the documented document-frequency threshold; there is no top-750 cap. Reading/Listening auto-discovered chunks likewise publish the complete qualifying set instead of a top-450 sample.
- The source audit exposes 32 aggregate source cards across eight source layers. Cambridge IELTS Academic 4-21 is listed as 18 separate volume sources; individual speaking references remain attached to questions rather than being duplicated as audit cards.
- `data/manifest.json` is the uncached version pointer. The client then loads the matching five-file JSON snapshot.
- GitHub is the public, versioned, read-only database for this network-compatible deployment. Updating `main` updates the data served to visitors after the Pages build completes.

## Refresh the practice bank

```powershell
python scripts/extract_local_speaking.py
python scripts/extract_cambridge_sections.py
python scripts/build_corpus_snapshot.py
python scripts/build_merged_speaking_bank.py
python scripts/build_lr_chunks.py
python scripts/generate_question_bank.py
python scripts/validate_public_data.py
```

The Cambridge and local speaking extraction caches live outside this repository under `outputs/ielts-corpus-build`; raw copyrighted text never enters Git. The speaking build splits every source record into individual Part questions, maps them to a controlled taxonomy, merges identical question text, and preserves every source reference. The 2026 9-12 month local material is retained as an explicitly labelled upcoming prediction, not as a verified current bank.

The Reading/Listening chunk build keeps the curated core and manually indexed entries, then mines additional two- and three-word sequences only when they recur across documents and at least two source collections. Automatically discovered entries are labelled as functional study indexes rather than presented as human translations.
