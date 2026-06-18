"""Skill 基类 — 所有技能必须继承此类。"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Agent 技能基类。

    每个技能需定义:
        name:        技能名 (英文, 唯一标识)
        description: 技能描述 (LLM 据此判断何时调用)
        tool_spec:   返回 OpenAI Function Calling 格式的工具定义
        execute:     执行技能, 接收 LLM 传来的参数, 返回结果字符串
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def tool_spec(self) -> dict:
        """返回 OpenAI tool 定义, 用于 bind_tools。"""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """执行技能, kwargs 由 LLM function call 传入。"""
        ...

    def __repr__(self) -> str:
        return f"<Skill name={self.name!r}>"
