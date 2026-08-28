from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT.parent / "雅思语料研究"
MATERIAL_ROOT = ROOT.parent / "资料"
BUILD_ROOT = ROOT.parent / "outputs" / "ielts-corpus-build"
CAMBRIDGE_CACHE = BUILD_ROOT / "cambridge_sections.json"
LOCAL_SPEAKING = BUILD_ROOT / "local_speaking_topics.csv"
OUTPUT = ROOT / "data" / "corpus.json"

STOP = set("""a an the and or but if then than so of in on at to from for with by as is are was were be been being do does did have has had this that these those it its they them their there here i you your we our he she him his her what which who how why when where can could may might should would will shall must not no yes about into over under between during after before more most some any each every other another also very just all both either neither only own same too out up down again further once while because however although though themselves yourself such even through around still less often""".split())
INSTRUCTION = set("""ielts test tests academic general reading listening writing speaking question questions answer answers task tasks sample section part passage page pages recording transcript tapescript candidate candidates examiner narrator choose correct letter letters box boxes sheet complete completion following below write read hear listen word words no more than true false given match matching option options label diagram table note summary sentence short multiple choice instruction instructions""".split())
BASIC = set("""one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty first second third last next now well good better best great bad big small new old man woman people person time year day thing things something number end get got make made know knew use used look looked come came go went take took say said tell told give gave want wanted like liked see saw really maybe much many little lot lots okay yeah sure adj""".split())
TASK_NOISE = set("""describe describes described describing discuss discusses discussed discussing opinion agree disagree extent essay introduction conclusion paragraph paragraphs chart charts graph graphs bar bars pie map maps process processes table tables show shows shown showing compare compares compared comparing comparison illustrate illustrates illustrated illustrating overview figure figures statement statements heading headings summarise summarize""".split())
PROPER_NOISE = set("""jack paul rachel marie curie judy ray british china chinese london america american australia canada cambridge""".split())
SKILL_NOISE = {
    "Reading": set("information statement statements claim claims writer paragraph paragraphs heading headings box boxes sheet sheets spend minute minutes list lists use using example examples says".split()),
    "Writing": set("spend minute minutes example examples relevant reason reasons answer knowledge experience explain support".split()),
}
IRREGULAR = {
    "people": "people", "children": "child", "men": "man", "women": "woman",
    "countries": "country", "cities": "city", "studies": "study", "activities": "activity",
    "companies": "company", "communities": "community", "technologies": "technology",
    "media": "media", "data": "data", "movies": "movie",
}
INVARIANT = {"always", "perhaps", "species", "series", "news", "clothes", "means"}

GROUP_META = {
    "official_public": ("官方公开材料", 1.0),
    "cambridge_practice": ("剑桥官方练习册", 0.95),
    "cambridge_derived": ("剑桥真题派生词汇", 0.9),
    "test_taker_recall": ("考生回忆", 0.6),
    "public_compilation": ("公开非官方汇编", 0.5),
    "user_provided": ("用户手动提供", 0.5),
    "local_question_bank": ("本地题库汇编", 0.45),
    "third_party_prediction": ("第三方预测题", 0.35),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_text(value: object) -> str:
    text = str(value or "").replace("’", "'").replace("“", " ").replace("”", " ")
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str) -> str:
    normalized = re.sub(r"[^a-z]+", "", clean_text(text).lower())
    return hashlib.sha256(normalized.encode()).hexdigest()


def source_id(name: str) -> str:
    return "src_" + hashlib.sha1(name.encode()).hexdigest()[:14]


def doc_id(seed: str) -> str:
    return "doc_" + hashlib.sha1(seed.encode()).hexdigest()[:16]


def lemma(word: str) -> str:
    word = word.lower().strip("'")
    if word.endswith("'s"):
        word = word[:-2]
    if word in IRREGULAR:
        return IRREGULAR[word]
    if word in INVARIANT:
        return word
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith(("ches", "shes", "sses", "xes", "zes")):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is", "ous")):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    output = []
    for raw in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text or ""):
        raw = raw.lower()
        if "'" in raw or len(raw) <= 2 or raw in STOP | INSTRUCTION | BASIC | TASK_NOISE | PROPER_NOISE:
            continue
        value = lemma(raw)
        if len(value) <= 2 or value in STOP | INSTRUCTION | BASIC | TASK_NOISE | PROPER_NOISE:
            continue
        output.append(value)
    return output


def period_from_path(path: Path) -> str:
    value = str(path)
    year = "2026" if "2026" in value or re.search(r"(?<!\d)26年", value) else ("2025" if "2025" in value or re.search(r"(?<!\d)25年", value) else "")
    month = re.search(r"(?<!\d)(1[0-2]|[1-9])月", value)
    return f"{year}-{int(month.group(1)):02d}" if year and month else year


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path), strict=False)
    return clean_text(" ".join(page.extract_text() or "" for page in reader.pages))


def existing_group(row: dict[str, str]) -> str:
    return {
        "official_public_sample": "official_public",
        "test_taker_recall": "test_taker_recall",
        "public_compilation_unofficial": "public_compilation",
        "user_provided_copy_unofficial": "user_provided",
    }.get(row.get("source_status", ""), "public_compilation")


def split_numbered(raw: str) -> list[str]:
    rows = []
    current = []
    for raw_line in raw.replace("\r", "\n").splitlines():
        line = clean_text(raw_line)
        if not line:
            continue
        if re.match(r"^\d+\s*[.)]\s*", line):
            if current:
                rows.append(clean_text(" ".join(current)))
            current = [re.sub(r"^\d+\s*[.)]\s*", "", line)]
        elif current:
            current.append(line)
        else:
            current = [line]
    if current:
        rows.append(clean_text(" ".join(current)))
    return [value for value in rows if len(re.findall(r"[A-Za-z]+", value)) >= 4]


classified = read_csv(STUDY_ROOT / "outputs" / "data" / "classified_corpus.csv")
integrated = read_csv(STUDY_ROOT / "outputs" / "data" / "speaking_integrated_topics.csv")
local_speaking = read_csv(LOCAL_SPEAKING)
cambridge = json.loads(CAMBRIDGE_CACHE.read_text(encoding="utf-8"))

documents: list[dict[str, object]] = []
source_blueprints: dict[str, dict[str, object]] = {}


def register_source(name: str, publisher: str, group: str, skill: str, period: str, url: str, rights: str, display: str, notes: str) -> str:
    sid = source_id(name)
    source_blueprints.setdefault(sid, {
        "id": sid, "name": name, "publisher": publisher, "sourceGroup": group,
        "rightsStatus": rights, "publicDisplay": display, "skill": skill,
        "period": period, "url": url, "notes": notes,
    })
    return sid


for row in classified:
    if row.get("source_status") == "excluded_by_terms":
        continue
    text = clean_text(row.get("question_text"))
    if not text:
        continue
    group = existing_group(row)
    name = row["source_name"]
    publisher = "IELTS.org" if group == "official_public" else ("IELTS-Blog" if "IELTS-Blog" in name else ("Joe Speaking" if "Joe Speaking" in name else "Public compilation"))
    period = (row.get("published_date") or "")[:7]
    if not period:
        year = re.search(r"20\d{2}", name)
        period = year.group() if year else ""
    sid = register_source(name, publisher, group, row["skill"], period, row.get("source_url", ""), "copyright_retained", "metadata_and_aggregate", "Public site stores counts, metadata and source links; full copyrighted content is not republished.")
    documents.append({
        "id": row.get("record_id") or doc_id(name + text), "sourceId": sid, "skill": row["skill"],
        "period": period, "documentType": row.get("text_role") or "question_prompt", "tokens": tokenize(text),
    })

local_specs = []
for path in MATERIAL_ROOT.rglob("*.pdf"):
    if "剑" in path.name and "同义词" in path.name:
        local_specs.append((path, "Listening", "cambridge_derived"))
    elif "阅读试题" in path.name:
        local_specs.append((path, "Reading", "third_party_prediction"))
    elif "听力文本" in path.name or "听力原文" in path.name:
        local_specs.append((path, "Listening", "third_party_prediction"))

seen_local = set()
local_failures = []
for path, skill, group in local_specs:
    try:
        text = extract_pdf(path)
    except Exception as exc:
        local_failures.append({"file": path.name, "error": str(exc)[:160]})
        continue
    if len(text) < 100:
        continue
    digest = content_hash(text)
    if (skill, group, digest) in seen_local:
        continue
    seen_local.add((skill, group, digest))
    period = "" if group == "cambridge_derived" else period_from_path(path)
    if group == "cambridge_derived":
        name, publisher, notes = "剑桥雅思 C4-C16 同义替换资料（本地派生）", "Third-party notes derived from Cambridge IELTS", "Local derivative notes from Cambridge IELTS volumes 4-16; kept as a separate vocabulary layer."
    elif skill == "Reading":
        name, publisher, notes = "本地 2025-2026 阅读预测试题（去重）", "Third-party preparation materials", "Locally provided prediction papers, deduplicated by extracted-text hash; aggregate statistics only."
    else:
        name, publisher, notes = "本地 2025-2026 听力文本（去重）", "Third-party preparation materials", "Locally provided listening transcripts, deduplicated by extracted-text hash; aggregate statistics only."
    sid = register_source(name, publisher, group, skill, period, "", "local_private_aggregate_only", "aggregate_only", notes)
    documents.append({"id": doc_id(str(path) + digest), "sourceId": sid, "skill": skill, "period": period, "documentType": "derived_vocab_notes" if group == "cambridge_derived" else ("reading_paper" if skill == "Reading" else "listening_transcript"), "tokens": tokenize(text)})

for volume in cambridge["volumes"]:
    number = int(volume["volume"])
    year = str(volume["year"])
    name = f"Cambridge IELTS Academic {number}（本地真题册）"
    sid = register_source(name, "Cambridge University Press & Assessment", "cambridge_practice", "Listening / Speaking / Reading / Writing", year, "", "local_private_aggregate_only", "aggregate_only", "Local Cambridge IELTS practice book; only aggregate statistics and metadata are published. Raw passages, audio, images and answers remain private.")
    for section in volume.get("sections", []):
        tokens = tokenize(section["text"])
        if not tokens:
            continue
        documents.append({"id": section["id"], "sourceId": sid, "skill": section["skill"], "period": year, "documentType": section["documentType"], "tokens": tokens})

seen_speaking = set()
for row in local_speaking:
    sid = register_source(row["source_name"], "Local third-party compilation", "local_question_bank", "Speaking", row["period"], "", "local_private_aggregate_only", "attributed_questions_and_aggregate", "Local question-only PDF. Questions are deduplicated and attributed; third-party answers, images and audio are excluded. 9–12 month material is labelled as an upcoming prediction.")
    for field in ("part_1_questions", "part_2_cue_cards", "part_3_questions"):
        for text in split_numbered(row.get(field, "")):
            digest = content_hash(text)
            key = (sid, digest)
            if key in seen_speaking:
                continue
            seen_speaking.add(key)
            documents.append({"id": doc_id(row["source_name"] + field + digest), "sourceId": sid, "skill": "Speaking", "period": row["period"][:7], "documentType": field, "tokens": tokenize(text)})

for document in documents:
    skill_noise = SKILL_NOISE.get(str(document["skill"]), set())
    if skill_noise:
        document["tokens"] = [token for token in document["tokens"] if token not in skill_noise]

source_docs = defaultdict(list)
for document in documents:
    source_docs[document["sourceId"]].append(document)

sources = []
for sid, meta in source_blueprints.items():
    docs = source_docs.get(sid, [])
    if not docs:
        continue
    skills = sorted({str(doc["skill"]) for doc in docs})
    periods = sorted({str(doc["period"]) for doc in docs if doc["period"]})
    sources.append({
        **meta, "skill": " / ".join(skills),
        "period": f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else (periods[0] if periods else meta["period"]),
        "documentCount": len(docs), "wordCount": sum(len(doc["tokens"]) for doc in docs),
        "reliabilityWeight": GROUP_META[str(meta["sourceGroup"])][1],
    })


def compute_word_stats(scope: str, scoped_docs: list[dict[str, object]]) -> list[dict[str, object]]:
    skills = ("Listening", "Speaking", "Reading", "Writing")
    occurrences = defaultdict(Counter)
    doc_frequency = defaultdict(lambda: defaultdict(set))
    source_frequency = defaultdict(lambda: defaultdict(set))
    group_occurrence = defaultdict(lambda: defaultdict(Counter))
    totals = Counter()
    doc_counts = Counter()
    for document in scoped_docs:
        skill = str(document["skill"])
        tokens = list(document["tokens"])
        counts = Counter(tokens)
        group = str(source_blueprints[str(document["sourceId"])]["sourceGroup"])
        for bucket in (skill, "All"):
            doc_counts[bucket] += 1
            totals[bucket] += len(tokens)
            occurrences[bucket].update(counts)
            for word, count in counts.items():
                doc_frequency[bucket][word].add(document["id"])
                source_frequency[bucket][word].add(document["sourceId"])
                group_occurrence[bucket][word][group] += count

    top_skills = {}
    for word in occurrences["All"]:
        ranked = []
        for skill in skills:
            count = occurrences[skill][word]
            if not count:
                continue
            per_10k = count * 10000 / max(1, totals[skill])
            ranked.append((per_10k, count, skill))
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        top_skills[word] = [skill for _, _, skill in ranked[:2]]

    rows = []
    for skill in ("All", *skills):
        candidates = []
        minimum_docs = 5 if skill == "All" else (2 if skill in {"Listening", "Reading"} else 5)
        for word, count in occurrences[skill].items():
            df = len(doc_frequency[skill][word])
            if df < minimum_docs:
                continue
            source_count = len(source_frequency[skill][word])
            coverage = df / max(1, doc_counts[skill])
            per_10k = count * 10000 / max(1, totals[skill])
            high_cut = max(8, round(doc_counts[skill] * 0.12))
            confidence = "high" if df >= high_cut and source_count >= 2 else ("medium" if df >= 3 and source_count >= 2 else "exploratory")
            candidates.append((count, df, word, source_count, coverage, per_10k, confidence, group_occurrence[skill][word]))
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        # Publish every lemma that passes the documented cross-document
        # threshold.  Pagination belongs in the UI; truncating the data here
        # made a full-corpus build look like a top-750 sample.
        for rank, (count, df, word, source_count, coverage, per_10k, confidence, mix) in enumerate(candidates, 1):
            rows.append({"skill": skill, "scope": scope, "lemma": word, "display": word, "rank": rank, "occurrenceCount": count, "documentFrequency": df, "documentCoverage": round(coverage, 5), "normalizedPer10k": round(per_10k, 2), "sourceCount": source_count, "confidence": confidence, "sourceMix": dict(mix.most_common()), "topSkills": top_skills.get(word, [])})
    return rows


word_rows = compute_word_stats("overall", documents)
recent_documents = [document for document in documents if str(document["period"])[:4].isdigit() and int(str(document["period"])[:4]) >= 2021]
word_rows += compute_word_stats("recent_5y", recent_documents)


def scope_coverage(scope: str, scoped_docs: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for skill in ("All", "Listening", "Speaking", "Reading", "Writing"):
        skill_docs = scoped_docs if skill == "All" else [document for document in scoped_docs if document["skill"] == skill]
        rows.append({
            "skill": skill,
            "scope": scope,
            "documents": len(skill_docs),
            "filteredTokens": sum(len(document["tokens"]) for document in skill_docs),
            "sources": len({document["sourceId"] for document in skill_docs}),
        })
    return rows


word_scope_coverage = scope_coverage("overall", documents) + scope_coverage("recent_5y", recent_documents)

source_by_name = {str(meta["name"]): sid for sid, meta in source_blueprints.items()}
topic_rows = list(integrated) + local_speaking
topics = []
for row in topic_rows:
    sid = source_by_name.get(row["source_name"])
    if not sid:
        continue
    seed = "|".join([row["source_name"], row.get("period", ""), row.get("topic_number", ""), row.get("topic_title", "")])
    topics.append({"id": "topic_" + hashlib.sha1(seed.encode()).hexdigest()[:16], "title": row.get("topic_title") or "Untitled topic", "period": row.get("period", ""), "region": row.get("region") or "未标注", "partStructure": row.get("part_structure") or "未标注", "primaryTheme": row.get("primary_theme") or "other", "questionCount": int(row.get("question_count") or 0), "sourceId": sid, "sourceGroup": source_blueprints[sid]["sourceGroup"], "current": row.get("phase") != "upcoming_prediction" and "2026" in row.get("period", ""), "upcoming": row.get("phase") == "upcoming_prediction", "integrationQuality": row.get("integration_quality") or "source_theme_normalized", "sourceUrl": row.get("source_url") or ""})
topics = list({row["id"]: row for row in topics}.values())
topics.sort(key=lambda row: (not row["current"], row["upcoming"], row["period"], row["title"]))

theme_counts = Counter((row["primaryTheme"], row["current"], row["upcoming"]) for row in topics)
themes = []
for theme in sorted({row["primaryTheme"] for row in topics}):
    themes.append({"theme": theme, "overallCount": sum(value for (name, _current, _upcoming), value in theme_counts.items() if name == theme), "currentCount": sum(value for (name, current, _upcoming), value in theme_counts.items() if name == theme and current), "upcomingCount": sum(value for (name, _current, upcoming), value in theme_counts.items() if name == theme and upcoming)})
themes.sort(key=lambda row: (-row["overallCount"], row["theme"]))


def row_year(row: dict[str, str]) -> int | None:
    for value in (row.get("published_date", ""), row.get("year", ""), row.get("source_name", "")):
        match = re.search(r"20\d{2}", str(value))
        if match:
            return int(match.group())
    return None


def classify_task1(text: str) -> str:
    value = text.lower()
    if "map" in value or "plan" in value:
        return "map/plan"
    if "process" in value or "how" in value and ("produced" in value or "made" in value):
        return "process"
    types = []
    if "table" in value:
        types.append("table")
    if "pie" in value:
        types.append("pie/proportion")
    if "bar" in value:
        types.append("bar/column")
    if "graph" in value or "line chart" in value:
        types.append("line/trend")
    if len(types) > 1:
        return "mixed/multiple visuals"
    return types[0] if types else "diagram/system/other"


def classify_task2(text: str) -> str:
    value = text.lower()
    if "discuss both" in value or "discuss these" in value:
        return "discuss-both-views"
    if "advantage" in value or "disadvantage" in value or "outweigh" in value:
        return "advantages-disadvantages/outweigh"
    if "positive or negative" in value:
        return "positive-negative development"
    if "agree" in value or "to what extent" in value:
        return "agree-disagree/opinion"
    if "problem" in value or "cause" in value or "solution" in value:
        return "problem-solution/causes-effects"
    return "two-part/direct questions" if value.count("?") >= 2 else "agree-disagree/opinion"


def writing_theme(text: str) -> str:
    value = text.lower()
    rules = [
        ("education", r"school|student|teacher|education|university|learn"),
        ("children-family", r"child|parent|family|young people"),
        ("work-economy", r"work|job|employ|business|econom|income|salary"),
        ("government-public-policy", r"government|public|policy|tax|fund"),
        ("technology-media", r"technology|internet|media|computer|online|advertis"),
        ("environment-energy", r"environment|pollution|energy|climate|waste|animal"),
        ("transport-cities-housing", r"transport|traffic|city|cities|housing|home|building"),
        ("health-lifestyle", r"health|food|diet|sport|exercise|lifestyle"),
        ("globalization-travel", r"travel|touris|country|international|global"),
        ("arts-sports", r"art|music|sport|museum"),
        ("crime-law", r"crime|law|prison|police"),
        ("science-research-language", r"science|research|language"),
        ("society-culture", r"society|culture|tradition|community"),
    ]
    for label, pattern in rules:
        if re.search(pattern, value):
            return label
    return "other"


writing_rows = [row for row in classified if row.get("skill") == "Writing" and row.get("source_status") != "excluded_by_terms"]
for section in cambridge["sections"]:
    if section["skill"] != "Writing":
        continue
    task = f"Task {section['part']}"
    writing_rows.append({"part_or_task": task, "classification": classify_task1(section["text"]) if task == "Task 1" else classify_task2(section["text"]), "primary_theme": writing_theme(section["text"]), "source_name": f"Cambridge IELTS Academic {section['volume']}", "year": str(section["year"])})

writing_facets = []
for scope, scoped_rows in (("overall", writing_rows), ("recent_3y", [row for row in writing_rows if row_year(row) and row_year(row) >= 2024])):
    buckets = defaultdict(lambda: {"count": 0, "sources": set()})
    for row in scoped_rows:
        task = row.get("part_or_task") or "未标注"
        classification = row.get("classification") or row.get("task_type") or "other"
        theme = row.get("primary_theme") or "other"
        for facet_type, label in (("task_type", classification), ("theme", theme)):
            key = (facet_type, task, label)
            buckets[key]["count"] += 1
            buckets[key]["sources"].add(row.get("source_name") or "unknown")
    grouped = defaultdict(list)
    for (facet_type, task, label), values in buckets.items():
        grouped[(facet_type, task)].append((label, values))
    for (facet_type, task), items in grouped.items():
        items.sort(key=lambda item: (-item[1]["count"], item[0]))
        for rank, (label, values) in enumerate(items, 1):
            seed = "|".join([facet_type, scope, task, label])
            writing_facets.append({"id": "writing_" + hashlib.sha1(seed.encode()).hexdigest()[:16], "facetType": facet_type, "scope": scope, "task": task, "label": label, "count": values["count"], "sourceCount": len(values["sources"]), "rank": rank})

coverage = []
for skill in ("Listening", "Speaking", "Reading", "Writing"):
    skill_docs = [document for document in documents if document["skill"] == skill]
    coverage.append({"skill": skill, "documents": len(skill_docs), "filteredTokens": sum(len(document["tokens"]) for document in skill_docs), "sources": len({document["sourceId"] for document in skill_docs}), "sourceGroups": sorted({source_blueprints[str(document["sourceId"])]["sourceGroup"] for document in skill_docs})})

payload = {
    "meta": {
        "generatedAt": datetime.now(timezone.utc).isoformat(), "cutoff": "2026-08-25",
        "documentCount": len(documents), "filteredTokenCount": sum(len(document["tokens"]) for document in documents),
        "sourceCount": len(sources), "topicCount": len(topics),
        "copyrightPolicy": "Public site stores aggregate statistics, metadata, attributed question references and original study content. Full Cambridge passages, audio, images, answer keys and third-party model answers are excluded.",
        "method": "Conservative lowercase tokenization and plural normalization; function words, task instructions and common proper-name noise removed. Cambridge IELTS Academic 4-21 and every selected unit from the other declared sources enter the four-skill counts. Every lemma meeting the documented minimum document-frequency threshold is published without a top-N cap. Rankings expose occurrence count, document frequency, per-10k rate, source count and confidence.",
        "wordListPolicy": "all_qualifying_no_top_n_cap",
        "recentWindow": "2021-2026",
        "cambridgeVolumes": len(cambridge["volumes"]), "cambridgeSections": len(cambridge["sections"]),
        "localSpeakingSourceCount": len({row["source_name"] for row in local_speaking}),
        "localFailures": local_failures,
    },
    "coverage": coverage, "wordScopeCoverage": word_scope_coverage, "sources": sources, "words": word_rows,
    "topics": topics, "themes": themes, "writingFacets": writing_facets,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(json.dumps({"output": str(OUTPUT), "meta": payload["meta"], "coverage": coverage, "wordRows": len(word_rows), "writingFacets": len(writing_facets)}, ensure_ascii=False, indent=2))
