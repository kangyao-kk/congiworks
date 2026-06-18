"""
Skill 系统演示 — LLM 自动判断并调用技能。

流程:
    用户提问 → LLM 判断是否需要调用工具
    → 需要: 生成 tool_call → registry.execute() → 结果喂回 LLM
    → 不需要: 直接回答

用法:
    python skills_demo.py
    python skills_demo.py "帮我统计这段话的字数: 今天天气真好，适合出去散步。"
"""

import sys, json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openai import OpenAI
from config import config
from skills import registry

# ── 加载技能 ──────────────────────────────────────────────────────────────────
registry.load_all()

tool_specs = registry.get_tool_specs()
print(f"\n已加载 {len(tool_specs)} 个技能:")
for t in tool_specs:
    fn = t["function"]
    print(f"  /{fn['name']} — {fn['description']}")

llm = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)


def chat_with_tools(user_input: str):
    """带工具调用的对话。"""
    messages = [
        {
            "role": "system",
            "content": "你是 Agency 助手。你可以调用 text_tools 技能来分析文本。"
            "如果用户要你统计字数、估算阅读时间或提取关键词，请调用工具。",
        },
        {"role": "user", "content": user_input},
    ]

    # ── 第一轮: LLM 决定是否调用工具 ──────────────────────────────────
    response = llm.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        tools=tool_specs,
        tool_choice="auto",
    )

    choice = response.choices[0]
    msg = choice.message

    if msg.tool_calls:
        print(f"\n  [LLM] 决定调用工具 ({len(msg.tool_calls)} 次)")

        # 把 LLM 的 tool_call 消息加入历史
        messages.append(msg.model_dump())

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)

            print(f"  [Tool] → {tool_name}")
            print(f"  [Args] → {json.dumps(tool_args, ensure_ascii=False)}")

            # 执行技能
            result = registry.execute(tool_name, **tool_args)

            print(f"  [Result] → {result}")

            # 把 tool 结果加入历史
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # ── 第二轮: LLM 根据工具结果生成最终回答 ──────────────────────
        print(f"\n  [LLM] 综合工具结果生成回答:\n")
        stream = llm.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                sys.stdout.write(chunk.choices[0].delta.content)
                sys.stdout.flush()
        print()

    else:
        # 不需要工具, 直接回答
        print(f"\n  [LLM] 无需工具, 直接回答:\n")
        print(msg.content)


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        chat_with_tools(" ".join(sys.argv[1:]))
    else:
        print("=" * 60)
        print("  Skill 调用演示")
        print("=" * 60)

        demos = [
            '帮我统计这段话的字数和阅读时间："人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。自然语言处理是人工智能领域的重要方向之一。"',
            '"今天天气真好" 这句话有多少字？',
            '提取这段话的关键词："深度学习通过构建多层神经网络来学习数据的表示，Transformer 架构基于自注意力机制。大语言模型如 GPT 和 Claude 拥有数百亿参数。"',
        ]

        for i, q in enumerate(demos, 1):
            print(f"\n{'=' * 60}")
            print(f"  Demo {i}")
            print(f"  用户: {q}")
            chat_with_tools(q)

        print(f"\n{'=' * 60}")
        print("  演示结束 — 你可以试试 python skills_demo.py 你的问题")
