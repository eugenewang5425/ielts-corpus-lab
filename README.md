# IELTS Corpus Lab public mirror

Static public mirror of the IELTS Corpus Lab aggregate dataset and study interface.

- No Cambridge IELTS passages, audio, images, answer keys, or third-party full question banks are republished.
- The public dataset contains aggregate word statistics, topic indexes, source metadata, provenance labels, and original practice questions with answer plans, templates, sample answers, and vocabulary.
- `data/manifest.json` is the uncached version pointer. The client then loads the matching `corpus.json` and `questions.json` snapshot.
- GitHub is the public, versioned, read-only database for this network-compatible deployment. Updating `main` updates the data served to visitors after the Pages build completes.

## Refresh the practice bank

```powershell
python scripts/generate_question_bank.py
python scripts/validate_public_data.py
```
