import re
from typing import Optional

KEYWORD_PATTERNS = {
    "exam": [
        r"真题", r"考题", r"题目", r"练习", r"选择题", r"填空.*题",
        r"计算.*题", r"解答.*题", r"试卷", r"第.*[题问]",
        r"\d+[\.、].*[A-D]", r"[A-D][\.、]", r"习题", r"怎么做",
        r"选.*正确", r"选.*错误", r"下列.*正确", r"下列.*错误",
    ],
    "note": [
        r"心得", r"笔记", r"总结", r"分享", r"经验",
        r"学习.*[方法感悟]", r"[如何怎么怎样].*[学复]习",
        r"复习.*计划", r"备考", r"学习.*建议",
    ],
}

META_PATTERNS = [
    r"(你|这个|当前)(用|使用|是|基于|采用)什么(模型|引擎|架构)",
    r"你(是|叫什么|是什么|用的|基于)",
    r"(你|这个)(助手|系统|AI|机器人|聊天)",
    r"(这个|你).*(模型|版本|能力|功能|能做什么)",
    r"什么(模型|版本|引擎|AI|LLM|大模型)",
    r"你是谁",
    r"(介绍|说明).*(你自己|自身|这个系统)",
    r"你.*(底层|背后|技术栈|开发|搭建)",
]


def is_meta_question(question: str) -> bool:
    for p in META_PATTERNS:
        if re.search(p, question):
            return True
    return False


def is_model_identity_question(question: str) -> bool:
    """Return whether the user is asking which configured model serves Q&A."""
    normalized = re.sub(r"\s+", "", question).lower()
    if not any(keyword in normalized for keyword in ("模型", "版本", "deepseek", "大模型", "llm")):
        return False
    return any(keyword in normalized for keyword in (
        "你现在", "你是", "你用", "你使用", "当前", "这个系统", "这个助手",
    ))


def detect_intent(question: str) -> str:
    for intent, patterns in KEYWORD_PATTERNS.items():
        for p in patterns:
            if re.search(p, question):
                return intent
    return "knowledge"
