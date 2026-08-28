from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT.parent
MATERIAL_ROOT = STUDY_ROOT / "资料"
BUILD_ROOT = STUDY_ROOT / "outputs" / "ielts-corpus-build"
OUTPUT = BUILD_ROOT / "local_speaking_topics.csv"

SOURCES = [
    {
        "path": MATERIAL_ROOT / "2026年口语题库" / "2026" / "1-4月（持续更新中）" / "雅s哥（仅题目）" / "2026年1-4月最新雅思口语题库-0324.pdf",
        "name": "本地 2026 1–4 月口语题库（截至 3.24）",
        "period": "2026-01–04",
        "phase": "current_2026",
        "parser": "full",
    },
    {
        "path": MATERIAL_ROOT / "2026年口语题库" / "2026" / "5-8月（保留题已更新，新题后续会持续搜集更新，请耐心等待！）" / "雅思哥新题" / "2026年5-8月最新雅思口语题库-0604.pdf",
        "name": "本地 2026 5–8 月口语题库（截至 6.4）",
        "period": "2026-05–08",
        "phase": "current_2026",
        "parser": "full",
    },
    {
        "path": MATERIAL_ROOT / "2026年9-12月口语题库（包含部分其它资料包）" / "2026年9-12月口语题库" / "2026年9-12月雅思口语保留题_纯题目版.pdf",
        "name": "本地 2026 9–12 月口语预测保留题",
        "period": "2026-09–12",
        "phase": "upcoming_prediction",
        "parser": "forecast",
    },
]

FIELDS = [
    "source_name", "source_status", "period", "region", "topic_number", "topic_title",
    "part_structure", "primary_theme", "part_1_questions", "part_2_cue_cards",
    "part_3_questions", "question_count", "integration_quality", "source_url", "phase",
]


def clean_line(value: str) -> str:
    value = value.replace("\u3000", " ").replace("？", "?").replace("’", "'")
    return re.sub(r"\s+", " ", value).strip()


def pdf_text(path: Path) -> str:
    reader = PdfReader(str(path), strict=False)
    return "\n".join((page.extract_text() or "").replace("\r", "\n") for page in reader.pages)


def english_question_lines(text: str) -> list[str]:
    rows: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        line = re.sub(r"^\d+\s*[.)]\s*", "", line)
        if not line or line == "P3" or re.fullmatch(r"\d+", line):
            continue
        if not re.search(r"[A-Za-z]", line):
            continue
        current.append(line)
        if "?" in line:
            value = clean_line(" ".join(current))
            value = value[: value.rfind("?") + 1]
            if len(re.findall(r"[A-Za-z]+", value)) >= 4:
                rows.append(value)
            current = []
    return rows


def primary_theme(title: str, text: str) -> str:
    value = f"{title} {text}".lower()
    rules = [
        ("food", r"\bfood|meal|cook|restaurant|diet"),
        ("travel-transport", r"\btravel|trip|journey|car|transport|bicycle|traffic"),
        ("home/hometown/accommodation", r"\bhome|hometown|accommodation|neighbou?rhood|where you live"),
        ("work-study", r"\bwork|job|career|teacher|school|study|learn|education|language"),
        ("person/family/friends", r"\bperson|friend|family|child|parent|people|doctor|nurse"),
        ("object/technology", r"\btechnology|phone|app|website|watch|headphone|computer|object|item"),
        ("place", r"\bplace|city|building|park|garden|shop|store"),
        ("society-government", r"\blaw|government|advertis|news|environment"),
        ("culture", r"\bculture|tradition|history|festival"),
        ("activity/hobby", r"\bmusic|sing|sport|hobby|reading|film|movie|art|walk"),
        ("event/experience", r"\bexperience|occasion|decision|plan|goal|problem|help|advice"),
    ]
    for theme, pattern in rules:
        if re.search(pattern, value):
            return theme
    return "other"


def make_row(source: dict[str, object], number: int, title: str, part1: list[str], part2: list[str], part3: list[str], quality: str) -> dict[str, str]:
    parts = []
    if part1:
        parts.append("Part 1")
    if part2:
        parts.append("Part 2")
    if part3:
        parts.append("Part 3")
    all_text = "\n".join(part1 + part2 + part3)
    return {
        "source_name": str(source["name"]),
        "source_status": "local_private_compilation",
        "period": str(source["period"]),
        "region": "China (Mainland)",
        "topic_number": str(number),
        "topic_title": clean_line(title),
        "part_structure": " / ".join(parts),
        "primary_theme": primary_theme(title, all_text),
        "part_1_questions": "\n".join(f"{index}. {value}" for index, value in enumerate(part1, 1)),
        "part_2_cue_cards": "\n".join(f"{index}. {value}" for index, value in enumerate(part2, 1)),
        "part_3_questions": "\n".join(f"{index}. {value}" for index, value in enumerate(part3, 1)),
        "question_count": str(len(part1) + len(part2) + len(part3)),
        "integration_quality": quality,
        "source_url": "",
        "phase": str(source["phase"]),
    }


def parse_full(source: dict[str, object], text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # Ignore the table of contents; real topic blocks begin after the usage guide.
    marker = text.find("一、大陆地区新题")
    body = text[marker:] if marker >= 0 else text
    p1_matches = list(re.finditer(r"(?m)^(?:\d+\s+P1|万年老题)\s+([^\n]+)$", body))
    p2_start = re.search(r"(?m)^Part\s*2&3[^\n]*$", body)
    for index, match in enumerate(p1_matches):
        if p2_start and match.start() > p2_start.start():
            break
        end_candidates = [next_match.start() for next_match in p1_matches[index + 1:index + 2]]
        if p2_start:
            end_candidates.append(p2_start.start())
        end = min(end_candidates) if end_candidates else len(body)
        questions = english_question_lines(body[match.end():end])
        if questions:
            rows.append(make_row(source, len(rows) + 1, match.group(1), questions, [], [], "local_question_pdf_exact"))

    p2_matches = list(re.finditer(r"(?m)^\d+\s+P2\s+([^\n]+)$", body))
    for index, match in enumerate(p2_matches):
        end = p2_matches[index + 1].start() if index + 1 < len(p2_matches) else len(body)
        block = body[match.end():end]
        cue_part, separator, p3_part = block.partition("\nP3\n")
        cue_lines = []
        started = False
        for raw in cue_part.splitlines():
            line = clean_line(raw)
            if re.fullmatch(r"\d+", line):
                continue
            if re.match(r"(?:Describe|A high-rise|Local news)", line, flags=re.IGNORECASE):
                started = True
            if started and re.search(r"[A-Za-z]", line):
                cue_lines.append(line)
        cue = clean_line(" ".join(cue_lines))
        part2 = [cue] if len(re.findall(r"[A-Za-z]+", cue)) >= 12 else []
        part3 = english_question_lines(p3_part if separator else "")
        if part2 or part3:
            topic_title = cue_lines[0] if cue_lines else match.group(1)
            rows.append(make_row(source, len(rows) + 1, topic_title, [], part2, part3, "local_question_pdf_exact"))
    return rows


def parse_numbered_topics(section: str) -> list[tuple[str, list[str]]]:
    lines = [clean_line(line) for line in section.splitlines()]
    result: list[tuple[str, list[str]]] = []
    title = ""
    question_buffer: list[str] = []
    for line in lines:
        if not line or re.fullmatch(r"\d+", line):
            continue
        numbered = re.match(r"^\d+\s*[.)]\s*(.+)$", line)
        if numbered:
            question_buffer.append(numbered.group(1))
            continue
        if "?" in line and question_buffer:
            question_buffer[-1] = clean_line(question_buffer[-1] + " " + line)
            continue
        if re.search(r"[A-Za-z]", line) and "?" not in line and not line.lower().startswith(("part ", "you should", "and explain")):
            if title and question_buffer:
                result.append((title, english_question_lines("\n".join(question_buffer))))
            title = line
            question_buffer = []
    if title and question_buffer:
        result.append((title, english_question_lines("\n".join(question_buffer))))
    return result


def parse_forecast(source: dict[str, object], text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    part1_match = re.search(r"(?m)^Part\s*1\s*$", text)
    part2_match = re.search(r"(?m)^Part\s*2\s*$", text)
    part3_match = re.search(r"(?m)^Part\s*3\s*$", text)
    if not (part1_match and part2_match and part3_match):
        return rows
    for title, questions in parse_numbered_topics(text[part1_match.end():part2_match.start()]):
        if questions:
            rows.append(make_row(source, len(rows) + 1, title, questions, [], [], "local_forecast_pdf_exact"))

    part2_text = text[part2_match.end():part3_match.start()]
    cue_matches = list(re.finditer(r"(?m)^(?P<title>(?:Describe|A high-rise|Local news)[^\n]+)\nYou should say:", part2_text, flags=re.IGNORECASE))
    cues: list[tuple[str, str]] = []
    for index, match in enumerate(cue_matches):
        end = cue_matches[index + 1].start() if index + 1 < len(cue_matches) else len(part2_text)
        cue = clean_line(part2_text[match.start():end])
        cues.append((clean_line(match.group("title")), cue))
        rows.append(make_row(source, len(rows) + 1, match.group("title"), [], [cue], [], "local_forecast_pdf_exact"))

    part3_topics = parse_numbered_topics(text[part3_match.end():])
    for title, questions in part3_topics:
        if not questions:
            continue
        # Merge Part 3 questions into the nearest existing cue topic when titles overlap.
        normalized = re.sub(r"[^a-z]+", " ", title.lower()).strip()
        target = None
        for row in reversed(rows):
            candidate = re.sub(r"[^a-z]+", " ", row["topic_title"].lower()).strip()
            if normalized and (normalized in candidate or candidate in normalized):
                target = row
                break
        if target and "Part 2" in target["part_structure"]:
            target["part_3_questions"] = "\n".join(f"{index}. {value}" for index, value in enumerate(questions, 1))
            target["part_structure"] = "Part 2 / Part 3"
            target["question_count"] = str(int(target["question_count"]) + len(questions))
        else:
            rows.append(make_row(source, len(rows) + 1, title, [], [], questions, "local_forecast_pdf_exact"))
    return rows


def main() -> None:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    audit = []
    for source in SOURCES:
        path = Path(source["path"])
        if not path.exists():
            raise FileNotFoundError(path)
        text = pdf_text(path)
        parsed = parse_full(source, text) if source["parser"] == "full" else parse_forecast(source, text)
        question_count = sum(int(row["question_count"]) for row in parsed)
        if source["parser"] == "full" and question_count < 250:
            raise RuntimeError(f"Too few questions parsed from {path.name}: {question_count}")
        if source["parser"] == "forecast" and question_count < 70:
            raise RuntimeError(f"Too few forecast questions parsed from {path.name}: {question_count}")
        rows.extend(parsed)
        audit.append({"source": source["name"], "topics": len(parsed), "questions": question_count})
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": str(OUTPUT), "rows": len(rows), "sources": audit}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
