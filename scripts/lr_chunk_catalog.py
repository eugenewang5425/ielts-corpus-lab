from __future__ import annotations


def _entries(category: str, blob: str) -> list[tuple[str, str, str]]:
    rows = []
    for raw in blob.strip().split("|"):
        phrase, meaning = raw.strip().split("=", 1)
        rows.append((phrase.strip(), category, meaning.strip()))
    return rows


READING_EXPANSION = [
    *_entries("逻辑与衔接", """
        for example=例如|such as=例如；诸如|due to=由于|as well as=以及；并且|one of the most=最……的之一|
        in fact=事实上|in order to=为了|instead of=而不是；代替|associated with=与……相关|related to=与……有关|
        in addition=此外|in addition to=除……之外还|as a result=因此；结果|over time=随着时间推移|
        in terms of=就……而言|compared with=与……相比|contribute to=促成；有助于|in response to=作为对……的回应|
        in the form of=以……的形式|at the same time=与此同时|on the other hand=另一方面|referred to=被称作；被提及为|
        is thought to=被认为会|is believed to=据信；被认为|in contrast=相比之下|in recent years=近年来|
        depends on=取决于|consists of=由……组成|can be found=可以在……找到|more likely to=更有可能|
        less likely to=较不可能|a variety of=各种各样的
    """),
    *_entries("数量与变化", """
        a wide range of=广泛的；多种|a large number of=大量的|a small number of=少量的|the majority of=大多数|
        the proportion of=……的比例|the rate of=……的比率|the level of=……的水平|an increase in=……的增长|
        a great deal of=大量的|a series of=一系列|a combination of=……的组合|large numbers=大量；大批|
        wide range=广泛范围|million years=数百万年|years ago=……年前
    """),
    *_entries("研究与分析", """
        research shows=研究显示|scientific research=科学研究|recent research=近期研究|research team=研究团队|
        study found=研究发现|analysis of=对……的分析|data from=来自……的数据|results of=……的结果|
        effect of=……的影响|effects of=……的多种影响|impact of=……的影响|role of=……的作用|
        relationship between=……之间的关系|difference between=……之间的差异|changes in=……的变化|process of=……的过程|
        method of=……的方法|system of=……的体系|source of=……的来源|form of=……的形式|
        type of=……的类型|types of=……的多种类型|different types=不同类型|important role=重要作用|
        point of view=观点；角度|valuable information=有价值的信息|ability to adapt=适应能力|high quality=高质量的
    """),
    *_entries("环境与科学", """
        climate change=气候变化|global warming=全球变暖|natural resources=自然资源|water resources=水资源|
        water vapour=水蒸气|wind speed=风速|body temperature=体温|sea level=海平面|
        natural environment=自然环境|endangered species=濒危物种|animal species=动物物种|human beings=人类|
        human activity=人类活动|human activities=多种人类活动|human brain=人脑|brain activity=大脑活动|
        immune system=免疫系统|blood pressure=血压|heart rate=心率|food intake=食物摄入量|
        eating habits=饮食习惯|drinking water=饮用水|exposure to sunlight=暴露于阳光|highly efficient=高效的|
        radiocarbon dating=放射性碳测年|chaos theory=混沌理论|scientific community=科学界
    """),
    *_entries("社会与发展", """
        young children=幼儿|child labour=童工|children's development=儿童发展|primary school=小学|
        job market=就业市场|full time work=全职工作|living conditions=生活条件|economic growth=经济增长|
        developing countries=发展中国家|industrial revolution=工业革命|middle class=中产阶级|rural areas=农村地区|
        urban areas=城市地区|modern society=现代社会|local people=当地居民|decision making=决策|
        problem solving=解决问题|technological development=技术发展|social interaction=社会互动|social development=社会发展|
        population growth=人口增长|health problems=健康问题|trade routes=贸易路线|illegal trade=非法贸易|
        medical school=医学院|nobel prize=诺贝尔奖|middle ages=中世纪|prehistoric ancestors=史前祖先|
        long term=长期的|large scale=大规模的|early stages=早期阶段|around the world=世界各地|
        throughout history=纵观历史
    """),
]


LISTENING_EXPANSION = [
    *_entries("互动与回应", """
        that's right=没错|anything else=还有别的吗|that's fine=那可以；没问题|i'm afraid=恐怕|
        don't worry=别担心|i'm sorry=抱歉|looking forward to=期待|able to find=能够找到|
        let's begin=我们开始吧|need to ask=需要询问|that's all=就这些|sounds great=听起来很棒|
        sounds good=听起来不错|could you tell me=你能告诉我吗|would you mind=你介意……吗|do you mean=你的意思是……吗|
        let me check=让我核对一下|let me see=让我看看|i think so=我想是的|i don't think=我认为不是；我不觉得|
        not sure=不确定|it depends=视情况而定|how about=……怎么样|what about=……怎么样
    """),
    *_entries("功能与动作", """
        used to=过去常常；曾用于|be able to=能够|be used to=习惯于；被用来|talk about=谈论|
        find out=查明；了解|look for=寻找|prepare for=为……做准备|agree with=同意；与……一致|
        ask about=询问关于……|think about=考虑|pick up=领取；接人|drop off=送到；放下|
        pay for=为……付款|fill in=填写|sign up=报名|take part in=参加|
        a bit more=再多一点|at least=至少|according to=根据|in relation to=关于；与……相关|
        made up of=由……组成|range of=一系列；范围|a number of=若干；……的数量|a range of=一系列|
        wide range of=广泛的；多种|a great deal of=大量的|a couple of=几个；一对|all kinds of=各种各样的
    """),
    *_entries("时间与安排", """
        next week=下周|few days=几天|long term=长期的|full time=全职；全日制|
        part time=兼职；非全日制|at the moment=目前|by the end of=到……末为止|at the beginning of=在……开始时|
        for the first time=第一次|as soon as=一……就……|from time to time=不时；偶尔|take time off=请假；休息一段时间|
        book in advance=提前预订|opening hours=营业时间|closing time=关闭时间
    """),
    *_entries("地点与方位", """
        city centre=市中心|in front of=在……前面|on the left=在左侧|on the right=在右侧|
        turn right=向右转|at the end of=在……尽头|just past=刚过……|next door to=紧挨着；隔壁|
        straight on=一直向前|on your left=在你的左侧|on your right=在你的右侧|opposite this=在这个的对面|
        ground floor=底层；一楼|main entrance=主入口|local area=当地地区|rural areas=农村地区|
        train station=火车站|shopping centre=购物中心|tourist information=游客信息；旅游咨询
    """),
    *_entries("手续与信息", """
        credit card=信用卡|online system=在线系统|personal details=个人信息|card details=银行卡信息|
        phone number=电话号码|reference number=参考编号|postal code=邮政编码|date of birth=出生日期|
        full name=全名|entrance fee=入场费|membership fee=会员费|entrance ticket=入场票|
        ticket prices=票价|customer service=客户服务|basic information=基本信息|background information=背景信息
    """),
    *_entries("学习与工作", """
        research project=研究项目|case study=案例研究|practical experience=实践经验|past experience=以往经验|
        time management=时间管理|study skills=学习技能|primary school=小学|student accommodation=学生宿舍|
        private accommodation=私人住宿|local community=当地社区|city council=市议会|natural habitat=自然栖息地|
        state of the art=最先进的
    """),
    *_entries("设施与场景", """
        information desk=服务台；信息台|reception desk=接待台|public library=公共图书馆|swimming pool=游泳池|
        air conditioning=空调|gift shop=礼品店|dining room=餐厅|seminar room=研讨室|
        sports centre=体育中心|arts centre=艺术中心|public transport=公共交通|accommodation office=住宿办公室
    """),
]


CATEGORY_TIPS = {
    "逻辑与衔接": "用于追踪作者的举例、因果、转折、比较和补充关系。",
    "数量与变化": "用于识别数量、比例、范围和时间尺度。",
    "研究与分析": "用于定位研究方法、证据、结果和作者判断。",
    "环境与科学": "常见于自然科学、环境、生物和健康类文章。",
    "社会与发展": "常见于历史、教育、工作、城市和社会发展主题。",
    "互动与回应": "用于识别确认、否定、犹豫、澄清和话轮转折。",
    "功能与动作": "重点听词块之后的对象、动作或选项。",
    "时间与安排": "用于捕捉日期、截止时间、频率和安排变化。",
    "地点与方位": "用于地图题和设施介绍中的位置关系。",
    "手续与信息": "用于表格填空、预订、付款和个人信息场景。",
    "学习与工作": "用于课程咨询、校园讨论、研究和职业场景。",
    "设施与场景": "用于快速预测地点、设施和服务类答案。",
}
