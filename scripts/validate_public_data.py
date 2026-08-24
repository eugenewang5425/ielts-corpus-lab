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
    assert manifest["counts"]["topics"] == len(topic_ids)
    assert manifest["counts"]["sourceQuestions"] == len(source_question_ids)
    assert manifest["counts"]["practiceQuestions"] == len(question_ids)
    assert questions["meta"]["practiceQuestionCount"] == len(question_ids)
    assert manifest["files"] == {
        "corpus": "data/corpus.json",
        "speaking": "data/speaking.json",
        "questions": "data/questions.json",
    }
    print(
        f"Validated {len(topic_ids)} merged topics, {len(source_question_ids)} source questions "
        f"and {len(question_ids)} practice questions."
    )


if __name__ == "__main__":
    main()
