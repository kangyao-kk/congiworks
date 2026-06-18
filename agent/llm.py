from langchain_deepseek import ChatDeepSeek
from agent.config import config


def create_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        model=config.DEEPSEEK_MODEL,
        temperature=0.7,
        extra_body={"thinking": {"type": "disabled"}},
    )
