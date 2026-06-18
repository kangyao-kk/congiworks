"""Demo Skill — 文本分析工具。

展示 Skill 系统的完整操作方式:
    1. 继承 BaseSkill
    2. 定义 tool_spec() → OpenAI Function Calling 格式
    3. 实现 execute() → 接收参数, 返回结果
    4. 在模块级别创建实例 → SkillRegistry 自动发现
"""

import re
from skills.base import BaseSkill


class TextToolsSkill(BaseSkill):
    name = "text_tools"
    description = "文本分析工具: 统计字数词数、估算阅读时间、提取关键词"

    def tool_spec(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "text_tools",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["word_count", "reading_time", "keywords", "all"],
                            "description": "操作类型: word_count=字词统计, reading_time=阅读时间, keywords=关键词提取, all=全部",
                        },
                        "text": {
                            "type": "string",
                            "description": "要分析的文本内容",
                        },
                    },
                    "required": ["action", "text"],
                },
            },
        }

    def execute(self, action: str = "all", text: str = "", **kwargs) -> str:
        if action == "word_count":
            return self._word_count(text)
        elif action == "reading_time":
            return self._reading_time(text)
        elif action == "keywords":
            return self._keywords(text)
        else:
            return "\n".join([
                self._word_count(text),
                self._reading_time(text),
                self._keywords(text),
            ])

    # ── private ──────────────────────────────────────────────────────────

    def _word_count(self, text: str) -> str:
        chars = len(text.replace("\n", "").replace(" ", ""))
        chinese = len(re.findall(r"[一-鿿]", text))
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        return f"字词统计: 总字符({chars}), 中文字({chinese}), 英文词({english_words})"

    def _reading_time(self, text: str) -> str:
        # 中文约 300 字/分钟, 英文约 200 词/分钟
        chinese = len(re.findall(r"[一-鿿]", text))
        english = len(re.findall(r"[a-zA-Z]+", text))
        minutes = max(1, round(chinese / 300 + english / 200))
        return f"预计阅读时间: ~{minutes} 分钟"

    def _keywords(self, text: str) -> str:
        # 简单的关键词提取 (基于词频)
        # 提取 2-4 字的中文短语
        words = re.findall(r"[一-鿿]{2,4}", text)
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:8]
        kw_str = ", ".join(f"{w}({c})" for w, c in top)
        return f"高频关键词: {kw_str}"


# ── 模块级实例 (SkillRegistry 会自动发现) ──────────────────────────────────
DEMO_SKILL = TextToolsSkill()
