"""Notification and search-style utility tool execution."""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from typing import Any, Iterable
import urllib.parse
import urllib.request

UTILITY_TOOL_NAMES = {
    "send_notification",
    "search_knowledge_base",
    "web_search",
    "web_extractor",
    "web_research",
    "search_assets_by_tag",
}


async def execute_utility_tool(
    tool_call_name: str,
    args: dict[str, Any],
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    if tool_call_name == "send_notification":
        return await _send_notification(args, log)
    if tool_call_name == "search_knowledge_base":
        return await _search_knowledge_base(args)
    if tool_call_name == "web_search":
        return await _web_search(args, log)
    if tool_call_name == "web_extractor":
        return await _web_extractor(args, log)
    if tool_call_name == "web_research":
        return await _web_research(args, log)
    if tool_call_name == "search_assets_by_tag":
        return await _search_assets_by_tag(args, log)
    return '{"error": "Unknown utility tool"}'


def filter_assets_by_tags(assets: Iterable[dict[str, Any]], tags_to_search: Iterable[str]) -> list[dict[str, Any]]:
    tags = list(tags_to_search)
    matched_assets = []
    for asset in assets:
        asset_tags = asset.get("tags", [])
        if all(tag in asset_tags for tag in tags):
            matched_assets.append(
                {
                    "id": asset.get("id"),
                    "host": asset.get("host"),
                    "port": asset.get("port"),
                    "username": asset.get("username"),
                    "asset_type": asset.get("asset_type"),
                    "protocol": asset.get("protocol"),
                    "remark": asset.get("remark"),
                    "tags": asset.get("tags"),
                }
            )
    return matched_assets


async def _send_notification(args: dict[str, Any], logger: logging.Logger) -> str:
    channel = args.get("channel", "auto")
    title = args.get("title")
    content = args.get("content")

    def do_notify():
        logger.info(f"AI 发起了群组通知 -> 渠道: {channel}, 标题: {title}")
        from core.notifier import send_notification

        result = send_notification(channel, title, content)
        return json.dumps(result)

    return await asyncio.to_thread(do_notify)


async def _search_knowledge_base(args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "知识库检索关键词不能为空。"}, ensure_ascii=False)

    try:
        from core.knowledge_base_service import build_vault_rag_context_for_prompt

        vault_result = await asyncio.to_thread(build_vault_rag_context_for_prompt, query, limit=5)
        context = str(vault_result.get("context") or "").strip()
        if context:
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "source": "vault",
                    "results": context,
                    "references": vault_result.get("references") or [],
                },
                ensure_ascii=False,
            )
    except Exception as exc:
        logging.getLogger(__name__).warning("vault knowledge lookup failed: %s", exc)

    try:
        from core.llm_factory import get_embedding_client_and_model
        from core.rag import kb_manager

        client, embedding_model = get_embedding_client_and_model()
        result = await asyncio.wait_for(
            kb_manager.search(query, client, embedding_model), timeout=60.0
        )
        return json.dumps({"status": "SUCCESS", "source": "vector", "results": result}, ensure_ascii=False)
    except asyncio.TimeoutError:
        return json.dumps({"error": "知识库检索超时被强制截断。"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"知识库检索异常: {str(e)}"}, ensure_ascii=False)


def _run_duckduckgo_search(query: str, logger: logging.Logger) -> list[dict[str, Any]]:
    import warnings

    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    logger.info(f"AI 发起了外网检索: {query}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5, backend="auto")]
            if not results:
                results = [r for r in ddgs.text(query, max_results=5, backend="html")]
            return results


def _strip_search_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def _run_bing_html_search(query: str, logger: logging.Logger) -> list[dict[str, str]]:
    logger.info(f"AI 使用 Bing HTML 兜底检索: {query}")
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 OpsCore"})
    with urllib.request.urlopen(request, timeout=15) as response:
        page = response.read(300000).decode("utf-8", errors="ignore")

    results: list[dict[str, str]] = []
    for match in re.finditer(r'<li class="b_algo".*?</li>', page, flags=re.I | re.S):
        block = match.group(0)
        link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not link_match:
            continue
        body_match = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.I | re.S)
        title = _strip_search_html(link_match.group(2))
        href = html.unescape(link_match.group(1))
        body = _strip_search_html(body_match.group(1)) if body_match else ""
        if title and href:
            results.append({"title": title, "href": href, "body": body})
        if len(results) >= 5:
            break
    return results


def _search_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36 OpsCore"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
        },
    )


def _normalize_result_url(href: str) -> str:
    return html.unescape(href).strip()


def _extract_html_results(page: str, block_pattern: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for match in re.finditer(block_pattern, page, flags=re.I | re.S):
        block = match.group(0)
        link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not link_match:
            continue
        body_match = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.I | re.S)
        if not body_match:
            body_match = re.search(r'<div[^>]+class="[^"]*(?:c-abstract|res-desc|mh-summary)[^"]*"[^>]*>(.*?)</div>', block, flags=re.I | re.S)
        title = _strip_search_html(link_match.group(2))
        href = _normalize_result_url(link_match.group(1))
        body = _strip_search_html(body_match.group(1)) if body_match else ""
        if title and href:
            results.append({"title": title, "href": href, "body": body})
        if len(results) >= 5:
            break
    return results


def _run_baidu_html_search(query: str, logger: logging.Logger) -> list[dict[str, str]]:
    logger.info(f"AI 使用百度 HTML 优先检索: {query}")
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    with urllib.request.urlopen(_search_request(url), timeout=15) as response:
        page = response.read(400000).decode("utf-8", errors="ignore")
    return _extract_html_results(page, r'<div[^>]+class="[^"]*(?:result|c-container)[^"]*"[^>]*>.*?</div>\s*</div>')


def _run_so360_html_search(query: str, logger: logging.Logger) -> list[dict[str, str]]:
    logger.info(f"AI 使用 360 搜索 HTML 优先检索: {query}")
    url = "https://www.so.com/s?q=" + urllib.parse.quote(query)
    with urllib.request.urlopen(_search_request(url), timeout=15) as response:
        page = response.read(400000).decode("utf-8", errors="ignore")
    return _extract_html_results(page, r'<li[^>]+class="[^"]*(?:res-list|result)[^"]*"[^>]*>.*?</li>')


def _run_china_html_search(query: str, logger: logging.Logger) -> list[dict[str, str]]:
    for provider in (_run_baidu_html_search, _run_so360_html_search):
        try:
            results = provider(query, logger)
        except Exception as exc:
            logger.warning("China search provider failed: %s", exc)
            continue
        if results:
            return results
    return []


def _query_prefers_china_search(query: str, args: dict[str, Any]) -> bool:
    region = str(args.get("region") or args.get("locale") or args.get("search_region") or "").lower()
    if region in {"cn", "zh", "zh-cn", "china", "中国", "国内"}:
        return True
    if re.search(r"[\u4e00-\u9fff]", query):
        return True
    china_terms = ("china", "chinese", "cn", "baidu", "360", "nanjing", "beijing", "shanghai", "guangzhou", "shenzhen")
    lowered = query.lower()
    return any(term in lowered for term in china_terms)


async def _web_search(args: dict[str, Any], logger: logging.Logger) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "联网搜索关键词不能为空。"}, ensure_ascii=False)
    try:
        from core.hermes_tool_adapter import execute_hermes_tool, hermes_tool_available

        hermes_ok, _ = hermes_tool_available("web_search")
        if hermes_ok:
            return await asyncio.wait_for(
                asyncio.to_thread(execute_hermes_tool, "web_search", args, {}),
                timeout=30.0,
            )
    except Exception as exc:
        logger.warning("Hermes web_search unavailable, falling back to OpsCore search: %s", exc)
    try:
        results = []
        if _query_prefers_china_search(query, args):
            results = await asyncio.wait_for(asyncio.to_thread(_run_china_html_search, query, logger), timeout=20.0)
        if not results:
            results = await asyncio.wait_for(asyncio.to_thread(_run_duckduckgo_search, query, logger), timeout=20.0)
        if not results:
            results = await asyncio.wait_for(asyncio.to_thread(_run_bing_html_search, query, logger), timeout=20.0)
        return json.dumps({"status": "SUCCESS", "results": results}, ensure_ascii=False)
    except asyncio.TimeoutError:
        return json.dumps({"error": "联网搜索超时，请稍后重试或换一个更具体的关键词。"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"外网检索异常: {str(e)}"}, ensure_ascii=False)


def _extract_urls_from_search_results(results: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        for key in ("href", "url", "link"):
            raw = item.get(key)
            if isinstance(raw, str):
                url = raw.strip()
                if url and url not in urls:
                    urls.append(url)
                break
    return urls


async def _web_extractor(args: dict[str, Any], logger: logging.Logger) -> str:
    urls = args.get("urls")
    if not isinstance(urls, list):
        single_url = args.get("url")
        if isinstance(single_url, str) and single_url.strip():
            urls = [single_url.strip()]
        else:
            urls = []
    normalized = [str(url).strip() for url in urls if str(url).strip()][:5]
    if not normalized:
        return json.dumps({"error": "web_extractor 需要 url 或 urls 参数。"}, ensure_ascii=False)

    try:
        from core.hermes_tool_adapter import execute_hermes_tool, hermes_tool_available

        hermes_ok, reason = hermes_tool_available("web_extract")
        if not hermes_ok:
            return json.dumps(
                {
                    "status": "ERROR",
                    "error": f"web_extract 不可用: {reason}",
                },
                ensure_ascii=False,
            )
        return await asyncio.wait_for(
            asyncio.to_thread(execute_hermes_tool, "web_extract", {"urls": normalized}, {}),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        logger.warning("web_extractor timeout for urls=%s", normalized)
        return json.dumps({"error": "web_extractor 超时，请减少 URL 数量或稍后重试。"}, ensure_ascii=False)
    except Exception as exc:
        logger.warning("web_extractor failed: %s", exc)
        return json.dumps({"error": f"web_extractor 异常: {type(exc).__name__}: {exc}"}, ensure_ascii=False)


async def _web_research(args: dict[str, Any], logger: logging.Logger) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "web_research 的 query 不能为空。"}, ensure_ascii=False)

    limit_raw = args.get("limit")
    try:
        limit = int(limit_raw) if limit_raw is not None else 5
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 10))

    search_result = await _web_search({"query": query, "limit": limit}, logger)
    try:
        search_payload = json.loads(search_result)
    except json.JSONDecodeError:
        search_payload = {"status": "ERROR", "error": "web_search 返回了不可解析内容。", "raw": search_result}

    results = search_payload.get("results") if isinstance(search_payload, dict) else None
    urls = _extract_urls_from_search_results(results if isinstance(results, list) else [])
    extract_payload: dict[str, Any]
    if urls:
        extract_result = await _web_extractor({"urls": urls[:2]}, logger)
        try:
            parsed_extract = json.loads(extract_result)
            extract_payload = parsed_extract if isinstance(parsed_extract, dict) else {"raw": extract_result}
        except json.JSONDecodeError:
            extract_payload = {"raw": extract_result}
    else:
        extract_payload = {"status": "SKIPPED", "reason": "搜索结果未提取到可用 URL。"}

    return json.dumps(
        {
            "status": "SUCCESS",
            "query": query,
            "search": search_payload,
            "extract": extract_payload,
        },
        ensure_ascii=False,
    )


async def _search_assets_by_tag(args: dict[str, Any], logger: logging.Logger) -> str:
    tags_to_search = args.get("tags", [])
    from core.memory import memory_db

    try:
        all_assets = await asyncio.to_thread(memory_db.get_all_assets)
        matched_assets = filter_assets_by_tags(all_assets, tags_to_search)
        logger.info(f"AI 发起了全局资产检索 tags={tags_to_search}, 匹配 {len(matched_assets)} 台")
        return json.dumps(
            {
                "status": "SUCCESS",
                "matched_count": len(matched_assets),
                "assets": matched_assets,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error(f"search_assets_by_tag 发生异常: {e}")
        return json.dumps({"error": f"全局检索异常: {str(e)}"})
