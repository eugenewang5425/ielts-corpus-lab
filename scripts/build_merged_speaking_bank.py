from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / "雅思语料研究" / "outputs" / "data" / "speaking_integrated_topics.csv"
LOCAL_SOURCE = ROOT.parent / "outputs" / "ielts-corpus-build" / "local_speaking_topics.csv"
OUTPUT = ROOT / "data" / "speaking.json"


TOPICS = [
    ("music", "Music & singing", "音乐与歌唱", "activity/hobby", [r"\bmusic\b", r"\bsongs?\b", r"\bsing(?:ing|er)?\b", r"\bconcert\b", r"\bmusician"]),
    ("film_tv", "Films, television & comedy", "电影、电视与喜剧", "activity/hobby", [r"\bfilms?\b", r"\bmovies?\b", r"\bcinema\b", r"\btelevision\b", r"\bTV\b", r"\bcomed(?:y|ies)\b", r"\bjokes?\b", r"\bprogramme\b", r"\bprogram you (?:watch|like)"]),
    ("books_reading", "Books, stories & reading", "书籍、故事与阅读", "activity/hobby", [r"\bbooks?\b", r"\bread(?:ing)?\b", r"\bstor(?:y|ies)\b", r"\bnovels?\b", r"\blibrar", r"\bpoe(?:m|try)"] ),
    ("social_media", "Social media & the internet", "社交媒体与互联网", "object/technology", [r"social media", r"\binternet\b", r"\bwebsites?\b", r"\bonline\b", r"\bdigital platform", r"\bpost(?:ed|ing)?\b"]),
    ("technology", "Technology, phones & devices", "科技、手机与设备", "object/technology", [r"\btechnology\b", r"technological", r"\bdevices?\b", r"\bcomputers?\b", r"\bphones?\b", r"mobile phone", r"\bapps?\b", r"\bsoftware\b", r"\bprograms?\b", r"\bheadphones?\b", r"\btyping\b", r"\brobots?\b", r"\bmachines?\b", r"\bappliances?\b"]),
    ("science_space", "Science & outer space", "科学与太空", "work-study", [r"\bscience\b", r"scientific", r"outer space", r"\bplanets?\b", r"\bstars?\b", r"\bastronaut", r"\bmoon\b"]),
    ("art_creativity", "Art, creativity & imagination", "艺术、创造力与想象力", "activity/hobby", [r"\bart\b", r"\bartist", r"\bdraw(?:ing)?\b", r"\bpaint(?:ing|er)?\b", r"\bcreative", r"\bcreativity\b", r"\bimagination\b", r"\bdesign(?:er)?\b"]),
    ("photos", "Photos & visual memories", "摄影与影像记忆", "activity/hobby", [r"\bphotos?\b", r"\bphotograph", r"\bpictures?\b", r"take a picture", r"take pictures"]),
    ("advertising_news", "Advertising, news & media", "广告、新闻与媒体", "society-government", [r"\badvertis", r"\bcommercials?\b", r"\bnews\b", r"\bnewspapers?\b", r"mass media"]),
    ("sports", "Sports, teams & exercise", "运动、团队与锻炼", "activity/hobby", [r"\bsports?\b", r"sports team", r"\bmatches?\b", r"\bexercise\b", r"\bgym\b", r"\bfitness\b", r"\bathlete", r"\bfootball\b", r"\bwalking\b", r"\bcycling\b"]),
    ("hobbies", "Hobbies & spare time", "爱好与闲暇", "activity/hobby", [r"\bhobb(?:y|ies)\b", r"free time", r"spare time", r"\bleisure\b", r"\bweekends?\b", r"days? off"]),
    ("teachers_education", "Teachers, schools & education", "教师、学校与教育", "work-study", [r"\bteachers?\b", r"\bschools?\b", r"\bstudents?\b", r"\bstud(?:y|ies|ying|ied)\b", r"\bsubjects?\b", r"\bexams?\b", r"\buniversity\b", r"\bcollege\b", r"\beducation\b", r"\bhomework\b", r"\bclass(?:es|room)?\b"]),
    ("language_learning", "Languages & learning", "语言与学习", "work-study", [r"\blanguages?\b", r"foreign language", r"\bEnglish\b", r"\blearn(?:ing|ed|t)?\b", r"without (?:a )?teacher", r"\bskills?\b"]),
    ("work_careers", "Work, careers & business", "工作、职业与商业", "work-study", [r"\bwork(?:ed|ing)?\b", r"\bjobs?\b", r"\bcareers?\b", r"\bbusiness", r"\bcompanies?\b", r"\boffices?\b", r"\bcolleagues?\b", r"\bemploy", r"\bprofession", r"\bmanager", r"\bsalary\b"]),
    ("home", "Home & accommodation", "住宅与居住", "home/hometown/accommodation", [r"\bhome\b", r"\bhouses?\b", r"\bapartments?\b", r"\baccommodation\b", r"\brooms?\b", r"where you live", r"living place", r"\bfurniture\b"]),
    ("hometown_neighbourhood", "Hometown & neighbourhood", "家乡与社区", "home/hometown/accommodation", [r"\bhometown\b", r"neighbou?rhood", r"the area you live", r"local area", r"\bneighbou?rs?\b"]),
    ("cities_countryside", "Cities & the countryside", "城市与乡村", "place", [r"\bcities?\b", r"\bcity\b", r"\bcountryside\b", r"\brural\b", r"\burban\b", r"\btowns?\b", r"city you live", r"city life"]),
    ("buildings", "Buildings & architecture", "建筑与空间", "place", [r"\bbuildings?\b", r"\barchitecture\b", r"\bskyscraper", r"tall building", r"historic building"]),
    ("parks_public_places", "Parks & public places", "公园与公共空间", "place", [r"\bparks?\b", r"public gardens?", r"green spaces?", r"public places?", r"public space", r"\bplaygrounds?\b", r"community cent(?:er|re)"]),
    ("travel_holidays", "Travel, trips & holidays", "旅行、出游与假期", "travel-transport", [r"\btravel", r"\btrips?\b", r"\bjourneys?\b", r"\bholidays?\b", r"\bvacations?\b", r"\btourists?\b", r"\btourism\b", r"\boverseas\b", r"visit another country"]),
    ("transport", "Transport, cars & bicycles", "交通、汽车与自行车", "travel-transport", [r"\btransport", r"\bcars?\b", r"\bbicycles?\b", r"\bbikes?\b", r"\bmotorcycles?\b", r"\bbuses?\b", r"\btrains?\b", r"\btraffic\b", r"\bdriv(?:e|ing|er)\b", r"\bcommut"]),
    ("shopping", "Shopping & consumer choices", "购物与消费选择", "place", [r"\bshopping\b", r"\bshops?\b", r"\bstores?\b", r"shopping cent(?:er|re)", r"\bbuy(?:ing)?\b", r"\bpurchases?\b", r"consumer"]),
    ("money_prices", "Money, prices & saving", "金钱、价格与储蓄", "work-study", [r"\bmoney\b", r"\bprices?\b", r"\bcost\b", r"expensive", r"\bsav(?:e|ing|ings)\b", r"\bspend(?:ing)?\b", r"\bpay(?:ing|ment)?\b", r"\bbudget\b"]),
    ("clothing", "Clothing & fashion", "服装与时尚", "other", [r"\bclothes?\b", r"\bclothing\b", r"\bfashion\b", r"\bshoes?\b", r"\bdress(?:es|ed)?\b", r"\buniforms?\b", r"second-hand clothes"]),
    ("food", "Food, meals & cooking", "食物、聚餐与烹饪", "food", [r"\bfood\b", r"\bmeals?\b", r"\bcook(?:ing|ed)?\b", r"\bdishes?\b", r"\brestaurants?\b", r"\beat(?:ing)?\b", r"\bdiet\b", r"\bbreakfast\b", r"\bdinner\b", r"\blunch\b"]),
    ("health", "Health & medicine", "健康与医疗", "person/family/friends", [r"\bhealth\b", r"\bhealthy\b", r"\bdoctors?\b", r"\bmedicine\b", r"\bmedical\b", r"\bhospitals?\b", r"\billness", r"\bdisease", r"\bnurses?\b", r"mental health"]),
    ("family", "Family & family relationships", "家庭与亲情", "person/family/friends", [r"\bfamil(?:y|ies)\b", r"family member", r"\bparents?\b", r"\bmother\b", r"\bfather\b", r"\bsiblings?\b", r"\bbrothers?\b", r"\bsisters?\b", r"\brelatives?\b"]),
    ("friends", "Friends & social relationships", "朋友与社交关系", "person/family/friends", [r"\bfriends?\b", r"\bfriendship", r"\bpeople together\b", r"social relationships?", r"\bcompanions?\b"]),
    ("children_childhood", "Children & childhood", "儿童与童年", "person/family/friends", [r"\bchildren\b", r"\bchild\b", r"\bchildhood\b", r"when you were young", r"\bteenagers?\b", r"young people"]),
    ("older_people", "Older people & generations", "老年人与代际", "person/family/friends", [r"older people", r"elderly", r"old people", r"\bgenerations?\b", r"younger and older", r"age groups?"]),
    ("people_personality", "People, personality & role models", "人物、性格与榜样", "person/family/friends", [r"\bperson\b", r"\bpersonality\b", r"\bcharacter\b", r"someone who", r"a person who", r"\brole model", r"\bstranger"]),
    ("famous_people", "Famous people & public figures", "名人与公众人物", "person/family/friends", [r"famous (?:person|people)", r"\bcelebrit", r"public figure", r"well-known person"]),
    ("gifts_possessions", "Gifts & personal possessions", "礼物与个人物品", "object/technology", [r"\bgifts?\b", r"\bpresents?\b", r"\bpossessions?\b", r"important (?:thing|item|object)", r"\bbelongings?\b", r"something you own", r"\bwatch(?:es)?\b", r"\bmirrors?\b"]),
    ("animals", "Animals & pets", "动物与宠物", "other", [r"\banimals?\b", r"\bpets?\b", r"\bdogs?\b", r"\bcats?\b", r"\bwildlife\b", r"\bbirds?\b"]),
    ("plants_gardening", "Plants, flowers & gardening", "植物、花卉与园艺", "home/hometown/accommodation", [r"\bplants?\b", r"\bflowers?\b", r"\bgarden(?:ing|er)?\b", r"grow plants", r"\btrees?\b"]),
    ("nature_scenery", "Nature, scenery & outdoor places", "自然、风景与户外地点", "place", [r"\bnature\b", r"\bnatural\b", r"\bscenery\b", r"\bviews?\b", r"\bmountains?\b", r"\bbeach(?:es)?\b", r"\bforests?\b", r"\brivers?\b", r"\blakes?\b", r"outdoors?"]),
    ("environment", "Environment & sustainability", "环境与可持续发展", "society-government", [r"\benvironment", r"\bpollution\b", r"\brecycl", r"\bwaste\b", r"climate change", r"global warming", r"fossil fuels?", r"\bplastic\b", r"sustainab"]),
    ("weather", "Weather & seasons", "天气与季节", "other", [r"\bweather\b", r"\bseasons?\b", r"\brain(?:y|ing)?\b", r"\bsnow\b", r"\btemperature\b", r"hot weather", r"cold weather"]),
    ("government_law", "Government, laws & public services", "政府、法律与公共服务", "society-government", [r"\bgovernments?\b", r"\blaws?\b", r"\brules?\b", r"\bpolic(?:y|ies)\b", r"public services?", r"legal", r"\bregulations?\b"]),
    ("society", "Society & social change", "社会与社会变化", "society-government", [r"\bsociety\b", r"social change", r"communities?", r"\bpublic\b", r"modern life", r"quality of life", r"social problem"]),
    ("culture_history", "Culture, traditions & history", "文化、传统与历史", "culture", [r"\bculture\b", r"cultural", r"\btraditions?\b", r"traditional", r"\bhistory\b", r"historic", r"\bheritage\b", r"\bmuseums?\b"]),
    ("festivals_events", "Festivals, celebrations & events", "节日、庆典与活动", "event/experience", [r"\bfestivals?\b", r"\bcelebrat", r"special occasions?", r"\bpart(?:y|ies)\b", r"\bevents?\b", r"\bceremon"]),
    ("crime_safety", "Crime, safety & responsibility", "犯罪、安全与责任", "society-government", [r"\bcrime\b", r"\bcriminal", r"\bpolice\b", r"\bsafety\b", r"\bsafe\b", r"\bdanger", r"\bpunish", r"\bprison"]),
    ("plans_decisions", "Plans, decisions & change", "计划、决定与改变", "event/experience", [r"\bplans?\b", r"\bplanning\b", r"\bdecisions?\b", r"change(?:d)? (?:your|an|a) (?:mind|opinion|plan)", r"\bchoices?\b", r"make up your mind"]),
    ("goals_success", "Goals, ambition & success", "目标、抱负与成功", "event/experience", [r"\bgoals?\b", r"\bambition", r"\bsuccess", r"\bachiev", r"\bproud\b", r"\baward", r"\bcompetition"]),
    ("problems_challenges", "Problems, challenges & solutions", "问题、挑战与解决", "event/experience", [r"\bproblems?\b", r"\bchalleng", r"\bdifficult", r"\bsolutions?\b", r"\bsolve", r"\bmistakes?\b", r"\bfail"]),
    ("help_advice", "Help, advice & kindness", "帮助、建议与善意", "event/experience", [r"\bhelp(?:ed|ing|s)?\b", r"\badvi[cs]e\b", r"\bencourag", r"\bsupport", r"\bkind(?:ness)?\b", r"\bvolunteer", r"do a favour", r"favor for"]),
    ("emotions", "Emotions, happiness & behaviour", "情绪、快乐与行为", "event/experience", [r"\bhappy\b", r"\bhappiness\b", r"\bsmil", r"\bfeelings?\b", r"\bemotions?\b", r"\bangry\b", r"\bsad\b", r"\bexcited\b", r"\bpatient", r"\bpolite\b", r"\bbehavio"]),
    ("memory_past", "Memory & past experiences", "记忆与过往经历", "event/experience", [r"\bmemor(?:y|ies|able)\b", r"\bremember", r"in the past", r"past experience", r"\bnostalgia", r"\bforgot"]),
    ("time_routines", "Time & daily routines", "时间与日常作息", "event/experience", [r"\bmorning\b", r"get up early", r"\bdaily routine", r"\btime\b", r"\bpunctual", r"\blate\b", r"\bwait(?:ing)?\b", r"\bschedule"]),
    ("organisation", "Tidiness & organisation", "整洁与组织安排", "other", [r"\btid(?:y|iness)\b", r"\borganis", r"\borganiz", r"\bplanning skills?\b", r"well[- ]organised", r"well[- ]organized"]),
    ("communication", "Communication, messages & conversation", "沟通、信息与交谈", "event/experience", [r"\bmessages?\b", r"\bemails?\b", r"\bconversation", r"\btalk(?:ing|ed)?\b", r"\bcommunicat", r"\bletters?\b", r"\breply\b", r"\bcontact\b"]),
    ("places_facilities", "Places, facilities & local services", "地点、设施与本地服务", "place", [r"\bplaces?\b", r"\blocation\b", r"\bfacilit", r"\bquiet place", r"\bcrowded place", r"\bmarket\b", r"\bstadium\b", r"\bhotel\b"]),
    ("everyday_objects", "Everyday objects & practical life", "日常物品与实用生活", "object/technology", [r"\bobjects?\b", r"\bitems?\b", r"\bthings?\b", r"\bkeys?\b", r"\bbags?\b", r"\btools?\b", r"\btoys?\b"]),
    ("other", "Everyday life & other topics", "日常生活与其他话题", "other", []),
]


TOPIC_BY_KEY = {item[0]: item for item in TOPICS}
FALLBACK_BY_THEME = {
    "activity/hobby": "hobbies",
    "object/technology": "technology",
    "travel-transport": "travel_holidays",
    "place": "places_facilities",
    "home/hometown/accommodation": "home",
    "event/experience": "memory_past",
    "food": "food",
    "society-government": "society",
    "work-study": "work_careers",
    "person/family/friends": "people_personality",
    "culture": "culture_history",
    "other": "other",
}

BROAD_TITLES = {
    "activity/hobby", "event/experience", "food", "home/hometown/accommodation",
    "object/technology", "person/family/friends", "place", "society-government",
    "travel-transport", "work-study",
}

JOE_TOPIC_MAP = {
    "Music": "music",
    "Teachers": "teachers_education",
    "Social media": "social_media",
    "Tidiness": "organisation",
    "Websites": "social_media",
    "Watch": "gifts_possessions",
    "Shopping": "shopping",
    "Cars": "transport",
    "Public gardens and parks": "parks_public_places",
    "Science": "science_space",
    "Mirrors": "gifts_possessions",
    "Outer space and stars": "science_space",
    "Singing": "music",
    "Clothing": "clothing",
    "Jokes & Comedies": "film_tv",
    "Headphones": "technology",
    "Food": "food",
    "Pets and Animals": "animals",
    "Sports team": "sports",
    "Hobby": "hobbies",
    "Morning time": "time_routines",
    "Gifts": "gifts_possessions",
    "Reading": "books_reading",
    "Walking": "sports",
    "Typing": "technology",
    "Scenery": "nature_scenery",
    "Building": "buildings",
    "Childhood activities": "children_childhood",
    "Views": "nature_scenery",
    "Life stages": "children_childhood",
    "Spare time": "hobbies",
    "Memory": "memory_past",
    "Crowded place": "places_facilities",
    "Work or studies": "work_careers",
    "Home/accommodation": "home",
    "Hometown": "hometown_neighbourhood",
    "The area you live in": "hometown_neighbourhood",
    "The city you live in": "cities_countryside",
    "Tall building you like or dislike": "buildings",
    "Interesting video": "film_tv",
    "Boring place": "places_facilities",
    "Got up early": "time_routines",
    "Person who grows plants": "plants_gardening",
    "New law to introduce": "government_law",
    "Childhood friend": "friends",
    "Person with medical career": "health",
    "Person with successful business": "work_careers",
    "Recently changed plan": "plans_decisions",
    "Worked in a group": "work_careers",
    "Important decision that you made": "plans_decisions",
    "Live sports event you watched and liked": "sports",
    "Food for special occasions/events": "food",
    "Person good at languages": "language_learning",
    "Challenging technological problem": "technology",
    "Advertisement with a famous person": "advertising_news",
    "Place travelled to recommend": "travel_holidays",
    "Home you like to visit but not live in": "home",
    "Story/book with animals": "books_reading",
    "Law on environmental protection": "environment",
    "Message or email with no reply": "communication",
    "Long-term goal/ambition": "goals_success",
    "Changed an important opinion": "plans_decisions",
    "Environmental law to introduce": "environment",
    "Perfect job": "work_careers",
    "Famous person you would like to meet": "famous_people",
    "Occasion when not allowed to use phone": "technology",
    "Giving advice": "help_advice",
    "Technology you would like to own": "technology",
    "Person good at planning": "organisation",
    "Child who loves drawing": "art_creativity",
    "App/Program": "technology",
    "Smiling occasion": "emotions",
    "Proud of family member": "family",
    "Important thing for family": "family",
    "Bicycle/motorcycle/car trip": "transport",
    "Person who solved problem smartly": "problems_challenges",
    "Friend learned without teacher": "language_learning",
    "Music event you didn't enjoy": "music",
    "Recent movie": "film_tv",
    "Interesting building": "buildings",
    "Using imagination": "art_creativity",
    "Person who helps others": "help_advice",
    "Item cost more than expected": "money_prices",
    "Encouraging someone": "help_advice",
    "Short-term overseas job": "work_careers",
    "Nature-loving person": "nature_scenery",
    "Shop/store you enjoy visiting": "shopping",
    "City you enjoyed visiting": "cities_countryside",
    "Quiet place you like to go": "places_facilities",
    "TV or online program you like to watch": "film_tv",
}


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:16]}"


def clean_question(text: str) -> str:
    text = re.sub(r"^\s*\d+\s*[.)]\s*", "", text)
    text = re.sub(r"^\s*[–—-]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_questions(raw: str, part: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    entries: list[str] = []
    current: list[str] = []
    for raw_line in raw.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        numbered = re.match(r"^\s*\d+\s*[.)]\s*", line)
        if numbered:
            if current:
                entries.append(clean_question(" ".join(current)))
            current = [clean_question(line)]
        elif current:
            current.append(line)
        else:
            current = [clean_question(line)]
    if current:
        entries.append(clean_question(" ".join(current)))
    if part != "Part 2":
        flattened: list[str] = []
        for entry in entries:
            pieces = re.split(r"(?<=\?)\s+(?=[–—-]?[A-Z])", entry)
            flattened.extend(clean_question(piece) for piece in pieces if clean_question(piece))
        entries = flattened
    return [entry for entry in entries if is_valid_question(entry)]


def is_valid_question(text: str) -> bool:
    lowered = text.lower()
    if len(text) < 4:
        return False
    blocked = ("unavailable", "not available", "prompt group", "practice these topics")
    if any(marker in lowered for marker in blocked):
        return False
    normalized = re.sub(r"[^a-z]+", " ", lowered).strip()
    if normalized in {"why", "how", "why not", "what else", "and how", "and why", "how often", "why and how"}:
        return False
    if normalized.startswith("talk about ") and len(normalized.split()) < 5:
        return False
    return True


def normalise_question(text: str) -> str:
    value = text.lower()
    replacements = {
        "favourite": "favorite",
        "organisation": "organization",
        "organise": "organize",
        "centre": "center",
        "travelling": "traveling",
        "neighbourhood": "neighborhood",
        "neighbours": "neighbors",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical_topic(row: dict[str, str], question: str) -> str:
    title = row.get("topic_title", "")
    source = row.get("source_name", "")
    if source.startswith("Joe Speaking") and title in JOE_TOPIC_MAP:
        return JOE_TOPIC_MAP[title]
    context = question
    if not title.lower().startswith("exam report") and title.lower() not in BROAD_TITLES:
        context = f"{title}. {question}"
    best_key = ""
    best_score = 0
    for key, _title, _zh, _theme, patterns in TOPICS[:-1]:
        score = sum(1 for pattern in patterns if re.search(pattern, context, flags=re.IGNORECASE))
        if score > best_score:
            best_key = key
            best_score = score
    if best_key:
        return best_key
    return FALLBACK_BY_THEME.get(row.get("primary_theme", "other"), "other")


def source_ref(row: dict[str, str]) -> tuple[str, dict[str, object]]:
    payload = "|".join([
        row.get("source_name", ""), row.get("source_status", ""), row.get("period", ""),
        row.get("region", ""), row.get("source_url", ""), row.get("phase", ""),
    ])
    ref = stable_id("source", payload)
    status = row.get("source_status", "")
    group = {
        "official_public_sample": "official_public",
        "user_provided_copy_unofficial": "user_provided",
        "test_taker_recall": "test_taker_recall",
        "public_compilation_unofficial": "public_compilation",
        "local_private_compilation": "local_question_bank",
    }.get(status, status or "unknown")
    return ref, {
        "id": ref,
        "name": row.get("source_name", "来源未标注"),
        "status": status,
        "sourceGroup": group,
        "period": row.get("period", "") or "时期未标注",
        "region": row.get("region", "") or "地区未标注",
        "url": row.get("source_url", ""),
        "phase": row.get("phase", "") or "historical_or_unlabelled",
    }


def main() -> None:
    if not DEFAULT_SOURCE.exists():
        raise FileNotFoundError(f"Speaking source CSV not found: {DEFAULT_SOURCE}")
    with DEFAULT_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if LOCAL_SOURCE.exists():
        with LOCAL_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
            rows.extend(csv.DictReader(handle))

    sources: dict[str, dict[str, object]] = {}
    topic_questions: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    aliases: dict[str, set[str]] = defaultdict(set)
    source_occurrences = 0
    part_fields = (("Part 1", "part_1_questions"), ("Part 2", "part_2_cue_cards"), ("Part 3", "part_3_questions"))

    for row in rows:
        ref, source = source_ref(row)
        sources[ref] = source
        raw_title = row.get("topic_title", "").strip()
        for part, field in part_fields:
            for text in split_questions(row.get(field, ""), part):
                source_occurrences += 1
                key = canonical_topic(row, text)
                normalized = normalise_question(text)
                if not normalized:
                    continue
                question_key = f"{part}|{normalized}"
                question = topic_questions[key].get(question_key)
                if question is None:
                    question = {
                        "id": stable_id("sourceq", f"{key}|{question_key}"),
                        "part": part,
                        "text": text,
                        "sourceRefs": [],
                    }
                    topic_questions[key][question_key] = question
                if ref not in question["sourceRefs"]:
                    question["sourceRefs"].append(ref)
                if raw_title and not raw_title.lower().startswith("exam report") and raw_title.lower() not in BROAD_TITLES:
                    aliases[key].add(raw_title)

    part_order = {"Part 1": 1, "Part 2": 2, "Part 3": 3}
    topics: list[dict[str, object]] = []
    for key, title, title_zh, theme, _patterns in TOPICS:
        questions = list(topic_questions.get(key, {}).values())
        if not questions:
            continue
        for question in questions:
            question["sourceRefs"].sort(key=lambda ref: (
                str(sources[ref]["period"]) == "时期未标注",
                str(sources[ref]["period"]),
                str(sources[ref]["name"]),
            ), reverse=True)
            question["current"] = any(
                str(sources[ref].get("phase")) == "current_2026"
                or (
                    str(sources[ref]["period"]).startswith("2026")
                    and str(sources[ref].get("phase")) != "upcoming_prediction"
                )
                for ref in question["sourceRefs"]
            )
            question["upcoming"] = any(str(sources[ref].get("phase")) == "upcoming_prediction" for ref in question["sourceRefs"])
        questions.sort(key=lambda question: (
            part_order[question["part"]],
            not question["current"],
            question["text"].lower(),
        ))
        topic_source_refs = sorted({ref for question in questions for ref in question["sourceRefs"]})
        periods = sorted({str(sources[ref]["period"]) for ref in topic_source_refs}, reverse=True)
        parts = [part for part in part_order if any(question["part"] == part for question in questions)]
        topics.append({
            "id": f"merged_{key}",
            "key": key,
            "title": title,
            "titleZh": title_zh,
            "primaryTheme": theme,
            "partStructure": " / ".join(parts),
            "parts": parts,
            "aliases": sorted(aliases.get(key, set()), key=str.lower),
            "questionCount": len(questions),
            "currentQuestionCount": sum(1 for question in questions if question["current"]),
            "sourceCount": len(topic_source_refs),
            "current": any(question["current"] for question in questions),
            "periods": periods,
            "questions": questions,
        })
    topics.sort(key=lambda topic: (-int(topic["currentQuestionCount"]), -int(topic["questionCount"]), str(topic["title"])))

    unique_questions = sum(int(topic["questionCount"]) for topic in topics)
    current_questions = sum(int(topic["currentQuestionCount"]) for topic in topics)
    upcoming_questions = sum(1 for topic in topics for question in topic["questions"] if question.get("upcoming"))
    payload = {
        "meta": {
            "schemaVersion": 1,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "sourceRecordCount": len(rows),
            "sourceQuestionOccurrences": source_occurrences,
            "uniqueQuestionCount": unique_questions,
            "currentQuestionCount": current_questions,
            "upcomingQuestionCount": upcoming_questions,
            "mergedTopicCount": len(topics),
            "deduplicatedOccurrenceCount": source_occurrences - unique_questions,
            "method": "Split every source record into individual Part questions, assign a controlled canonical topic, normalise spelling and punctuation, then merge identical questions while retaining every source reference.",
            "copyrightNotice": "Questions are shown as attributed source records. Local 2026 compilations are deduplicated and attributed; third-party answers and audio are excluded. The 9–12 month source is labelled as an upcoming prediction rather than a verified current bank. The site does not claim that recall or compilation sources are official IELTS releases.",
        },
        "sources": sources,
        "topics": topics,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Merged {source_occurrences} question occurrences into {unique_questions} unique questions "
        f"across {len(topics)} canonical topics ({current_questions} current)."
    )


if __name__ == "__main__":
    main()
