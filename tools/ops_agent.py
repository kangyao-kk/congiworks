from langchain.agents import create_agent
from langchain.tools import tool
from agent.llm import create_llm


@tool
def generate_content(topic: str, style: str = "专业") -> str:
    """根据主题和风格生成运营文案或内容。

    Args:
        topic: 内容主题
        style: 文案风格，如"专业"、"活泼"、"简洁"
    """
    llm = create_llm()
    prompt = f"请以{style}风格，围绕「{topic}」写一段运营文案。"
    return llm.invoke(prompt).content


@tool
def analyze_data(text: str) -> str:
    """分析给定的运营数据文本，提取关键指标和趋势。

    Args:
        text: 要分析的运营数据文本
    """
    llm = create_llm()
    prompt = f"请分析以下运营数据，提取关键指标、趋势和优化建议：\n\n{text}"
    return llm.invoke(prompt).content


@tool
def brainstorm_ideas(goal: str) -> str:
    """根据运营目标进行头脑风暴，生成创意方案。

    Args:
        goal: 运营目标，如"提升用户留存"、"增加社群活跃度"
    """
    llm = create_llm()
    prompt = f"针对「{goal}」这个运营目标，请提出5个创意方案，每个方案简要说明执行思路和预期效果。"
    return llm.invoke(prompt).content


def create_ops_agent():
    """创建运营 Agent，包含内容生成、数据分析和创意策划能力。"""
    llm = create_llm()
    tools = [generate_content, analyze_data, brainstorm_ideas]

    agent = create_agent(
        llm=llm,
        tools=tools,
        system_prompt="你是一个专业的运营助手，擅长内容创作、数据分析和创意策划。请根据用户需求选择合适的工具完成任务。",
    )
    return agent
