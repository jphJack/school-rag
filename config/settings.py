"""全局配置模块 - 读取环境变量并定义所有配置参数"""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"


class CrawlerSettings(BaseSettings):
    """爬虫配置"""
    crawl_delay: float = Field(default=2.0, alias="CRAWL_DELAY")
    crawl_depth: int = Field(default=2, alias="CRAWL_DEPTH")
    crawl_concurrent: int = Field(default=4, alias="CRAWL_CONCURRENT")
    crawl_robots_txt: bool = Field(default=True, alias="CRAWL_ROBOTS_TXT")
    crawl_user_agent: str = Field(
        default="SchoolRAG-Bot/1.0",
        alias="CRAWL_USER_AGENT",
    )
    raw_data_dir: str = Field(default=str(RAW_DATA_DIR), alias="RAW_DATA_DIR")

    class Config:
        env_file = ".env"
        extra = "ignore"


class LLMSettings(BaseSettings):
    """LLM配置"""
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    class Config:
        env_file = ".env"
        extra = "ignore"


class EmbeddingSettings(BaseSettings):
    """Embedding配置"""
    embedding_provider: str = Field(default="bge-local", alias="EMBEDDING_PROVIDER")
    bge_model_name: str = Field(default="BAAI/bge-large-zh-v1.5", alias="BGE_MODEL_NAME")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    class Config:
        env_file = ".env"
        extra = "ignore"


class VectorDBSettings(BaseSettings):
    """向量数据库配置"""
    chroma_persist_dir: str = Field(default=str(CHROMA_DIR), alias="CHROMA_PERSIST_DIR")

    class Config:
        env_file = ".env"
        extra = "ignore"


class APISettings(BaseSettings):
    """API服务配置"""
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")

    class Config:
        env_file = ".env"
        extra = "ignore"


class AppSettings(BaseSettings):
    """应用全局配置"""
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    metadata_db: str = Field(default=str(DATA_DIR / "metadata.db"), alias="METADATA_DB")

    crawler: CrawlerSettings = CrawlerSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    vector_db: VectorDBSettings = VectorDBSettings()
    api: APISettings = APISettings()

    class Config:
        env_file = ".env"
        extra = "ignore"


# 全局配置实例
settings = AppSettings()


def ensure_dirs():
    """确保所有必要目录存在"""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ["html", "pdf", "images", "other"]:
        (RAW_DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)
