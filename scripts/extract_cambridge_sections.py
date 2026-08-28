from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT.parent
MATERIAL_ROOT = STUDY_ROOT / "资料"
BUILD_ROOT = STUDY_ROOT / "outputs" / "ielts-corpus-build"
OCR_PACKAGES = STUDY_ROOT / "outputs" / "ocr-tools"
OUTPUT = BUILD_ROOT / "cambridge_sections.json"

VOLUME_YEARS = {
    4: 2005,
    5: 2006,
    6: 2007,
    7: 2009,
    8: 2011,
    9: 2013,
    10: 2015,
    11: 2016,
    12: 2017,
    13: 2018,
    14: 2019,
    15: 2020,
    16: 2021,
    17: 2022,
    18: 2023,
    19: 2024,
    20: 2025,
    21: 2026,
}

# Page boundaries are stable for the exact local editions identified by their
# source hashes below.  These four books have damaged/ambiguous contents-page
# text, so the generic heading detector can mistake late practice material for
# the start of the audioscripts.
STRUCTURE_OVERRIDES = {
    4: {"audio": 131, "answers": 153},
    8: {"audio": 129, "answers": 151},
    9: {"audio": 94, "answers": 115},
    15: {"audio": 96, "answers": 119},
}


def clean_text(value: str) -> str:
    value = value.replace("\x00", " ").replace("\u00ad", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def alpha_words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z]{2,}", value)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_pdf(volume: int) -> Path:
    if volume <= 19:
        candidates = list((MATERIAL_ROOT / "剑雅真题4-19全套PDF").glob(f"剑{volume}真题*.pdf"))
    elif volume == 20:
        candidates = list((MATERIAL_ROOT / "剑桥雅思20").rglob("*.pdf"))
    else:
        candidates = list((MATERIAL_ROOT / "剑21完整版").rglob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(f"Cambridge IELTS {volume} PDF was not found")
    # Duplicate downloads with a '(1)' suffix are byte-identical. Prefer the clean name.
    candidates.sort(key=lambda path: ("(1)" in path.name, -path.stat().st_size, path.name))
    return candidates[0]


def pdf_text_pages(path: Path) -> list[str]:
    reader = PdfReader(str(path), strict=False)
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(clean_text(page.extract_text() or ""))
        except Exception:
            pages.append("")
    return pages


def import_ocr():
    if str(OCR_PACKAGES) not in sys.path:
        sys.path.insert(0, str(OCR_PACKAGES))
    os.environ.setdefault("OC_DISABLE_DOT_ACCESS_WARNING", "1")
    import pypdfium2 as pdfium  # type: ignore
    from rapidocr import RapidOCR  # type: ignore

    return pdfium, RapidOCR


def ocr_pages(path: Path, page_numbers: list[int], pages: list[str]) -> tuple[list[str], int]:
    pdfium, RapidOCR = import_ocr()
    engine = RapidOCR()
    document = pdfium.PdfDocument(str(path))
    completed = 0
    total = len(page_numbers)
    for position, page_number in enumerate(page_numbers, 1):
        index = page_number - 1
        if index < 0 or index >= len(document):
            continue
        result = engine(document[index].render(scale=1.25).to_pil())
        text = "\n".join(result.txts or []) if result else ""
        pages[index] = clean_text(text)
        completed += 1
        if position == 1 or position % 8 == 0 or position == total:
            print(f"  OCR {position}/{total} (PDF page {page_number})", flush=True)
    return pages, completed


def parse_toc_numbers(toc_text: str) -> dict[str, object]:
    flat = re.sub(r"\s+", " ", toc_text)

    def find(label: str) -> int | None:
        before = re.search(r"\b(\d{1,3})\s*" + label, flat, flags=re.IGNORECASE)
        if before:
            return int(before.group(1))
        after = re.search(label + r"\s*[:.\-–—]*\s*(\d{1,3})\b", flat, flags=re.IGNORECASE)
        return int(after.group(1)) if after else None

    before_values = []
    after_values = []
    for test in range(1, 5):
        label = rf"Test\s*{test}"
        before = re.search(r"\b(\d{1,3})\s*" + label, flat, flags=re.IGNORECASE)
        after = re.search(label + r"\s*[:.\-–—]*\s*(\d{1,3})\b", flat, flags=re.IGNORECASE)
        before_values.append(int(before.group(1)) if before else None)
        after_values.append(int(after.group(1)) if after else None)

    def sequence_score(values: list[int | None]) -> int:
        if any(value is None for value in values):
            return -100
        numbers = [int(value) for value in values]
        score = 4 if 5 <= numbers[0] <= 20 else -8
        for first, second in zip(numbers, numbers[1:]):
            gap = second - first
            score += 3 if 17 <= gap <= 27 else -5
        return score

    starts = before_values if sequence_score(before_values) >= sequence_score(after_values) else after_values
    last_test = int(starts[-1] or 73)
    audio_options = []
    for pattern in (
        r"\b(\d{1,3})\s*(?:Audio|Tape)scripts?",
        r"(?:Audio|Tape)scripts?\s*[:.\-–—]*\s*(\d{1,3})\b",
    ):
        match = re.search(pattern, flat, flags=re.IGNORECASE)
        if match:
            audio_options.append(int(match.group(1)))
    audio = min((value for value in audio_options if last_test + 15 <= value <= last_test + 65), default=None)
    answers = find(r"Listening\s+and\s+Reading\s+Answer\s+Keys?")
    return {"tests": starts, "audio": audio, "answers": answers}


def infer_page_offset(pages: list[str]) -> int:
    offsets: list[int] = []
    for pdf_page, text in enumerate(pages[:12], 1):
        numbers = re.findall(r"(?:^|\n)\s*(\d{1,2})\s*$", text)
        if not numbers:
            continue
        printed = int(numbers[-1])
        delta = pdf_page - printed
        if -3 <= delta <= 4:
            offsets.append(delta)
    if not offsets:
        return 0
    return max(set(offsets), key=offsets.count)


def detect_structure(pages: list[str], preliminary: dict[str, object]) -> dict[str, object]:
    detected_starts = []
    for page_number, text in enumerate(pages, 1):
        head = text[:900]
        if (
            page_number < len(pages) * 0.72
            and re.search(r"SECTION\s*1|PART\s*1", head)
            and re.search(r"Questions?\s*1\b", head, flags=re.IGNORECASE)
            and re.search(r"\bTest\s*[1-4]\b", head, flags=re.IGNORECASE)
        ):
            if not detected_starts or page_number - detected_starts[-1] > 8:
                detected_starts.append(page_number)
    starts = detected_starts[:4] if len(detected_starts) >= 4 else [int(value) for value in preliminary["tests"]]

    # Older books often render the heading as ``Tape scripts`` or inject OCR
    # punctuation between its letters.  Looking at a compact form near the
    # beginning of the page is more reliable than requiring an exact line.
    audio_candidates = []
    for page_number, text in enumerate(pages, 1):
        if page_number <= starts[-1]:
            continue
        compact = re.sub(r"[^a-z]", "", text[:500].lower())
        heading_positions = [
            compact.find(label)
            for label in ("audioscript", "tapescript")
            if compact.find(label) >= 0
        ]
        if heading_positions and min(heading_positions) <= 24 and len(alpha_words(text)) > 40:
            audio_candidates.append(page_number)
    audio = audio_candidates[0] if audio_candidates else int(preliminary["audio"])
    answer_candidates = [
        page_number
        for page_number, text in enumerate(pages, 1)
        if page_number > audio
        and (
            re.search(r"Listening\s+and\s+Reading\s+Answer\s+Keys?", text, flags=re.IGNORECASE)
            or re.search(r"(?:^|\n)\s*Answer\s+Key\s*(?:\n|$)", text, flags=re.IGNORECASE)
        )
    ]
    answers = answer_candidates[0] if answer_candidates else int(preliminary["answers"])
    return {"tests": starts, "audio": audio, "answers": answers, "pageOffset": preliminary.get("pageOffset", 0)}


def infer_ranges(volume: int, pages: list[str], scanned: bool, path: Path) -> tuple[list[str], dict[str, object], int]:
    ocr_count = 0
    if scanned:
        pages, count = ocr_pages(path, list(range(1, min(10, len(pages)) + 1)), pages)
        ocr_count += count
    toc = parse_toc_numbers("\n".join(pages[:10]))
    page_offset = infer_page_offset(pages)
    starts = list(toc["tests"])
    # The modern Academic books consistently place four tests at roughly 21-page intervals.
    defaults = [10, 31, 52, 73]
    for index, value in enumerate(starts):
        if value is None:
            starts[index] = defaults[index]
    starts = [int(value) + page_offset for value in starts]
    audio = int(toc["audio"] or (int(starts[-1]) + 21 - page_offset)) + page_offset
    raw_answers = int(toc["answers"] or 0)
    # OCR can drop the leading digit in three-digit TOC page numbers (for
    # example 119 -> 19/68).  An answer-key boundary must sit after the
    # audioscripts; otherwise scan a deliberately wider tail and let the
    # section-heading detector find the real boundary.
    printed_audio = audio - page_offset
    if raw_answers > printed_audio:
        answers = raw_answers + page_offset
    else:
        answers = min(len(pages), audio + 36)
    if scanned:
        candidates: set[int] = set()
        for index, start in enumerate(starts):
            next_start = int(starts[index + 1]) if index < 3 else audio
            candidates.update(range(int(start) + 6, next_start))
        candidates.update(range(audio, min(answers + 2, len(pages) + 1)))
        candidates = {page for page in candidates if 1 <= page <= len(pages)}
        pages, count = ocr_pages(path, sorted(candidates), pages)
        ocr_count += count
    toc = detect_structure(pages, {"tests": starts, "audio": audio, "answers": answers, "pageOffset": page_offset})
    toc.update(STRUCTURE_OVERRIDES.get(volume, {}))
    if int(toc["answers"]) <= int(toc["audio"]):
        toc["answers"] = min(len(pages), int(toc["audio"]) + 36)
    return pages, toc, ocr_count


def split_marked_blocks(text: str, pattern: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    rows: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        rows.append((match.group(1), clean_text(text[match.start():end])))
    return rows


def strip_after(text: str, patterns: list[str]) -> str:
    end = len(text)
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            end = min(end, match.start())
    return clean_text(text[:end])


def extract_sections(volume: int, year: int, pages: list[str], toc: dict[str, object], extraction: str, source_hash: str) -> list[dict[str, object]]:
    starts = [int(value) for value in toc["tests"]]
    audio = int(toc["audio"])
    answers = int(toc["answers"])
    sections: list[dict[str, object]] = []

    for test_index, start in enumerate(starts, 1):
        end = starts[test_index] - 1 if test_index < 4 else audio - 1
        test_text = "\n".join(pages[start - 1:end])
        reading_part = re.split(r"\bWRITING\s+TASK\s*1\b", test_text, maxsplit=1)[0]
        passage_candidates = list(re.finditer(r"READING\s+PASSAGE\s*([123])", reading_part, flags=re.IGNORECASE))
        passage_matches = []
        cursor = 0
        for expected_passage in (1, 2, 3):
            marker = next(
                (
                    item
                    for item in passage_candidates
                    if int(item.group(1)) == expected_passage and item.start() >= cursor
                ),
                None,
            )
            if marker:
                passage_matches.append(marker)
                cursor = marker.start() + 1
        for index, marker in enumerate(passage_matches):
            passage = int(marker.group(1))
            block_end = passage_matches[index + 1].start() if index + 1 < len(passage_matches) else len(reading_part)
            text = clean_text(reading_part[marker.start():block_end])
            if len(alpha_words(text)) < 120:
                continue
            sections.append({
                "id": f"cambridge-{volume}-test-{test_index}-reading-{passage}",
                "volume": volume,
                "year": year,
                "skill": "Reading",
                "documentType": "reading_passage_with_questions",
                "test": test_index,
                "part": int(passage),
                "text": text,
                "extraction": extraction,
                "sourceHash": source_hash,
            })

        writing_candidates = list(re.finditer(r"WRIT(?:I|1)NG\s+TASK\s*([12Z])", test_text, flags=re.IGNORECASE))
        # Ignore references to writing that occur in the Listening/Reading
        # pages.  The Academic Writing prompts follow the final Reading
        # passage; General Training material may follow the Speaking page in
        # older combined books and is cut off below.
        writing_floor = passage_matches[-1].start() if passage_matches else 0
        writing_candidates = [item for item in writing_candidates if item.start() > writing_floor]
        writing_matches = []
        cursor = 0
        for expected_task in (1, 2):
            match = next(
                (
                    item
                    for item in writing_candidates
                    if (2 if item.group(1).upper() == "Z" else int(item.group(1))) == expected_task and item.start() >= cursor
                ),
                None,
            )
            if match:
                writing_matches.append(match)
                cursor = match.start() + 1
        for index, match in enumerate(writing_matches):
            task = 2 if match.group(1).upper() == "Z" else int(match.group(1))
            if index + 1 < len(writing_matches):
                block_end = writing_matches[index + 1].start()
            else:
                speaking_boundary = re.search(r"\bSPEAK(?:I|1)NG\b", test_text[match.end():], flags=re.IGNORECASE)
                block_end = match.end() + speaking_boundary.start() if speaking_boundary else len(test_text)
            text = clean_text(test_text[match.start():block_end])
            # Only the two task prompts at the end of each Academic test belong here.
            if task not in {1, 2} or len(alpha_words(text)) < 25:
                continue
            sections.append({
                "id": f"cambridge-{volume}-test-{test_index}-writing-{task}",
                "volume": volume,
                "year": year,
                "skill": "Writing",
                "documentType": "writing_prompt",
                "test": test_index,
                "part": task,
                "text": text,
                "extraction": extraction,
                "sourceHash": source_hash,
            })

    # If damaged OCR hides one of the three passage headings or one of the two
    # writing-task headings, replace that test's partial extraction with
    # page-level units spanning the complete skill range.  This prevents a
    # cosmetically neat section count from dropping real source text.
    for test_index, start in enumerate(starts, 1):
        end = starts[test_index] - 1 if test_index < 4 else audio - 1
        page_numbers = list(range(start, end + 1))
        compact_pages = {
            page_number: re.sub(r"[^a-z0-9]", "", pages[page_number - 1].lower())
            for page_number in page_numbers
        }
        reading_candidates = [
            page_number
            for page_number in page_numbers
            if "readingpassage" in compact_pages[page_number]
            or ("reading" in compact_pages[page_number] and "questions1" in compact_pages[page_number])
        ]
        writing_candidates = [
            page_number
            for page_number in page_numbers
            if "writingtask" in compact_pages[page_number]
            or ("writing" in compact_pages[page_number] and "task1" in compact_pages[page_number])
        ]
        speaking_candidates = [
            page_number
            for page_number in page_numbers
            if ("examiner" in compact_pages[page_number] or "candidate" in compact_pages[page_number])
            and "part1" in compact_pages[page_number]
        ]

        reading_rows = [row for row in sections if row["skill"] == "Reading" and row["test"] == test_index]
        if len(reading_rows) < 3 and reading_candidates:
            sections = [row for row in sections if not (row["skill"] == "Reading" and row["test"] == test_index)]
            first_reading = min(reading_candidates)
            first_writing = min((page for page in writing_candidates if page > first_reading), default=end - 1)
            for page_number in range(first_reading, first_writing):
                text = clean_text(pages[page_number - 1])
                if len(alpha_words(text)) < 60:
                    continue
                sections.append({
                    "id": f"cambridge-{volume}-test-{test_index}-reading-page-{page_number}",
                    "volume": volume,
                    "year": year,
                    "skill": "Reading",
                    "documentType": "reading_page_segment",
                    "test": test_index,
                    "part": page_number - first_reading + 1,
                    "text": text,
                    "extraction": extraction + "_page_fallback",
                    "sourceHash": source_hash,
                })

        writing_rows = [row for row in sections if row["skill"] == "Writing" and row["test"] == test_index]
        if len(writing_rows) < 2 and writing_candidates:
            sections = [row for row in sections if not (row["skill"] == "Writing" and row["test"] == test_index)]
            first_writing = max(start, min(writing_candidates) - 1)
            first_speaking = min((page for page in speaking_candidates if page >= first_writing), default=end + 1)
            for page_number in range(first_writing, first_speaking):
                text = clean_text(pages[page_number - 1])
                if len(alpha_words(text)) < 20:
                    continue
                sections.append({
                    "id": f"cambridge-{volume}-test-{test_index}-writing-page-{page_number}",
                    "volume": volume,
                    "year": year,
                    "skill": "Writing",
                    "documentType": "writing_page_segment",
                    "test": test_index,
                    "part": page_number - first_writing + 1,
                    "text": text,
                    "extraction": extraction + "_page_fallback",
                    "sourceHash": source_hash,
                })

    audio_text = "\n".join(pages[audio - 1:answers - 1])
    audio_buckets: dict[tuple[int, int], list[str]] = {}
    marker_pattern = r"(?:S\s*E\s*C\s*T\s*I\s*O\s*N|P\s*A\s*R\s*T)\s*([1-4])"
    markers = list(re.finditer(marker_pattern, audio_text, flags=re.IGNORECASE))
    test_number = 0
    previous_part = 4
    for index, marker in enumerate(markers):
        part_number = int(marker.group(1))
        if part_number == 1 and previous_part != 1:
            test_number += 1
        previous_part = part_number
        if not (1 <= test_number <= 4):
            continue
        block_end = markers[index + 1].start() if index + 1 < len(markers) else len(audio_text)
        audio_buckets[(test_number, part_number)] = [clean_text(audio_text[marker.end():block_end])]
    # A partially recognised marker sequence must not silently drop transcript
    # text.  When all 16 semantic parts cannot be recovered, replace the
    # partial result with page-level statistical units that cover the complete
    # audioscript range exactly once.  These units are used only for aggregate
    # vocabulary/chunk statistics and are labelled honestly as page segments.
    audio_fallback_pages: list[tuple[int, str]] = []
    if len(audio_buckets) != 16:
        audio_buckets = {}
        for page_number in range(audio, answers):
            text = clean_text(pages[page_number - 1])
            if len(alpha_words(text)) >= 70:
                audio_fallback_pages.append((page_number, text))
    print(
        "  audio buckets="
        + str({f"T{test}P{part}": len(alpha_words(" ".join(lines))) for (test, part), lines in sorted(audio_buckets.items())}),
        flush=True,
    )
    for (test_number, part_number), lines in sorted(audio_buckets.items()):
            text = clean_text("\n".join(lines))
            if len(alpha_words(text)) < 70:
                continue
            sections.append({
                "id": f"cambridge-{volume}-test-{test_number}-listening-{part_number}",
                "volume": volume,
                "year": year,
                "skill": "Listening",
                "documentType": "listening_transcript",
                "test": test_number,
                "part": part_number,
                "text": text,
                "extraction": extraction,
                "sourceHash": source_hash,
            })

    for segment_number, (page_number, text) in enumerate(audio_fallback_pages, 1):
        sections.append({
            "id": f"cambridge-{volume}-listening-page-{page_number}",
            "volume": volume,
            "year": year,
            "skill": "Listening",
            "documentType": "listening_transcript_page_segment",
            "test": 0,
            "part": segment_number,
            "text": text,
            "extraction": extraction + "_page_fallback",
            "sourceHash": source_hash,
        })

    speaking_pages = []
    speaking_part_pattern = r"P\s*A\s*R\s*T\s*([123])"
    for page_number, text in enumerate(pages[:audio - 1], 1):
        compact = re.sub(r"[^a-z]", "", text.lower())
        parts = re.findall(speaking_part_pattern, text, flags=re.IGNORECASE)
        looks_like_interview = "examiner" in compact or "candidate" in compact
        if len(set(parts)) >= 2 and looks_like_interview:
            speaking_pages.append((page_number, text))
    for page_number, text in speaking_pages:
        candidates = list(re.finditer(speaking_part_pattern, text, flags=re.IGNORECASE))
        markers = []
        cursor = 0
        for expected_part in (1, 2, 3):
            marker = next(
                (item for item in candidates if int(item.group(1)) == expected_part and item.start() >= cursor),
                None,
            )
            if marker:
                markers.append(marker)
                cursor = marker.start() + 1
        for index, marker in enumerate(markers):
            part_number = int(marker.group(1))
            block_end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
            block = clean_text(text[marker.start():block_end])
            if len(alpha_words(block)) < 18:
                continue
            sections.append({
                "id": f"cambridge-{volume}-speaking-{page_number}-{part_number}",
                "volume": volume,
                "year": year,
                "skill": "Speaking",
                "documentType": "speaking_prompt",
                "test": 0,
                "part": part_number,
                "text": block,
                "extraction": extraction,
                "sourceHash": source_hash,
            })
    return sections


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract private Cambridge IELTS sections for aggregate statistics.")
    parser.add_argument("--volumes", default="4-21", help="Comma-separated volumes or a range such as 4-21")
    parser.add_argument("--force", action="store_true", help="Ignore an existing volume cache")
    parser.add_argument("--resegment", action="store_true", help="Reuse cached page text but rerun section detection")
    args = parser.parse_args()
    if "-" in args.volumes and "," not in args.volumes:
        first, last = (int(value) for value in args.volumes.split("-", 1))
        volumes = list(range(first, last + 1))
    else:
        volumes = [int(value) for value in args.volumes.split(",")]

    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    existing: dict[int, dict[str, object]] = {}
    if OUTPUT.exists():
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        for item in old.get("volumes", []):
            existing[int(item["volume"])] = item

    volume_rows: list[dict[str, object]] = []
    all_sections: list[dict[str, object]] = []
    for volume in sorted(VOLUME_YEARS):
        if volume not in volumes and volume in existing:
            volume_rows.append(existing[volume])
            all_sections.extend(existing[volume].get("sections", []))
            continue
        if volume not in volumes:
            continue
        path = choose_pdf(volume)
        source_hash = file_sha256(path)
        cached = existing.get(volume)
        if cached and cached.get("sourceHash") == source_hash and not args.force and not args.resegment:
            print(f"Cambridge {volume}: cache hit", flush=True)
            volume_rows.append(cached)
            all_sections.extend(cached.get("sections", []))
            continue
        print(f"Cambridge {volume}: extracting {path.name}", flush=True)
        if cached and cached.get("sourceHash") == source_hash and args.resegment:
            pages = list(cached["pageTexts"])
            toc = dict(cached["toc"])
            toc.update(STRUCTURE_OVERRIDES.get(volume, {}))
            extraction = str(cached.get("extraction") or "cached_text")
            ocr_count = int(cached.get("ocrPageCount") or 0)
        else:
            pages = pdf_text_pages(path)
            sampled_words = sum(len(alpha_words(text)) for text in pages[:12])
            scanned = sampled_words < 250
            pages, toc, ocr_count = infer_ranges(volume, pages, scanned, path)
            extraction = "ocr" if scanned else "embedded_text"
        sections = extract_sections(volume, VOLUME_YEARS[volume], pages, toc, extraction, source_hash)
        section_ids = [str(section["id"]) for section in sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError(f"Cambridge {volume}: duplicate section ids")
        for skill in ("Reading", "Writing"):
            covered_tests = {int(section["test"]) for section in sections if section["skill"] == skill}
            if covered_tests != {1, 2, 3, 4}:
                raise ValueError(f"Cambridge {volume}: {skill} does not cover all four tests: {sorted(covered_tests)}")
        listening_rows = [section for section in sections if section["skill"] == "Listening"]
        listening_tests = {int(section["test"]) for section in listening_rows}
        if listening_tests != {1, 2, 3, 4} and not (listening_tests == {0} and len(listening_rows) >= 16):
            raise ValueError(f"Cambridge {volume}: incomplete Listening coverage")
        if not any(section["skill"] == "Speaking" for section in sections):
            raise ValueError(f"Cambridge {volume}: no Speaking prompt units")
        by_skill = {skill: sum(1 for row in sections if row["skill"] == skill) for skill in ("Listening", "Speaking", "Reading", "Writing")}
        print(f"  sections={by_skill} OCR pages={ocr_count} TOC={toc}", flush=True)
        row = {
            "volume": volume,
            "year": VOLUME_YEARS[volume],
            "sourceFile": path.name,
            "sourceHash": source_hash,
            "extraction": extraction,
            "ocrPageCount": ocr_count,
            "toc": toc,
            "pageTexts": pages,
            "sections": sections,
        }
        volume_rows.append(row)
        all_sections.extend(sections)
        OUTPUT.write_text(json.dumps({"generatedAt": datetime.now(timezone.utc).isoformat(), "volumes": sorted(volume_rows, key=lambda item: int(item["volume"])), "sections": all_sections}, ensure_ascii=False), encoding="utf-8")

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "copyrightPolicy": "Private local extraction cache. Raw Cambridge text must never be copied into the public site repository.",
        "volumes": sorted(volume_rows, key=lambda item: int(item["volume"])),
        "sections": all_sections,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    counts = {skill: sum(1 for row in all_sections if row["skill"] == skill) for skill in ("Listening", "Speaking", "Reading", "Writing")}
    print(f"Wrote private cache: {OUTPUT}", flush=True)
    print(json.dumps({"volumes": len(volume_rows), "sections": counts}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
