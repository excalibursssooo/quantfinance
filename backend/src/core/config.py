# src/core/config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5-flash") # 设个缺省值
    OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/quant_agent")
    
    @classmethod
    def get_llm(cls, temperature=0.0, model_name="qwen3.5-flash", streaming=False):
        """
        动态获取 LLM 实例，支持模型路由和流式输出
        """
        if not cls.OPENAI_API_KEY:
            raise ValueError("未找到 OPENAI_API_KEY，请检查环境变量。")
        
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "openai_api_key": cls.OPENAI_API_KEY,
            "streaming": streaming # 开启流式输出
        }
        if cls.OPENAI_API_BASE_URL:
            kwargs["openai_api_base"] = cls.OPENAI_API_BASE_URL
            
        return ChatOpenAI(**kwargs)

config = Config()