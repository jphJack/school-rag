"""检索器 - 向量检索 + 元数据过滤 + 重排序

核心功能:
1. 接收用户查询，生成向量嵌入
2. 从Chroma向量库检索Top-K相似文档
3. 可选的元数据过滤（按站点、类型）
4. 结果去重（同一文档多个chunk只保留最相关的）
5. 返回结构化的SearchResult列表
"""
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from indexer.embedder import Embedder
from indexer.vector_store import VectorStore


@dataclass
class SearchResult:
    """检索结果条目"""
    # 文本内容
    text: str
    # 来源URL
    source_url: str
    # 来源站点
    source_site: str
    # 文档标题
    title: str
    # 内容类型(html/pdf等)
    content_type: str
    # 发布日期
    publish_date: str = ""
    # 相似度分数(0~1, 越高越相似)
    score: float = 0.0
    # 文档ID
    doc_id: str = ""
    # 分块序号
    chunk_index: int = 0
    # 总分块数
    total_chunks: int = 1

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source_url": self.source_url,
            "source_site": self.source_site,
            "title": self.title,
            "content_type": self.content_type,
            "publish_date": self.publish_date,
            "score": round(self.score, 4),
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }


class Retriever:
    """检索器 - 向量检索 + 结果去重 + 可选过滤"""

    def __init__(self, embedder: Optional[Embedder] = None,
                 vector_store: Optional[VectorStore] = None,
                 default_top_k: int = 8,
                 score_threshold: float = 0.3,
                 deduplicate: bool = True):
        """
        Args:
            embedder: 嵌入器实例
            vector_store: 向量库实例
            default_top_k: 默认返回结果数
            score_threshold: 相似度阈值(低于此值的结果被过滤)
            deduplicate: 是否按文档去重(同一文档只保留最相关的chunk)
        """
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()
        self.default_top_k = default_top_k
        self.score_threshold = score_threshold
        self.deduplicate = deduplicate

    def retrieve(self, query: str, top_k: Optional[int] = None,
                 filter_site: Optional[str] = None,
                 filter_type: Optional[str] = None) -> list[SearchResult]:
        """执行检索

        Args:
            query: 用户查询文本
            top_k: 返回结果数
            filter_site: 按来源站点过滤（如"教务部"）
            filter_type: 按内容类型过滤（如"pdf"）

        Returns:
            检索结果列表
        """
        top_k = top_k or self.default_top_k

        # 构建过滤条件
        filter_dict = None
        if filter_site or filter_type:
            filter_dict = {}
            if filter_site:
                filter_dict["source_site"] = filter_site
            if filter_type:
                filter_dict["content_type"] = filter_type

        # 查询嵌入
        # BGE推荐对查询添加指令前缀以提高检索效果
        query_text = f"为这个句子生成表示以用于检索相关文章：{query}"
        query_embedding = self.embedder.embed_query(query_text)

        # 向量检索（多取一些，去重后可能减少）
        search_k = top_k * 2 if self.deduplicate else top_k
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=search_k,
            filter_dict=filter_dict,
        )

        if not raw_results:
            logger.info(f"检索无结果: query='{query[:30]}'")
            return []

        # 转换为SearchResult
        results = []
        for item in raw_results:
            meta = item.get("metadata", {})
            # Chroma返回的是余弦距离，转为相似度分数
            distance = item.get("distance", 1.0)
            score = 1.0 - distance  # 余弦距离 → 相似度

            if score < self.score_threshold:
                continue

            result = SearchResult(
                text=item.get("text", ""),
                source_url=meta.get("source_url", ""),
                source_site=meta.get("source_site", ""),
                title=meta.get("title", ""),
                content_type=meta.get("content_type", ""),
                publish_date=meta.get("publish_date", ""),
                score=score,
                doc_id=meta.get("doc_id", ""),
                chunk_index=int(meta.get("chunk_index", 0)),
                total_chunks=int(meta.get("total_chunks", 1)),
            )
            results.append(result)

        # 按文档去重：同一文档只保留最相关的chunk
        if self.deduplicate and results:
            results = self._deduplicate(results)

        # 截取top_k
        results = results[:top_k]

        logger.info(
            f"检索完成: query='{query[:30]}', "
            f"原始={len(raw_results)}, 过滤后={len(results)}"
        )
        return results

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """按文档去重，同一doc_id只保留score最高的chunk"""
        seen_docs = {}
        for r in results:
            doc_id = r.doc_id
            if doc_id not in seen_docs or r.score > seen_docs[doc_id].score:
                seen_docs[doc_id] = r

        # 按score降序排列
        deduped = sorted(seen_docs.values(), key=lambda x: -x.score)
        return deduped
