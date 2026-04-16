"""搜索接口 - 核心搜索功能

接口:
- POST /api/search       - 搜索（检索+LLM生成摘要）
- POST /api/search/stream - 流式搜索（SSE）
- GET  /api/suggest      - 搜索建议（纯检索，快速）
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from loguru import logger

from api.schemas import (
    SearchRequest, SearchResponse, SuggestResponse,
    ResultItem, SourceItem,
)
from api.dependencies import get_rag_chain
from rag.chain import RAGChain
from rag.retriever import SearchResult

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    chain: RAGChain = Depends(get_rag_chain),
):
    """搜索接口 - 检索 + LLM生成摘要"""
    start_time = time.time()
    logger.info(f"搜索请求: query='{req.query[:30]}', top_k={req.top_k}, use_llm={req.use_llm}")

    try:
        if req.use_llm:
            # 完整RAG流程
            rag_resp = chain.ask(
                query=req.query,
                top_k=req.top_k,
                filter_site=req.filter_site,
                filter_type=req.filter_type,
            )
            total_ms = int((time.time() - start_time) * 1000)

            return SearchResponse(
                query=rag_resp.query,
                answer=rag_resp.answer,
                results=[_to_result_item(r) for r in rag_resp.results],
                sources=[SourceItem(**s) for s in rag_resp.sources],
                has_llm=rag_resp.has_llm,
                error=rag_resp.error,
                retrieve_time_ms=rag_resp.retrieve_time_ms,
                generate_time_ms=rag_resp.generate_time_ms,
                total_time_ms=total_ms,
            )
        else:
            # 仅检索
            return await _search_only(req, chain, start_time)

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        total_ms = int((time.time() - start_time) * 1000)
        return SearchResponse(
            query=req.query,
            error=str(e),
            total_time_ms=total_ms,
        )


@router.post("/search/stream")
async def search_stream(
    req: SearchRequest,
    chain: RAGChain = Depends(get_rag_chain),
):
    """流式搜索接口 - SSE (Server-Sent Events)

    返回text/event-stream格式的流式响应
    """
    logger.info(f"流式搜索请求: query='{req.query[:30]}'")

    def event_generator():
        try:
            for chunk in chain.ask_stream(
                query=req.query,
                top_k=req.top_k,
                filter_site=req.filter_site,
                filter_type=req.filter_type,
            ):
                # SSE格式: data: {content}\n\n
                import json
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # 发送结束标记
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            import json
            data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    q: str = Query(..., min_length=1, max_length=200, description="查询文本"),
    top_k: int = Query(default=5, ge=1, le=10, description="返回结果数"),
    chain: RAGChain = Depends(get_rag_chain),
):
    """搜索建议 - 纯检索，快速响应（不调用LLM）"""
    start_time = time.time()
    logger.info(f"搜索建议: q='{q[:30]}'")

    try:
        results = chain.search_only(query=q, top_k=top_k)
        retrieve_ms = int((time.time() - start_time) * 1000)

        return SuggestResponse(
            query=q,
            results=[_to_result_item(r) for r in results],
            retrieve_time_ms=retrieve_ms,
        )
    except Exception as e:
        logger.error(f"搜索建议失败: {e}")
        return SuggestResponse(query=q, retrieve_time_ms=0)


async def _search_only(req: SearchRequest, chain: RAGChain, start_time: float) -> SearchResponse:
    """仅检索模式（不调用LLM）"""
    results = chain.search_only(
        query=req.query,
        top_k=req.top_k,
        filter_site=req.filter_site,
        filter_type=req.filter_type,
    )
    retrieve_ms = int((time.time() - start_time) * 1000)

    # 收集来源
    seen_urls = set()
    sources = []
    for r in results:
        if r.source_url and r.source_url not in seen_urls:
            seen_urls.add(r.source_url)
            sources.append(SourceItem(
                url=r.source_url, title=r.title,
                site=r.source_site, type=r.content_type,
            ))

    return SearchResponse(
        query=req.query,
        results=[_to_result_item(r) for r in results],
        sources=sources,
        has_llm=False,
        retrieve_time_ms=retrieve_ms,
        total_time_ms=retrieve_ms,
    )


def _to_result_item(r: SearchResult) -> ResultItem:
    """SearchResult → ResultItem"""
    return ResultItem(
        text=r.text,
        source_url=r.source_url,
        source_site=r.source_site,
        title=r.title,
        content_type=r.content_type,
        publish_date=r.publish_date,
        score=r.score,
        doc_id=r.doc_id,
        chunk_index=r.chunk_index,
        total_chunks=r.total_chunks,
    )
