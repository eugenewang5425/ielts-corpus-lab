from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    manifest = load("manifest.json")
    corpus = load("corpus.json")
    speaking = load("speaking.json")
    questions = load("questions.json")
    writing = load("writing.json")
    chunks = load("chunks.json")

    topic_ids = [topic["id"] for topic in speaking["topics"]]
    assert len(topic_ids) == len(set(topic_ids)), "duplicate merged topic id"
    assert set(topic_ids) == set(questions["topics"]), "practice coverage does not match merged topics"

    source_question_ids: list[str] = []
    for topic in speaking["topics"]:
        assert topic["questions"], f"no source questions for {topic['id']}"
        assert topic["questionCount"] == len(topic["questions"])
        for question in topic["questions"]:
            source_question_ids.append(question["id"])
            assert question["part"] in {"Part 1", "Part 2", "Part 3"}
            assert question["text"].strip()
            assert question["sourceRefs"]
            assert all(ref in speaking["sources"] for ref in question["sourceRefs"])
    assert len(source_question_ids) == len(set(source_question_ids)), "duplicate source question id"
    assert speaking["meta"]["uniqueQuestionCount"] == len(source_question_ids)
    assert speaking["meta"]["currentQuestionCount"] > 2000
    assert speaking["meta"]["upcomingQuestionCount"] >= 70
    assert any(source.get("phase") == "upcoming_prediction" for source in speaking["sources"].values())

    question_ids: list[str] = []
    for topic_id in topic_ids:
        topic = questions["topics"][topic_id]
        assert topic["notOfficial"] is True
        assert topic["contentLabel"] == "本站原创练习"
        assert topic["questions"], f"no questions for {topic_id}"
        for question in topic["questions"]:
            question_ids.append(question["id"])
            assert question["part"] in {"Part 1", "Part 2", "Part 3"}
            assert question["question"].strip()
            assert len(question["ideasZh"]) >= 3
            assert question["templateEn"].strip()
            assert question["sampleAnswerEn"].strip()
            assert question["vocabulary"]

    assert len(question_ids) == len(set(question_ids)), "duplicate practice question id"

    writing_ids: list[str] = []
    for exercise in writing["exercises"]:
        writing_ids.append(exercise["id"])
        assert exercise["task"] in {"Task 1", "Task 2"}
        assert exercise["question"].strip()
        assert exercise["timeMinutes"] in {20, 40}
        assert exercise["minimumWords"] in {150, 250}
        assert len(exercise["plan"]) >= 4
        assert len(exercise["templateEn"]) >= 3
        assert len(exercise["vocabulary"]) >= 6
        assert len(exercise["modelAnswer"]) >= 4
        word_count = len(" ".join(exercise["modelAnswer"]).split())
        assert word_count >= exercise["minimumWords"], f"short writing model for {exercise['id']}"
        assert set(exercise["criterionNotes"]) == {"task", "coherence", "lexical", "grammar"}
        if exercise["task"] == "Task 1":
            assert exercise.get("visual"), f"missing Task 1 visual for {exercise['id']}"
        else:
            assert not exercise.get("visual"), f"unexpected Task 2 visual for {exercise['id']}"

    assert len(writing_ids) == len(set(writing_ids)), "duplicate writing exercise id"
    assert writing["meta"]["exerciseCount"] == len(writing_ids)
    assert writing["meta"]["task1Count"] == sum(item["task"] == "Task 1" for item in writing["exercises"])
    assert writing["meta"]["task2Count"] == sum(item["task"] == "Task 2" for item in writing["exercises"])
    chunk_ids: list[str] = []
    for chunk in chunks["chunks"]:
        chunk_ids.append(chunk["id"])
        assert chunk["skill"] in {"Reading", "Listening"}
        assert chunk["phrase"].strip()
        assert chunk["meaningZh"].strip()
        assert chunk["frame"].strip()
        assert chunk["usageZh"].strip()
        assert chunk["tier"] in {"core", "expansion"}
        if chunk["tier"] == "core":
            assert chunk["exampleEn"].strip()
            assert chunk["exampleZh"].strip()
            assert chunk["contentLabel"] == "本站原创例句"
        else:
            assert chunk["exampleEn"] == ""
            assert chunk["exampleZh"] == ""
            assert chunk["contentLabel"] in {"语料扩展索引", "语料自动发现"}
        assert chunk["occurrenceCount"] >= chunk["documentFrequency"] >= 1
        assert 0 < chunk["documentCoverage"] <= 1
        assert sum(chunk["sourceMix"].values()) == chunk["occurrenceCount"]
        assert chunk["sourceCount"] >= 1
        assert chunk["confidence"] in {"high", "medium", "exploratory"}
    assert len(chunk_ids) == len(set(chunk_ids)), "duplicate chunk id"
    assert chunks["meta"]["chunkCount"] >= 900
    assert sum(item.get("contentLabel") == "语料自动发现" for item in chunks["chunks"]) >= 500
    assert chunks["meta"]["chunkCount"] == len(chunk_ids)
    assert chunks["meta"]["coreChunkCount"] == sum(chunk["tier"] == "core" for chunk in chunks["chunks"])
    assert chunks["meta"]["expansionChunkCount"] == sum(chunk["tier"] == "expansion" for chunk in chunks["chunks"])
    assert {stat["skill"] for stat in chunks["skillStats"]} == {"Reading", "Listening"}
    assert sum(stat["chunkCount"] for stat in chunks["skillStats"]) == len(chunk_ids)
    coverage_by_skill = {row["skill"]: row for row in corpus["coverage"]}
    assert corpus["meta"]["cambridgeVolumes"] == 18
    assert corpus["meta"]["cambridgeSections"] >= 900
    assert corpus["meta"]["wordListPolicy"] == "all_qualifying_no_top_n_cap"
    assert chunks["meta"]["discoveryPolicy"] == "all_qualifying_no_top_n_cap"
    assert len(corpus["sources"]) == 32
    assert len({source["sourceGroup"] for source in corpus["sources"]}) == 8
    cambridge_numbers = sorted(
        int(match.group(1))
        for source in corpus["sources"]
        if source["sourceGroup"] == "cambridge_practice"
        if (match := re.search(r"Academic (\d+)", source["name"]))
    )
    assert cambridge_numbers == list(range(4, 22)), cambridge_numbers
    assert {"cambridge_practice", "local_question_bank"}.issubset({source["sourceGroup"] for source in corpus["sources"]})
    assert all("text" not in source and "tokens" not in source for source in corpus["sources"])
    word_keys = [(row["skill"], row["scope"], row["lemma"]) for row in corpus["words"]]
    assert len(word_keys) == len(set(word_keys)), "duplicate word statistic"
    word_groups = {}
    for row in corpus["words"]:
        word_groups.setdefault((row["skill"], row["scope"]), []).append(row)
        assert 1 <= len(row["topSkills"]) <= 2
        assert len(row["topSkills"]) == len(set(row["topSkills"]))
        assert set(row["topSkills"]).issubset({"Listening", "Speaking", "Reading", "Writing"})
    assert set(word_groups) == {
        (skill, scope)
        for skill in {"All", "Listening", "Speaking", "Reading", "Writing"}
        for scope in {"overall", "recent_5y"}
    }
    for rows in word_groups.values():
        rows.sort(key=lambda row: row["rank"])
        assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
    assert all(len(word_groups[(skill, "overall")]) > 750 for skill in {"All", "Listening", "Speaking", "Reading", "Writing"})
    scope_coverage_keys = {(row["skill"], row["scope"]) for row in corpus["wordScopeCoverage"]}
    assert scope_coverage_keys == set(word_groups)
    overall_scope = {row["skill"]: row for row in corpus["wordScopeCoverage"] if row["scope"] == "overall"}
    assert overall_scope["All"]["documents"] == corpus["meta"]["documentCount"]
    assert overall_scope["All"]["filteredTokens"] == corpus["meta"]["filteredTokenCount"]
    assert overall_scope["All"]["sources"] == corpus["meta"]["sourceCount"]
    for skill, coverage in coverage_by_skill.items():
        assert overall_scope[skill]["documents"] == coverage["documents"]
        assert overall_scope[skill]["filteredTokens"] == coverage["filteredTokens"]
        assert overall_scope[skill]["sources"] == coverage["sources"]
    for stat in chunks["skillStats"]:
        coverage = coverage_by_skill[stat["skill"]]
        assert stat["documents"] == coverage["documents"]
        assert stat["filteredTokenCount"] == coverage["filteredTokens"]
        assert stat["sourceCount"] == coverage["sources"]
        assert stat["sourceGroups"] == coverage["sourceGroups"]
        assert stat["coreChunkCount"] + stat["expansionChunkCount"] == stat["chunkCount"]
    assert manifest["counts"]["topics"] == len(topic_ids)
    assert manifest["counts"]["words"] == len(corpus["words"])
    assert manifest["counts"]["sourceQuestions"] == len(source_question_ids)
    assert manifest["counts"]["practiceQuestions"] == len(question_ids)
    assert manifest["counts"]["writingExercises"] == len(writing_ids)
    assert manifest["counts"]["chunks"] == len(chunk_ids)
    assert questions["meta"]["practiceQuestionCount"] == len(question_ids)
    assert manifest["files"] == {
        "corpus": "data/corpus.json",
        "speaking": "data/speaking.json",
        "questions": "data/questions.json",
        "writing": "data/writing.json",
        "chunks": "data/chunks.json",
    }
    print(
        f"Validated {len(topic_ids)} merged topics, {len(source_question_ids)} source questions "
        f"{len(question_ids)} speaking practice questions, {len(writing_ids)} writing exercises "
        f"and {len(chunk_ids)} Reading/Listening chunks."
    )


if __name__ == "__main__":
    main()
