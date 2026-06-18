"""Skill Registry — 自动发现并注册所有技能。

用法:
    from skills import registry
    registry.load_all()
    tools = registry.get_tool_specs()   # 给 LLM bind_tools
    registry.execute("tool_name", **kwargs)  # 执行技能
"""

import os
import importlib
import pkgutil
from typing import Any

from skills.base import BaseSkill


class SkillRegistry:
    """技能注册中心 — 管理所有已加载的技能。"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}      # name → skill
        self._tool_map: dict[str, BaseSkill] = {}     # tool_name → skill

    def register(self, skill: BaseSkill):
        """注册一个技能。"""
        self._skills[skill.name] = skill
        spec = skill.tool_spec()
        tool_name = spec.get("function", {}).get("name", skill.name)
        self._tool_map[tool_name] = skill
        print(f"  [skills] 已加载: {skill.name} — {skill.description}")

    def load_all(self):
        """自动扫描 skills/ 目录, 加载所有技能。"""
        skill_dir = os.path.dirname(__file__)
        for _, name, is_pkg in pkgutil.iter_modules([skill_dir]):
            if name in ("base",):
                continue
            try:
                mod = importlib.import_module(f"skills.{name}")
                # 查找模块中的 skill 实例
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, BaseSkill) and obj.name:
                        self.register(obj)
            except Exception as e:
                print(f"  [skills] 加载 '{name}' 失败: {e}")

    def get_tool_specs(self) -> list[dict]:
        """返回所有技能的 OpenAI tool 定义列表。"""
        return [s.tool_spec() for s in self._skills.values()]

    def execute(self, tool_name: str, **kwargs: Any) -> str:
        """执行指定技能。"""
        skill = self._tool_map.get(tool_name)
        if not skill:
            return f"未知技能: {tool_name}"
        try:
            return skill.execute(**kwargs)
        except Exception as e:
            return f"技能 '{tool_name}' 执行失败: {e}"

    def list_skills(self) -> list[str]:
        return [f"{s.name}: {s.description}" for s in self._skills.values()]


# 全局单例
registry = SkillRegistry()
