"""上海初中单元复习卷的公开目录范围与人工整理知识点。"""

GRADE = "六年级"
MATH_SOURCE_FIRST = "上海六年级第一学期《义务教育教科书（五·四学制）·数学》2024 年审定版目录"
MATH_SOURCE_SECOND = "上海六年级第二学期《义务教育教科书（五·四学制）·数学》2024 年审定版目录"
ENGLISH_SOURCE_FIRST = "上海六年级第一学期《义务教育教科书（五·四学制）·英语》2024 年审定版目录"
ENGLISH_SOURCE_SECOND = "上海六年级第二学期《义务教育教科书（五·四学制）·英语》2024 年审定版目录"


def unit(unit_id, subject, semester, title, knowledge_points, source_note):
    return {
        "id": unit_id,
        "grade": GRADE,
        "subject": subject,
        "semester": semester,
        "title": title,
        "knowledge_points": knowledge_points,
        "source_note": source_note,
    }


CURRICULUM_UNITS = [
    unit(
        "math-6a-rational-numbers",
        "math",
        "first",
        "第1章 有理数",
        ["有理数", "有理数的加法与减法", "有理数的乘法与除法", "有理数的乘方", "有理数的混合运算"],
        MATH_SOURCE_FIRST,
    ),
    unit(
        "math-6a-algebraic-expressions",
        "math",
        "first",
        "第2章 简单的代数式",
        ["用字母表示数", "代数式", "一次式"],
        MATH_SOURCE_FIRST,
    ),
    unit(
        "math-6a-linear-equation",
        "math",
        "first",
        "第3章 一元一次方程",
        ["方程与列方程", "一元一次方程及其解法", "一元一次方程的应用"],
        MATH_SOURCE_FIRST,
    ),
    unit(
        "math-6a-lines-angles",
        "math",
        "first",
        "第4章 线段与角",
        ["线段", "角"],
        MATH_SOURCE_FIRST,
    ),
    unit(
        "math-6b-ratio-proportion",
        "math",
        "second",
        "第5章 比与比例",
        ["比、比例及其性质", "百分数"],
        MATH_SOURCE_SECOND,
    ),
    unit(
        "math-6b-circle-sector",
        "math",
        "second",
        "第6章 圆与扇形",
        ["圆的周长与弧长", "圆与扇形的面积"],
        MATH_SOURCE_SECOND,
    ),
    unit(
        "math-6b-probability-statistics",
        "math",
        "second",
        "第7章 可能性与统计图表",
        ["随机现象及其结果的可能性", "数据的收集、整理与表达", "百分数的统计意义"],
        MATH_SOURCE_SECOND,
    ),
    unit(
        "math-6b-cylinder-cone",
        "math",
        "second",
        "第8章 圆柱与圆锥",
        ["圆柱及其侧面展开图", "圆锥及其侧面展开图"],
        MATH_SOURCE_SECOND,
    ),
    unit(
        "math-6b-linear-systems",
        "math",
        "second",
        "第9章 二元一次方程组",
        ["二元一次方程组的概念", "二元一次方程组的解法", "二元一次方程组的应用", "简单的三元一次方程组"],
        MATH_SOURCE_SECOND,
    ),
    unit(
        "english-6a-u1-school-life",
        "english",
        "first",
        "Unit 1 School life",
        ["school subjects", "school activities", "a school day", "my school life", "my dream school"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6a-u2-family-ties",
        "english",
        "first",
        "Unit 2 Family ties",
        ["family relations", "family members", "family duties", "family time", "a family poster"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6a-u3-food",
        "english",
        "first",
        "Unit 3 Food",
        ["food groups", "healthy food choices", "food for love", "my healthy dish", "a healthy school lunch menu"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6a-u4-sports",
        "english",
        "first",
        "Unit 4 Sports",
        ["sports activities", "sports safety", "sports fun", "sporting moments", "sports for us"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6a-u5-animals",
        "english",
        "first",
        "Unit 5 Animals and us",
        ["amazing animals", "getting along with animals", "a day on the farm", "my favourite animal", "an animal club logo"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6a-u6-travelling-china",
        "english",
        "first",
        "Unit 6 Travelling around China",
        ["a place to go", "ways of travelling", "young travellers", "my footprint", "a travel plan"],
        ENGLISH_SOURCE_FIRST,
    ),
    unit(
        "english-6b-u1-differences",
        "english",
        "second",
        "Unit 1 Everyone is different",
        ["noticing differences", "finding differences", "accepting differences", "showing differences", "future me"],
        ENGLISH_SOURCE_SECOND,
    ),
    unit(
        "english-6b-u2-rules",
        "english",
        "second",
        "Unit 2 Rules around us",
        ["signs and rules", "rules in different places", "a rule story", "an activity notice", "public signs and rules"],
        ENGLISH_SOURCE_SECOND,
    ),
    unit(
        "english-6b-u3-festivals",
        "english",
        "second",
        "Unit 3 Festivals across cultures",
        ["festival foods", "festival activities", "festival celebrations", "festival experiences", "a festival poster"],
        ENGLISH_SOURCE_SECOND,
    ),
    unit(
        "english-6b-u4-weather",
        "english",
        "second",
        "Unit 4 Weather and our lives",
        ["weather reports", "seasonal activities", "extreme weather", "weather and travel", "weather in life"],
        ENGLISH_SOURCE_SECOND,
    ),
    unit(
        "english-6b-u5-green-neighbourhood",
        "english",
        "second",
        "Unit 5 Green neighbourhood",
        ["a green song", "green ideas", "a green city", "greener experiences", "an ideal green neighbourhood"],
        ENGLISH_SOURCE_SECOND,
    ),
    unit(
        "english-6b-u6-famous-people",
        "english",
        "second",
        "Unit 6 Famous people in history",
        ["world changers", "life savers", "great storytellers", "great minds", "famous people in history"],
        ENGLISH_SOURCE_SECOND,
    ),
]


CURRICULUM_META = {
    "grade": GRADE,
    "default_grade": GRADE,
    "available_grades": [GRADE],
    "grades": [
        {"value": "六年级", "status": "available", "note": "2024 年审定新版目录已核对"},
        {"value": "七年级", "status": "pending", "note": "目录核对中"},
        {"value": "八年级", "status": "pending", "note": "目录核对中"},
        {"value": "九年级", "status": "pending", "note": "需区分学校使用的英语版本"},
    ],
    "edition_note": "六年级数学、英语使用依据 2022 年版课程标准修订并于 2024 年审定的五·四学制教材。",
    "scope_note": "仅使用公开教材目录和人工整理知识点，不存储教材正文。",
    "sources": [
        {
            "semester": "first",
            "label": "上海市教委 2025 年秋季中小学教学用书目录",
            "url": "https://edu.sh.gov.cn/cmsres/2d/2dc160ca4658483e8eaaf76e8f945637/28a7fabd94b936378d6dd4c271c12ad8.pdf",
        },
        {
            "semester": "second",
            "label": "上海市教委 2026 年春季中小学教学用书目录",
            "url": "https://edu.sh.gov.cn/cmsres/3a/3a555417ed2b47a38f730ca8c9f10881/9ba8430bf7e54d3e19fce9c17b45f5fb.pdf",
        },
    ],
}
