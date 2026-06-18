"""运营 Agent 入口 — 在 cmd 中运行，逐步展示 LangGraph 编排的执行过程。

用法:
    python main.py                        # 交互模式，逐轮对话
    python main.py "帮我分析用户留存"      # 单次查询
"""

import sys

# Windows cmd 默认用 GBK，强制 UTF-8 避免乱码和 UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage
from agent import create_ops_graph


def run_query(graph, user_input: str):
    """执行一次查询，stream 模式逐步展示每个节点的执行效果。"""
    print(f"\n{'=' * 60}")
    print(f"  Agency 代运营 Agent (LangGraph 编排)")
    print(f"{'=' * 60}")
    print(f"\n  DeepSeek 模型: deepseek-chat")
    print(f"  编排节点: analyze_intent → execute_tools ⇄ tools → synthesize")

    # stream_mode="updates": 每完成一个节点就 yield 该节点的输出
    for event in graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        stream_mode="updates",
    ):
        # event 是 {node_name: {state_updates}}
        pass  # 节点内部的 print 已经展示了详细输出

    print("  ✓ 执行完成\n")


def main():
    graph = create_ops_graph()

    if len(sys.argv) > 1:
        # 命令行传参模式
        user_input = " ".join(sys.argv[1:])
        run_query(graph, user_input)
    else:
        # 交互模式
        print(f"\n{'=' * 60}")
        print(f"  Agency 代运营 Agent — 交互模式")
        print(f"  输入 'exit' 或 Ctrl+C 退出")
        print(f"{'=' * 60}")

        graph = create_ops_graph()
        while True:
            try:
                user_input = input("\n你 > ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    print("  再见!")
                    break
                if not user_input:
                    continue
                run_query(graph, user_input)
            except KeyboardInterrupt:
                print("\n  再见!")
                break
            except Exception as e:
                print(f"  ✗ 执行出错: {e}")


if __name__ == "__main__":
    main()
