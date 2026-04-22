from typing import Union, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import Config

class UserIntent(BaseModel):
    ticker: str = Field(description="提取的美股代码，必须全大写，如 NVDA。如果用户输入的是公司名(如英伟达)，请转换为对应的股票代码。")
    investment_horizon: str = Field(description="投资周期，如：短期 (Short-term)、中期 (Medium-term)、长期 (Long-term)、未指定 (Unspecified)")
    user_concerns: Union[str, List[str]] = Field(description="用户核心关切点")
    sector: str = Field(description="股票所属的粗略板块，如 Technology, Financial Services, Healthcare 等。用于后续专家路由。")

def parse_user_input(user_text: str) -> dict:
    """
    将用户的自然语言输入转化为结构化的投研意图
    """
    # 意图解析不需要发散思维，temperature 设为 0 以保证稳定性
    llm = Config.get_llm(temperature=0.0) 
    
    # 强制 LLM 输出 UserIntent 结构
    structured_llm = llm.with_structured_output(UserIntent)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            "你是一个专业的投研助理。请从用户输入中提取简洁的意图。"
            "必须严格使用以下英文键名输出 JSON，严禁翻译键名：\n"
            "- ticker (股票代码，如 TSLA)\n"
            "- investment_horizon (投资期限)\n"
            "- user_concerns (核心关切)\n"
            "- sector (所属行业)\n"
            "确保输出为标准的 JSON 格式。"
        ),
        ("human", "客户委托内容：{text}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        # 执行解析并转换为字典格式返回
        result = chain.invoke({"text": user_text})
        return result.model_dump()
    except Exception as e:
        print(f"意图解析失败: {e}")
        # 提供一个 Fallback 兜底逻辑
        return {
            "ticker": "UNKNOWN",
            "investment_horizon": "Unspecified",
            "user_concerns": "",
            "sector": "Unknown"
        }