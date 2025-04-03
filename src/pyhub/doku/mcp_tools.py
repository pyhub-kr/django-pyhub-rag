from typing import Any

from asgiref.sync import sync_to_async

from pyhub.mcp import mcp

from .models import Document, VectorDocument


@mcp.tool()
async def similarity_search(query: str, k: int = 4) -> list[dict[str, Any]]:
    """Performs semantic similarity search on vector documents and returns top k matches."""
    qs = VectorDocument.objects.all()
    return await qs.similarity_search_async(query=query, k=k)


@mcp.resource("documents://", mime_type="application/json")
async def document_list() -> list[dict[str, Any]]:
    """MCP resource to get list of documents"""
    qs = Document.objects.all().values("id", "name", "status", "created_at")
    documents = await sync_to_async(list)(qs)
    return documents


@mcp.resource("vector-documents://", mime_type="application/json")
async def virtual_document_list() -> list[dict[str, Any]]:
    """MCP resource to get list of vector documents"""
    qs = VectorDocument.objects.all().values("id", "document__name", "created_at")
    documents = await sync_to_async(list)(qs)
    return documents


@mcp.resource("documents://{pk}")
async def document_jsonl(pk: int) -> str:
    """MCP resource to get JSONL data for a specific document"""
    doc: Document = await Document.objects.aget(pk=pk)
    return doc.to_jsonl()