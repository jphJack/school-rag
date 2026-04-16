"""依赖注入 - 数据库会话、RAG Chain实例"""

import os

from loguru import logger

# 离线模式环境变量（在import前设置）
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from rag.chain import RAGChain
from indexer.vector_store import VectorStore
from indexer.metadata_store import MetadataStore


# 全局单例（懒加载）
_rag_chain: RAGChain = None
_vector_store: VectorStore = None
_metadata_store: MetadataStore = None


def get_rag_chain() -> RAGChain:
    """获取RAGChain单例"""
    global _rag_chain
    if _rag_chain is None:
        logger.info("初始化RAGChain...")
        _rag_chain = RAGChain()
    return _rag_chain


def get_vector_store() -> VectorStore:
    """获取VectorStore单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_metadata_store() -> MetadataStore:
    """获取MetadataStore单例"""
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = MetadataStore()
    return _metadata_store
