from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from lr_chunk_catalog import CATEGORY_TIPS, LISTENING_EXPANSION, READING_EXPANSION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT.parent / "雅思语料研究" / "outputs" / "data" / "corpus_dedup.csv"
DEFAULT_MATERIALS = ROOT.parent / "资料"
CAMBRIDGE_CACHE = ROOT.parent / "outputs" / "ielts-corpus-build" / "cambridge_sections.json"

AUTO_EDGE = set("a an the and or but if than then of in on at to from for with by as is are was were be been being do does did have has had this that these those it its i me my mine you your yours we us our ours he him his she her hers they them their theirs there here what which who how why when where can could may might should would will not no yes about into over under between during after before more most some any each every other another also very just all both only own same too out up down again further once while because however although though well right now really okay please good quite lot something thing things one two three let's i'd i'm i've i'll you'd you're you've you'll we'd we're we've we'll they'd they're they've they'll don't doesn't didn't can't couldn't won't wouldn't shouldn't isn't aren't wasn't weren't that's it's what's there's here's".split())
AUTO_NOISE = set("ielts test tests academic general reading listening writing speaking question questions answer answers task tasks section sections part parts passage passages page pages recording transcript candidate candidates examiner choose correct letter letters complete following below write read hear listen word words true false given match matching option options label diagram table note summary sentence instructions i ii iii iv v vi vii viii ix x zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred hundreds thousand thousands million millions billion billions".split())
AUTO_INTERIOR_NOISE = set("i me my mine you your yours we us our ours he him his she her hers they them their theirs i'd i'm i've i'll you'd you're you've you'll we'd we're we've we'll they'd they're they've they'll don't doesn't didn't can't couldn't won't wouldn't shouldn't isn't aren't wasn't weren't that's it's what's there's here's don".split())
BROKEN_BIGRAM_FIRST = {"need", "going", "let", "like", "time", "number", "take", "plenty", "wanted", "tell", "don", "able"}
COMMON_VERBS_OR_GAPS = {"get", "go", "talk", "know", "take", "look", "tell", "make", "use", "see", "give", "find", "think", "say", "ask", "help", "work", "study", "different", "bring", "bit", "start", "time"}
READING_NOISE = set("box boxes sheet spend minute minutes statement statements agree agrees contradict contradicts claims writer paragraph paragraphs heading headings list lists information impossible say says use using which your you his her she he their they our we one two three four five six seven eight nine ten".split())
LISTENING_NOISE = set("woman man speaker narrator section test recording".split())


READING = [
    ("based on", "关系与论证", "基于；以……为依据", "be based on + evidence/data", "说明结论、分类或判断所依据的证据。", "The recommendation is based on evidence from several long-term studies.", "这项建议以多项长期研究的证据为依据。"),
    ("because of", "关系与论证", "因为；由于", "because of + noun phrase", "后接名词短语，不能直接接完整句子。", "The species declined because of rapid habitat loss.", "该物种因栖息地迅速减少而衰退。"),
    ("similar to", "关系与论证", "与……相似", "be similar to + noun", "用于定位比较对象和共同特征。", "The new material is similar to natural bone in structure.", "这种新材料在结构上与天然骨骼相似。"),
    ("compared to", "关系与论证", "与……相比", "compared to + comparison group", "常把基准组放在句首或句末。", "Compared to adults, younger learners adapted more quickly.", "与成年人相比，年轻学习者适应得更快。"),
    ("rather than", "关系与论证", "而不是", "A rather than B", "突出作者选择的解释、方法或对象。", "The change reflects social pressure rather than biological need.", "这种变化反映的是社会压力，而非生理需求。"),
    ("result in", "关系与论证", "导致", "cause + result in + outcome", "主语是原因，后面接结果。", "Poor ventilation can result in a sharp rise in indoor pollution.", "通风不良会导致室内污染大幅上升。"),
    ("led to", "关系与论证", "导致；促成", "event + led to + consequence", "用于过去发生的因果链。", "The discovery led to a new method of treatment.", "这一发现促成了一种新的治疗方法。"),
    ("as a result of", "关系与论证", "由于……的结果", "as a result of + cause", "把原因放在词块之后，常用于长句衔接。", "As a result of repeated flooding, the settlement was moved inland.", "由于反复洪水，该聚落被迁往内陆。"),
    ("found that", "研究与证据", "发现……", "researchers found that + clause", "快速识别研究结果句，that 后通常是核心发现。", "Researchers found that regular breaks improved recall.", "研究人员发现定期休息能改善记忆。"),
    ("suggest that", "研究与证据", "表明；暗示……", "evidence suggests that + clause", "语气弱于 prove，表示证据支持而非绝对证明。", "The results suggest that sleep affects decision-making.", "结果表明睡眠会影响决策。"),
    ("shows that", "研究与证据", "显示；说明……", "the data shows that + clause", "用于引出图表、实验或观察支持的结论。", "The survey shows that cost remains the main barrier.", "调查显示成本仍是主要障碍。"),
    ("according to", "研究与证据", "根据；按照", "according to + source", "标出观点或数据的来源，而非作者本人的断言。", "According to the report, demand has doubled since 2010.", "根据该报告，需求自 2010 年以来翻了一番。"),
    ("known as", "研究与证据", "被称为", "be known as + name/term", "常用于术语定义、别名和历史称谓。", "This stage is known as the consolidation period.", "这一阶段被称为巩固期。"),
    ("research into", "研究与证据", "对……的研究", "research into + topic", "into 后接研究对象或问题。", "Research into migration patterns has challenged the earlier theory.", "对迁徙模式的研究挑战了早期理论。"),
    ("found in", "研究与证据", "存在于；在……中发现", "be found in + place/group", "用于描述分布、位置或样本中的发现。", "The compound is found in several coastal plants.", "这种化合物存在于几种海岸植物中。"),
    ("closely related", "研究与证据", "密切相关", "be closely related to + factor", "表示相关关系，不自动等于因果关系。", "Language use is closely related to social identity.", "语言使用与社会身份密切相关。"),
    ("number of", "范围与数量", "……的数量；若干", "the/a number of + plural noun", "the number of 强调数量；a number of 表示若干。", "The number of recorded species increased after the survey.", "调查后记录到的物种数量增加了。"),
    ("range of", "范围与数量", "一系列；范围", "a wide/broad range of + plural noun", "用于概括多个类别、速度或方法。", "The device can operate across a wide range of temperatures.", "该设备可在很宽的温度范围内运行。"),
    ("amount of", "范围与数量", "……的量", "the amount of + uncountable noun", "后接不可数名词，如 water、energy、evidence。", "The amount of energy required falls as efficiency improves.", "随着效率提高，所需能量会减少。"),
    ("result of", "范围与数量", "……的结果", "the result of + cause/process", "把观察到的现象连接到其来源或过程。", "The pattern may be the result of seasonal migration.", "这种模式可能是季节性迁徙的结果。"),
    ("attached to", "结构与过程", "附着于；连接到", "be attached to + object", "阅读结构说明和生物描写中的高价值定位词块。", "A lightweight sensor is attached to the outer shell.", "一个轻型传感器连接在外壳上。"),
    ("used in", "结构与过程", "用于……；在……中使用", "be used in + field/process", "用于识别工具、材料与应用领域。", "The technique is used in both medicine and archaeology.", "该技术用于医学和考古学。"),
    ("use of", "结构与过程", "……的使用", "the use of + method/material", "名词化表达，常承载段落主题。", "The use of recycled glass reduced production costs.", "使用再生玻璃降低了生产成本。"),
    ("development of", "结构与过程", "……的发展；形成", "the development of + system/idea", "可能表示历史发展，也可能表示生物或技术形成过程。", "The development of railways changed the regional economy.", "铁路的发展改变了区域经济。"),
    ("able to", "结构与过程", "能够……", "be able to + verb", "关注主语具备的能力、条件或最终结果。", "The insects are able to survive long periods without water.", "这些昆虫能够在长期缺水的情况下存活。"),
    ("likely to", "结构与过程", "可能会；很可能", "be likely to + verb", "表示概率判断，不等同于确定发生。", "Older structures are more likely to fail under repeated stress.", "较旧的结构在反复受力下更可能失效。"),
]


LISTENING = [
    ("can i help you", "互动与澄清", "我能帮您吗", "Can I help you + ?", "服务场景常见开场，提示接下来会提出需求。", "Can I help you with the booking today?", "今天的预订需要我帮忙吗？"),
    ("would you like", "互动与澄清", "您想要……吗", "Would you like + noun/to do", "礼貌提供选项，答案常紧跟其后。", "Would you like a single room or a double room?", "您想要单人间还是双人间？"),
    ("can you tell me", "互动与澄清", "你能告诉我……吗", "Can you tell me + detail", "后面通常出现姓名、地址、时间或偏好等关键信息。", "Can you tell me which date you prefer?", "你能告诉我你更喜欢哪个日期吗？"),
    ("could you explain", "互动与澄清", "你能解释一下吗", "Could you explain + noun/clause", "提示说话人将改述或补充细节。", "Could you explain what the basic package includes?", "你能解释一下基础套餐包含什么吗？"),
    ("make sure", "互动与澄清", "确认；确保", "make sure + clause", "提示说话人正在核对条件、时间或必要步骤。", "Please make sure the form includes your reference number.", "请确认表格中包含你的参考编号。"),
    ("i'd like to", "互动与澄清", "我想要……", "I'd like to + verb", "比 I want to 更礼貌，常用于预订、咨询和报名。", "I'd like to reserve a place on the afternoon tour.", "我想预订下午参观的一个名额。"),
    ("a bit about", "互动与澄清", "一点关于……的信息", "tell/ask + a bit about + topic", "提示后面将展开主题背景或服务说明。", "Let me tell you a bit about the training programme.", "让我简单介绍一下培训项目。"),
    ("first of all", "互动与澄清", "首先", "First of all, + first step", "结构路标，预示流程或清单的第一项。", "First of all, please check the reference number.", "首先，请核对参考编号。"),
    ("deal with", "安排与流程", "处理；应对", "deal with + issue/request", "常用于职责、问题和服务流程说明。", "The accommodation office will deal with urgent repairs.", "住宿办公室会处理紧急维修。"),
    ("responsible for", "安排与流程", "负责……", "be responsible for + noun/-ing", "识别人物、部门或设施的职责分工。", "The course tutor is responsible for marking the final project.", "课程导师负责批改期末项目。"),
    ("apply for", "安排与流程", "申请……", "apply for + course/job/funding", "后面通常是申请对象，注意与 apply to 的区别。", "Students can apply for travel funding in September.", "学生可以在九月申请旅行资助。"),
    ("in advance", "安排与流程", "提前", "book/pay + in advance", "与预订、付款和通知期限高频搭配。", "Group visits must be booked at least a week in advance.", "团体参观必须至少提前一周预订。"),
    ("due to", "安排与流程", "由于", "due to + noun phrase", "常用于解释变更、延误或取消的原因。", "The afternoon session was cancelled due to low demand.", "下午场因需求不足而取消。"),
    ("as well as", "安排与流程", "以及；除……之外还", "A as well as B", "表示附加信息，主信息通常位于词块前。", "The centre provides study rooms as well as computer access.", "该中心除提供电脑使用外，还提供自习室。"),
    ("take place", "安排与流程", "举行；发生", "event + take place + time/place", "活动安排题中，时间或地点常紧随其后。", "The induction session will take place in the main hall.", "入门说明会将在主大厅举行。"),
    ("located in", "安排与流程", "位于……", "be located in + area/building", "地点说明中定位设施所在区域。", "The language lab is located in the west wing.", "语言实验室位于西翼。"),
    ("a variety of", "安排与流程", "多种；各种", "a variety of + plural noun", "预示后面会列举多个服务、课程或设施。", "The club offers a variety of weekend activities.", "俱乐部提供多种周末活动。"),
    ("focus on", "安排与流程", "重点关注", "focus on + topic/task", "课程、讲座和研究介绍中的主题定位词块。", "The second lecture will focus on urban transport.", "第二场讲座将重点讨论城市交通。"),
    ("interested in", "意向与选择", "对……感兴趣", "be interested in + noun/-ing", "用于筛选活动、地点、课程或服务偏好。", "Are you interested in joining the photography workshop?", "你有兴趣参加摄影工作坊吗？"),
    ("hoping to", "意向与选择", "希望做……", "be hoping to + verb", "表示计划但尚未最终确定。", "We're hoping to open the new study area in June.", "我们希望六月开放新的学习区。"),
    ("i'd rather", "意向与选择", "我宁愿……", "I'd rather + verb", "强烈提示前一个选项被否定、后一个选项被选择。", "I'd rather travel in the morning if possible.", "如果可以，我宁愿早上出发。"),
    ("go for", "意向与选择", "选择", "go for + option", "口语中常表示在几个方案中作出选择。", "I'll go for the standard membership this time.", "这次我选择标准会员。"),
    ("depends on", "意向与选择", "取决于", "depend on + factor", "提示答案受条件限制，注意后面的决定因素。", "The final price depends on the size of the group.", "最终价格取决于团体人数。"),
    ("next week", "时间与方位", "下周", "by/until/next week", "结合介词辨别是截止时间还是发生时间。", "The new timetable will be available next week.", "新时间表将在下周公布。"),
    ("at home", "时间与方位", "在家", "study/work/use + at home", "常与现场、学校或办公室形成地点对比。", "You can complete the online module at home.", "你可以在家完成在线模块。"),
    ("next to", "时间与方位", "紧挨着", "A is next to B", "地图题核心相邻关系，比 near 更精确。", "The information desk is next to the main entrance.", "服务台紧挨着主入口。"),
    ("on your right", "时间与方位", "在你的右侧", "on your right as you + move", "注意移动方向改变后左右关系也会改变。", "The café is on your right as you enter the hall.", "进入大厅时，咖啡馆在你的右侧。"),
    ("on your left", "时间与方位", "在你的左侧", "on your left as you + move", "地图题中常与 entrance、turn、go past 连用。", "The lockers are on your left after the stairs.", "经过楼梯后，储物柜在你的左侧。"),
    ("next door to", "时间与方位", "就在……隔壁", "be next door to + place", "表示直接相邻的房间或建筑。", "The seminar room is next door to the library.", "研讨室就在图书馆隔壁。"),
    ("straight on", "时间与方位", "一直向前", "go/carry straight on", "地图题的移动指令，听到后保持原方向。", "Go straight on until you reach the courtyard.", "一直向前走，直到到达庭院。"),
    ("opposite this", "时间与方位", "在它对面", "opposite this/that + landmark", "this 指代刚提到的地标，要及时在图上定位。", "The ticket office is opposite this building.", "售票处在这栋楼对面。"),
    ("get involved in", "学习与活动", "参与……", "get involved in + activity", "常出现在社团、志愿活动和社区场景。", "Students can get involved in several local projects.", "学生可以参与多个本地项目。"),
    ("get used to", "学习与活动", "习惯于……", "get used to + noun/-ing", "描述适应过程，to 后接名词或动名词。", "It took her a month to get used to studying alone.", "她花了一个月才习惯独自学习。"),
    ("time management", "学习与活动", "时间管理", "time-management + skills", "课程咨询和学习体验中的常见能力词块。", "The course helped him improve his time-management skills.", "这门课帮助他提高了时间管理能力。"),
    ("sign up for", "学习与活动", "报名参加", "sign up for + course/event", "提示课程或活动的最终选择。", "You can sign up for the workshop at reception.", "你可以在前台报名参加工作坊。"),
    ("made up of", "学习与活动", "由……组成", "be made up of + components", "听结构说明时用于预测后续列举。", "The programme is made up of four short modules.", "该项目由四个短模块组成。"),
    ("public library", "服务与设施", "公共图书馆", "the public library", "地点题和设施清单中的高辨识度名词词块。", "The public library also provides free computer access.", "公共图书馆还提供免费电脑使用服务。"),
    ("pay by", "服务与设施", "用……支付", "pay by + card/cheque", "付款方式题中关注 by 后面的名词。", "You can pay by card when you collect the pass.", "领取通行证时可以刷卡付款。"),
]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower().replace("’", "'"))


def count_phrase(tokens: list[str], phrase: str) -> int:
    needle = tokenize(phrase)
    return sum(tokens[index:index + len(needle)] == needle for index in range(len(tokens) - len(needle) + 1))


def confidence(document_frequency: int, source_count: int, document_count: int) -> str:
    if document_frequency >= max(4, round(document_count * 0.12)) and source_count >= 2:
        return "high"
    if document_frequency >= 3:
        return "medium"
    return "exploratory"


def clean_text(text: str) -> str:
    text = str(text or "").replace("’", "'").replace("“", " ").replace("”", " ")
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str) -> str:
    normalized = re.sub(r"[^a-z]+", "", clean_text(text).lower())
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return clean_text(" ".join(page.extract_text() or "" for page in reader.pages))


def collect_documents(corpus_path: Path, materials_path: Path) -> list[dict]:
    with corpus_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("skill") in {"Reading", "Listening"}]

    documents = [{
        "id": row["record_id"],
        "skill": row["skill"],
        "sourceName": row["source_name"],
        "sourceGroup": "official_public",
        "text": clean_text(row["question_text"]),
    } for row in rows]

    specs = []
    for path in materials_path.rglob("*.pdf"):
        name = path.name
        if "剑" in name and "同义词" in name:
            specs.append((path, "Listening", "cambridge_derived", "剑桥雅思 C4-C16 同义替换资料（本地派生）"))
        elif "阅读试题" in name:
            specs.append((path, "Reading", "third_party_prediction", "本地 2025-2026 阅读预测试题（去重）"))
        elif "听力文本" in name or "听力原文" in name:
            specs.append((path, "Listening", "third_party_prediction", "本地 2025-2026 听力文本（去重）"))

    seen_local = set()
    for path, skill, source_group, source_name in specs:
        try:
            text = extract_pdf(path)
        except Exception as exc:
            print(f"Skipped unreadable PDF {path.name}: {str(exc)[:120]}")
            continue
        if len(text) < 100:
            continue
        digest = content_hash(text)
        dedup_key = (skill, source_group, digest)
        if dedup_key in seen_local:
            continue
        seen_local.add(dedup_key)
        documents.append({
            "id": f"local-{digest[:18]}",
            "skill": skill,
            "sourceName": source_name,
            "sourceGroup": source_group,
            "text": text,
        })
    cambridge = json.loads(CAMBRIDGE_CACHE.read_text(encoding="utf-8"))
    for section in cambridge["sections"]:
        if section["skill"] not in {"Reading", "Listening"}:
            continue
        documents.append({
            "id": section["id"],
            "skill": section["skill"],
            "sourceName": f"Cambridge IELTS Academic {section['volume']}",
            "sourceGroup": "cambridge_practice",
            "text": clean_text(section["text"]),
        })
    return documents


def auto_category(skill: str, phrase: str) -> str:
    value = phrase.lower()
    if skill == "Reading":
        if re.search(r"research|study|evidence|result|analysis|data|survey|experiment", value):
            return "研究与分析"
        if re.search(r"number|amount|rate|percent|increase|decrease|level|majority", value):
            return "数量与变化"
        if re.search(r"environment|species|animal|plant|climate|energy|water|forest", value):
            return "环境与科学"
        if re.search(r"people|society|social|public|government|community|economic", value):
            return "社会与发展"
        return "逻辑与衔接"
    if re.search(r"thank|please|sorry|help|tell|ask|think|mean", value):
        return "互动与回应"
    if re.search(r"day|week|month|year|morning|afternoon|evening|minute|hour", value):
        return "时间与安排"
    if re.search(r"left|right|north|south|road|street|entrance|floor|corner", value):
        return "地点与方位"
    if re.search(r"name|address|number|phone|email|form|cost|price|book|ticket", value):
        return "手续与信息"
    if re.search(r"student|course|teacher|school|college|university|class|project", value):
        return "学习与工作"
    if re.search(r"room|centre|center|office|library|building|park|shop|hotel", value):
        return "设施与场景"
    return "功能与动作"


def discover_chunks(skill: str, documents: list[dict], excluded: set[str]) -> list[dict]:
    occurrences: Counter[str] = Counter()
    document_frequency: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)
    source_mix: dict[str, Counter[str]] = defaultdict(Counter)
    blocked = AUTO_NOISE | (READING_NOISE if skill == "Reading" else LISTENING_NOISE)
    for document in documents:
        tokens = [token for token in tokenize(document["text"]) if len(token) >= 3]
        per_document: Counter[str] = Counter()
        for size in (2, 3):
            for index in range(len(tokens) - size + 1):
                gram = tokens[index:index + size]
                if gram[0] in AUTO_EDGE or gram[-1] in AUTO_EDGE:
                    continue
                if size == 2 and gram[0] in BROKEN_BIGRAM_FIRST and gram[1] in COMMON_VERBS_OR_GAPS:
                    continue
                if any(token in blocked or token in AUTO_INTERIOR_NOISE for token in gram) or len(set(gram)) < len(gram):
                    continue
                phrase = " ".join(gram)
                if phrase in excluded:
                    continue
                per_document[phrase] += 1
        for phrase, count in per_document.items():
            occurrences[phrase] += count
            document_frequency[phrase] += 1
            sources[phrase].add(document["sourceName"])
            source_mix[phrase][document["sourceGroup"]] += count
    candidates = [
        phrase for phrase in occurrences
        if occurrences[phrase] >= 5 and document_frequency[phrase] >= 4 and len(sources[phrase]) >= 2
    ]
    candidates.sort(key=lambda phrase: (-len(sources[phrase]), -document_frequency[phrase], -occurrences[phrase], -len(phrase.split()), phrase))
    rows = []
    # Keep the complete qualifying set.  The browser paginates the result, so
    # a build-time top-N limit would only hide valid corpus evidence.
    for phrase in candidates:
        category = auto_category(skill, phrase)
        df = document_frequency[phrase]
        rows.append({
            "id": f"{skill.lower()}-auto-{hashlib.sha1(phrase.encode()).hexdigest()[:16]}",
            "skill": skill,
            "phrase": phrase,
            "category": category,
            "meaningZh": f"{category}高频搭配（语料自动发现）",
            "frame": phrase,
            "usageZh": CATEGORY_TIPS[category] + " 本条是按跨文档、跨来源重复出现自动发现的学习索引，不冒充人工翻译。",
            "exampleEn": "",
            "exampleZh": "",
            "occurrenceCount": occurrences[phrase],
            "documentFrequency": df,
            "documentCoverage": round(df / len(documents), 6),
            "sourceCount": len(sources[phrase]),
            "sourceMix": dict(source_mix[phrase].most_common()),
            "confidence": confidence(df, len(sources[phrase]), len(documents)),
            "contentLabel": "语料自动发现",
            "tier": "expansion",
        })
    return rows


def build(corpus_path: Path, materials_path: Path) -> dict:
    rows = collect_documents(corpus_path, materials_path)
    public_corpus = json.loads((ROOT / "data" / "corpus.json").read_text(encoding="utf-8"))
    public_coverage = {item["skill"]: item for item in public_corpus["coverage"]}

    by_skill = {skill: [row for row in rows if row["skill"] == skill] for skill in ("Reading", "Listening")}
    for skill, documents in by_skill.items():
        expected = public_coverage[skill]["documents"]
        if len(documents) != expected:
            raise ValueError(f"{skill} source drift: extracted {len(documents)} documents, expected {expected}")
    chunks = []
    category_counts: dict[str, Counter] = {"Reading": Counter(), "Listening": Counter()}
    seen_phrases: dict[str, set[str]] = {"Reading": set(), "Listening": set()}

    for skill, entries in (("Reading", READING), ("Listening", LISTENING)):
        documents = by_skill[skill]
        tokenized = [tokenize(row["text"]) for row in documents]
        for phrase, category, meaning, frame, usage, example_en, example_zh in entries:
            per_document = [count_phrase(tokens, phrase) for tokens in tokenized]
            occurrence_count = sum(per_document)
            document_frequency = sum(count > 0 for count in per_document)
            matching_sources = {documents[index]["sourceName"] for index, count in enumerate(per_document) if count}
            source_mix = Counter()
            for index, count in enumerate(per_document):
                if count:
                    source_mix[documents[index]["sourceGroup"]] += count
            if occurrence_count == 0:
                raise ValueError(f"Phrase is absent from {skill} corpus: {phrase}")
            category_counts[skill][category] += 1
            seen_phrases[skill].add(phrase)
            chunks.append({
                "id": f"{skill.lower()}-{re.sub(r'[^a-z]+', '-', phrase).strip('-')}",
                "skill": skill,
                "phrase": phrase,
                "category": category,
                "meaningZh": meaning,
                "frame": frame,
                "usageZh": usage,
                "exampleEn": example_en,
                "exampleZh": example_zh,
                "occurrenceCount": occurrence_count,
                "documentFrequency": document_frequency,
                "documentCoverage": round(document_frequency / len(documents), 6),
                "sourceCount": len(matching_sources),
                "sourceMix": dict(source_mix.most_common()),
                "confidence": confidence(document_frequency, len(matching_sources), len(documents)),
                "contentLabel": "本站原创例句",
                "tier": "core",
            })

    for skill, entries in (("Reading", READING_EXPANSION), ("Listening", LISTENING_EXPANSION)):
        documents = by_skill[skill]
        tokenized = [tokenize(row["text"]) for row in documents]
        for phrase, category, meaning in entries:
            if phrase in seen_phrases[skill]:
                continue
            per_document = [count_phrase(tokens, phrase) for tokens in tokenized]
            occurrence_count = sum(per_document)
            document_frequency = sum(count > 0 for count in per_document)
            if occurrence_count == 0:
                continue
            matching_sources = {documents[index]["sourceName"] for index, count in enumerate(per_document) if count}
            source_mix = Counter()
            for index, count in enumerate(per_document):
                if count:
                    source_mix[documents[index]["sourceGroup"]] += count
            category_counts[skill][category] += 1
            seen_phrases[skill].add(phrase)
            chunks.append({
                "id": f"{skill.lower()}-{re.sub(r'[^a-z]+', '-', phrase).strip('-')}",
                "skill": skill,
                "phrase": phrase,
                "category": category,
                "meaningZh": meaning,
                "frame": phrase,
                "usageZh": CATEGORY_TIPS[category],
                "exampleEn": "",
                "exampleZh": "",
                "occurrenceCount": occurrence_count,
                "documentFrequency": document_frequency,
                "documentCoverage": round(document_frequency / len(documents), 6),
                "sourceCount": len(matching_sources),
                "sourceMix": dict(source_mix.most_common()),
                "confidence": confidence(document_frequency, len(matching_sources), len(documents)),
                "contentLabel": "语料扩展索引",
                "tier": "expansion",
            })

    for skill in ("Reading", "Listening"):
        discovered = discover_chunks(skill, by_skill[skill], seen_phrases[skill])
        chunks.extend(discovered)
        for item in discovered:
            category_counts[skill][item["category"]] += 1
            seen_phrases[skill].add(item["phrase"])

    chunks.sort(key=lambda item: (item["skill"], -item["documentFrequency"], -item["occurrenceCount"], item["phrase"]))
    skill_stats = []
    for skill in ("Reading", "Listening"):
        documents = by_skill[skill]
        coverage = public_coverage[skill]
        selected = [item for item in chunks if item["skill"] == skill]
        skill_stats.append({
            "skill": skill,
            "documents": len(documents),
            "sourceCount": coverage["sources"],
            "filteredTokenCount": coverage["filteredTokens"],
            "sourceGroups": coverage["sourceGroups"],
            "chunkCount": len(selected),
            "coreChunkCount": sum(item["tier"] == "core" for item in selected),
            "expansionChunkCount": sum(item["tier"] == "expansion" for item in selected),
            "categories": [{"name": name, "count": count} for name, count in category_counts[skill].items()],
        })

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "titleZh": "阅读与听力词块库",
            "contentLabel": "统计证据 + 本站原创学习内容",
            "sourceFile": "corpus_dedup.csv + 本地资料去重 PDF + 剑桥雅思 4-21 私有分段缓存",
            "sourceLayers": ["official_public", "cambridge_practice", "cambridge_derived", "third_party_prediction"],
            "discoveryPolicy": "all_qualifying_no_top_n_cap",
            "chunkCount": len(chunks),
            "coreChunkCount": sum(item["tier"] == "core" for item in chunks),
            "expansionChunkCount": sum(item["tier"] == "expansion" for item in chunks),
            "copyrightNoteZh": "核心精学含原创搭配讲解与双语例句；扩展索引同时包含人工整理条目与跨来源自动发现的全部合格高频搭配，不设前 450 条上限。自动条目只给功能标签，不冒充人工翻译；所有层级均不复制原题长句。",
        },
        "methodology": {
            "countUnitZh": "按大小写归一后的连续词序列精确计数；同一统计单元内可重复出现。",
            "coverageZh": "文档覆盖表示至少出现一次该词块的统计单元占比。",
            "confidenceZh": "高可信需覆盖约 12% 的统计单元且跨至少两个来源集合；覆盖 3 个及以上但未跨来源为中，其余为探索。完整原题与派生资料分层统计。",
            "tierZh": "核心精学包含逐条搭配骨架、使用提示和原创例句；扩展索引包含人工整理条目与跨来源自动发现条目，两者均报告功能分类和语料证据。",
        },
        "skillStats": skill_stats,
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Reading and Listening phrase-chunk data.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--materials", type=Path, default=DEFAULT_MATERIALS)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "chunks.json")
    args = parser.parse_args()
    payload = build(args.corpus, args.materials)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {payload['meta']['chunkCount']} chunks to {args.output}")


if __name__ == "__main__":
    main()
