# src/core/config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini") # 设个缺省值
    OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL")

    @classmethod
    def get_llm(cls, temperature=0.0):
        """统一提供 LLM 实例，杜绝到处写 API Key"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("未找到 OPENAI_API_KEY，请检查环境变量。")
        
        # 兼容第三方代理转发
        kwargs = {
            "model": cls.MODEL_NAME,
            "temperature": temperature,
            "openai_api_key": cls.OPENAI_API_KEY
        }
        if cls.OPENAI_API_BASE_URL:
            kwargs["openai_api_base"] = cls.OPENAI_API_BASE_URL
            
        return ChatOpenAI(**kwargs)

config = Config()