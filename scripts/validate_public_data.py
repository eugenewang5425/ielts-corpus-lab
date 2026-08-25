from __future__ import annotations

import json
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
        assert chunk["exampleEn"].strip()
        assert chunk["exampleZh"].strip()
        assert chunk["contentLabel"] == "本站原创例句"
        assert chunk["occurrenceCount"] >= chunk["documentFrequency"] >= 1
        assert 0 < chunk["documentCoverage"] <= 1
        assert sum(chunk["sourceMix"].values()) == chunk["occurrenceCount"]
        assert chunk["sourceCount"] >= 1
        assert chunk["confidence"] in {"high", "medium", "exploratory"}
    assert len(chunk_ids) == len(set(chunk_ids)), "duplicate chunk id"
    assert chunks["meta"]["chunkCount"] == len(chunk_ids)
    assert {stat["skill"] for stat in chunks["skillStats"]} == {"Reading", "Listening"}
    assert sum(stat["chunkCount"] for stat in chunks["skillStats"]) == len(chunk_ids)
    coverage_by_skill = {row["skill"]: row for row in corpus["coverage"]}
    for stat in chunks["skillStats"]:
        coverage = coverage_by_skill[stat["skill"]]
        assert stat["documents"] == coverage["documents"]
        assert stat["filteredTokenCount"] == coverage["filteredTokens"]
        assert stat["sourceCount"] == coverage["sources"]
        assert stat["sourceGroups"] == coverage["sourceGroups"]
    assert manifest["counts"]["topics"] == len(topic_ids)
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
