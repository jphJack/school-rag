"""索引模块 - 文本分块、向量嵌入、向量存储、元数据管理

处理流程:
1. ParsedDocument → 文本分块(chunker) → 多个文本片段
2. 文本片段 → BGE嵌入(embedder) → 向量
3. 向量 + 元数据 → Chroma向量库(vector_store)
4. 元数据 → SQLite(metadata_store)
"""
from indexer.chunker import TextChunker, Chunk
from indexer.embedder import Embedder
from indexer.vector_store import VectorStore
from indexer.metadata_store import MetadataStore

__all__ = ["TextChunker", "Chunk", "Embedder", "VectorStore", "MetadataStore"]
