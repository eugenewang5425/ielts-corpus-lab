from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


THEMES = {
    "person/family/friends": {
        "zh": "人物、家庭与朋友",
        "scene": "a conversation with someone close to me",
        "value": "support, trust and a sense of belonging",
        "future": "people may rely more on technology to stay connected, while still valuing face-to-face time",
        "vocab": [("supportive", "给予支持的"), ("bond", "情感纽带"), ("reliable", "可靠的"), ("keep in touch", "保持联系")],
    },
    "object/technology": {
        "zh": "物品与科技",
        "scene": "using a useful digital tool during a busy week",
        "value": "convenience, efficiency and easier access to information",
        "future": "devices will become more personalised and more closely integrated into everyday routines",
        "vocab": [("user-friendly", "容易使用的"), ("efficient", "高效的"), ("feature", "功能"), ("rely on", "依赖")],
    },
    "travel-transport": {
        "zh": "旅行与交通",
        "scene": "a short journey that turned out to be more memorable than expected",
        "value": "mobility, independence and exposure to different places",
        "future": "cleaner vehicles and smarter public transport may make journeys more sustainable",
        "vocab": [("commute", "通勤"), ("convenient", "方便的"), ("scenic", "风景优美的"), ("get around", "出行")],
    },
    "place": {
        "zh": "地点与空间",
        "scene": "visiting a place whose atmosphere immediately caught my attention",
        "value": "comfort, identity and memorable experiences",
        "future": "public spaces may become greener, more accessible and better connected",
        "vocab": [("atmosphere", "氛围"), ("spacious", "宽敞的"), ("accessible", "便利可达的"), ("stand out", "显得突出")],
    },
    "home/hometown/accommodation": {
        "zh": "家、家乡与居住",
        "scene": "noticing a small change in the neighbourhood where I live",
        "value": "security, familiarity and a sense of identity",
        "future": "homes may become smaller, smarter and more energy-efficient",
        "vocab": [("neighbourhood", "社区"), ("cosy", "舒适温馨的"), ("familiar", "熟悉的"), ("settle down", "定居")],
    },
    "event/experience": {
        "zh": "事件与经历",
        "scene": "an unexpected experience that taught me something practical",
        "value": "personal growth, shared memories and lessons that are difficult to learn from books",
        "future": "people may look for more personalised and immersive experiences",
        "vocab": [("memorable", "难忘的"), ("unexpected", "意外的"), ("turning point", "转折点"), ("learn from", "从中学习")],
    },
    "food": {
        "zh": "食物与饮食",
        "scene": "sharing a simple meal with friends or family",
        "value": "health, cultural identity and social connection",
        "future": "people may pay more attention to nutrition, sustainability and food safety",
        "vocab": [("nutritious", "有营养的"), ("flavour", "风味"), ("homemade", "自制的"), ("balanced diet", "均衡饮食")],
    },
    "activity/hobby": {
        "zh": "活动与爱好",
        "scene": "making time for an activity after a demanding day",
        "value": "relaxation, skill development and a healthier balance in life",
        "future": "online communities may make hobbies easier to learn and share",
        "vocab": [("rewarding", "有收获的"), ("unwind", "放松"), ("take up", "开始从事"), ("stick with", "坚持")],
    },
    "society-government": {
        "zh": "社会与公共事务",
        "scene": "discussing a local issue with classmates or colleagues",
        "value": "fairness, public trust and the effective use of shared resources",
        "future": "citizens may expect greater transparency and more digital public services",
        "vocab": [("public awareness", "公众意识"), ("policy", "政策"), ("fair access", "公平获取"), ("long-term impact", "长期影响")],
    },
    "work-study": {
        "zh": "学习与工作",
        "scene": "completing a difficult task with help from a teacher or colleague",
        "value": "knowledge, independence and better future opportunities",
        "future": "flexible learning and artificial intelligence may change how people study and work",
        "vocab": [("productive", "富有成效的"), ("workload", "工作量"), ("practical skill", "实用技能"), ("meet a deadline", "按时完成")],
    },
    "culture": {
        "zh": "文化与传统",
        "scene": "taking part in a local tradition with people from different generations",
        "value": "identity, shared history and understanding between generations",
        "future": "traditions may be presented in more modern forms while keeping their core meaning",
        "vocab": [("heritage", "文化遗产"), ("tradition", "传统"), ("pass down", "传承"), ("cultural identity", "文化认同")],
    },
    "other": {
        "zh": "日常生活与综合话题",
        "scene": "a small everyday situation that made me reconsider my usual habits",
        "value": "practical choices, personal preferences and everyday well-being",
        "future": "people's choices may become more personalised and influenced by technology",
        "vocab": [("practical", "实用的"), ("preference", "偏好"), ("routine", "日常习惯"), ("make a difference", "产生影响")],
    },
}

THEME_EN = {
    "person/family/friends": "people, family and friendship",
    "object/technology": "objects and technology",
    "travel-transport": "travel and transport",
    "place": "places and public spaces",
    "home/hometown/accommodation": "homes, hometowns and accommodation",
    "event/experience": "events and personal experiences",
    "food": "food and eating habits",
    "activity/hobby": "activities and hobbies",
    "society-government": "society and public affairs",
    "work-study": "work and education",
    "culture": "culture and traditions",
    "other": "everyday life",
}


def answer_item(part: str, index: int, title: str, theme: dict[str, object]) -> dict[str, object]:
    topic = f'“{title}”'
    vocab = [{"word": word, "meaningZh": meaning} for word, meaning in theme["vocab"]]
    if part == "Part 1" and index == 1:
        return {
            "part": part,
            "question": f"When you hear the topic {topic}, what is the first thing that comes to mind?",
            "ideasZh": ["第一句直接给出人、物或经历", "补充时间和场景", "用 because 解释它为何突出"],
            "templateEn": "The first thing that comes to mind is ___. I first noticed it when ___. What stands out most is ___, mainly because ___.",
            "sampleAnswerEn": f"The first thing that comes to mind is {theme['scene']}. It was an ordinary moment, but it relates closely to {topic}. What stood out most was how personal the experience felt. I remember it clearly because it gave me a more concrete understanding of {theme['en']} and made the topic much easier to talk about.",
            "vocabulary": vocab[:3],
        }
    if part == "Part 1" and index == 2:
        return {
            "part": part,
            "question": f"Is {topic} important or common in your daily life?",
            "ideasZh": ["先回答程度：very / fairly / not particularly", "给一个最近的具体例子", "用一句结果或感受收尾"],
            "templateEn": "It is fairly ___ in my daily life. For instance, ___. As a result, it helps me / makes me feel ___.",
            "sampleAnswerEn": f"It is fairly relevant to my daily life, although I do not think about it all the time. For instance, I recently had {theme['scene']}. That experience reminded me that this topic can influence ordinary decisions. Overall, I value it because it can bring {theme['value']}.",
            "vocabulary": vocab[:3],
        }
    if part == "Part 1":
        return {
            "part": part,
            "question": f"Has your opinion about {topic} changed over time?",
            "ideasZh": ["用 used to 交代过去的看法", "说明改变看法的具体经历", "用 now / these days 给出当前观点"],
            "templateEn": "I used to think ___. My view changed when ___. These days, I tend to ___ because ___.",
            "sampleAnswerEn": f"Yes, it has changed to some extent. I used to see the topic as something quite ordinary and I rarely paid attention to it. My view changed after {theme['scene']}. That experience helped me notice its practical side and the effect it can have on daily choices. These days, I think about it more carefully because it can bring {theme['value']}.",
            "vocabulary": vocab[:3],
        }
    if part == "Part 2":
        return {
            "part": part,
            "question": f"Describe an experience connected with {topic} that you remember clearly. You should say: when and where it happened; who was involved; what happened; and explain why you remember it.",
            "ideasZh": ["背景：时间、地点、人物各一句", "经过：按 before–during–after 讲三步", "细节：加入一个可见、可听或可感的细节", "意义：说明改变、感受或学到什么"],
            "templateEn": "I’d like to talk about ___. It happened when ___. At first, ___. What happened next was ___. The detail I remember most is ___. Looking back, it mattered to me because ___.",
            "sampleAnswerEn": f"I’d like to talk about {theme['scene']}, which is the experience I connect most strongly with {topic}. It happened last year on a fairly ordinary day, and one other person was involved. At first, I did not expect anything special, but a small detail changed the whole experience. I had to make a quick decision, explain what I thought and then deal with the result. The detail I remember most is the relaxed conversation afterwards. Looking back, it mattered because it showed me the value of {theme['value']}. It also gave me a real story rather than an abstract opinion, so I can still describe the moment clearly today.",
            "vocabulary": vocab,
        }
    if part == "Part 3" and index == 1:
        return {
            "part": part,
            "question": f"Why does the broader theme of {theme['en']} matter to people today?",
            "ideasZh": ["先给核心原因，不要只说 important", "从个人影响扩展到社会影响", "承认一个限制或代价", "用 therefore 总结"],
            "templateEn": "I think it matters mainly because ___. On an individual level, ___. From a wider perspective, ___. Admittedly, ___. Even so, ___.",
            "sampleAnswerEn": f"I think it matters mainly because it can provide {theme['value']}. On an individual level, it affects the choices people make and the way they organise daily life. From a wider perspective, it can shape how communities use time, money and public resources. Admittedly, not everyone benefits in the same way, and access can be unequal. Even so, the topic deserves attention because small individual decisions can create a noticeable long-term impact.",
            "vocabulary": vocab,
        }
    if part == "Part 3" and index == 2:
        return {
            "part": part,
            "question": f"How might {theme['en']} change in the next ten years?",
            "ideasZh": ["提出一个最可能的变化", "解释推动因素：科技、成本、政策或观念", "比较受益者与可能被落下的人", "避免绝对预测，用 may / likely to"],
            "templateEn": "Over the next decade, I expect ___. The main driver will probably be ___. This could benefit ___, although ___. So the change is likely to be ___ rather than ___.",
            "sampleAnswerEn": f"Over the next decade, I expect that {theme['future']}. The main driver will probably be a mixture of technology, changing expectations and cost. This could benefit people who are willing and able to adapt, although others may need extra support. So the change is likely to be gradual rather than immediate. The basic human need behind the topic will remain, but the way people respond to it may look quite different.",
            "vocabulary": vocab,
        }
    return {
        "part": part,
        "question": f"Do different generations think differently about {topic}?",
        "ideasZh": ["明确比较对象：younger / older people", "各给一个原因，避免刻板印象", "指出共同点或例外", "以平衡判断收尾"],
        "templateEn": "There is a difference, but it is not absolute. Younger people tend to ___ because ___. Older people may prefer ___ since ___. However, both groups ___.",
        "sampleAnswerEn": "There is a difference, but it is not absolute. Younger people are often quicker to accept new ways of doing things because they encounter them through school, work and social media. Older people may place more value on familiarity and proven experience. However, both groups usually care about convenience, security and meaningful results. In my view, personality and circumstances can be just as influential as age, so it is better to avoid a simple stereotype.",
        "vocabulary": vocab,
    }


def build_topic(topic: dict[str, object]) -> dict[str, object]:
    title = str(topic["title"])
    theme_key = str(topic.get("primaryTheme"))
    profile = dict(THEMES.get(theme_key, THEMES["other"]))
    profile["en"] = THEME_EN.get(theme_key, THEME_EN["other"])
    structure = str(topic.get("partStructure") or "")
    items: list[dict[str, object]] = []
    if "Part 1" in structure:
        items.extend(answer_item("Part 1", index, title, profile) for index in (1, 2, 3))
    if "Part 2" in structure:
        items.append(answer_item("Part 2", 1, title, profile))
    if "Part 3" in structure:
        items.extend(answer_item("Part 3", index, title, profile) for index in (1, 2, 3))
    if not items:
        items.extend(answer_item("Part 1", index, title, profile) for index in (1, 2, 3))
        items.append(answer_item("Part 2", 1, title, profile))
    for index, item in enumerate(items, start=1):
        item["id"] = f"{topic['id']}_q{index}"
    return {
        "topicId": topic["id"],
        "topicTitle": title,
        "primaryTheme": topic.get("primaryTheme", "other"),
        "contentLabel": "本站原创练习",
        "notOfficial": True,
        "questions": items,
    }


def main() -> None:
    corpus_path = DATA_DIR / "corpus.json"
    speaking_path = DATA_DIR / "speaking.json"
    writing_path = DATA_DIR / "writing.json"
    chunks_path = DATA_DIR / "chunks.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    speaking = json.loads(speaking_path.read_text(encoding="utf-8"))
    writing = json.loads(writing_path.read_text(encoding="utf-8"))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    generated_at = datetime.now(timezone.utc).isoformat()
    topics = {topic["id"]: build_topic(topic) for topic in speaking["topics"]}
    question_count = sum(len(topic["questions"]) for topic in topics.values())
    question_bank = {
        "meta": {
            "schemaVersion": 1,
            "generatedAt": generated_at,
            "sourceCorpusGeneratedAt": corpus["meta"]["generatedAt"],
            "topicCount": len(topics),
            "practiceQuestionCount": question_count,
            "contentPolicy": "Original practice questions, answer plans, reusable templates and sample answers. They are not official IELTS questions and do not reproduce proprietary question banks.",
        },
        "topics": topics,
    }
    (DATA_DIR / "questions.json").write_text(
        json.dumps(question_bank, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    version = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    manifest = {
        "schemaVersion": 4,
        "dataVersion": version,
        "generatedAt": generated_at,
        "files": {"corpus": "data/corpus.json", "speaking": "data/speaking.json", "questions": "data/questions.json", "writing": "data/writing.json", "chunks": "data/chunks.json"},
        "counts": {
            "documents": corpus["meta"]["documentCount"],
            "words": len(corpus["words"]),
            "topics": len(topics),
            "sourceQuestions": speaking["meta"]["uniqueQuestionCount"],
            "sourceQuestionOccurrences": speaking["meta"]["sourceQuestionOccurrences"],
            "practiceQuestions": question_count,
            "writingExercises": writing["meta"]["exerciseCount"],
            "chunks": chunks["meta"]["chunkCount"],
        },
        "repository": "https://github.com/eugenewang5425/ielts-corpus-lab",
        "updateModel": "Versioned public JSON snapshot on GitHub Pages. The client fetches the manifest without cache and then loads matching data files.",
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(topics)} topics and {question_count} practice questions ({version}).")


if __name__ == "__main__":
    main()
