"""非交互式媒体链接解析 CLI，供 agent skill 调用。

用法:
    python media_parser_cli.py "包含链接的文本"
    python media_parser_cli.py "text" --proxy http://127.0.0.1:7897
    python media_parser_cli.py "text" --no-download
    python media_parser_cli.py "text" --output-dir D:/media
    python media_parser_cli.py -f input.txt
    echo "text" | python media_parser_cli.py
    python media_parser_cli.py "text" --pretty
"""
import sys
import os
import json
import asyncio
import argparse
import logging
import importlib
import inspect
import pkgutil
from typing import List, Dict, Any, Optional, Type

import aiohttp

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from core.constants import Config
from core.parser import ParserManager
from core.parser.utils import format_duration_ms
from core.parser.platform.base import BaseVideoParser
from core.downloader import DownloadManager
from core.downloader.utils import check_cache_dir_available, strip_media_prefixes

from core.logger import logger as _plugin_logger

LOCAL_MEDIA_DIR = Config.build_cache_dir(_project_root)

PARSER_DISCOVERY_PACKAGE = "core.parser.platform"
PARSER_DISCOVERY_SKIP_MODULES = {"base", "short_video_shared"}
PARSER_DISCOVERY_ORDER = (
    "bilibili", "douyin", "tiktok", "kuaishou", "weibo",
    "xiaohongshu", "xianyu", "toutiao", "xiaoheihe", "twitter",
)
PARSER_DISCOVERY_ORDER_INDEX = {
    name: idx for idx, name in enumerate(PARSER_DISCOVERY_ORDER)
}


def _parser_order_key(parser_class: Type[BaseVideoParser]):
    module_name = parser_class.__module__.rsplit(".", 1)[-1]
    return (
        PARSER_DISCOVERY_ORDER_INDEX.get(module_name, len(PARSER_DISCOVERY_ORDER_INDEX)),
        module_name,
        parser_class.__name__,
    )


def discover_local_parser_classes() -> List[Type[BaseVideoParser]]:
    package = importlib.import_module(PARSER_DISCOVERY_PACKAGE)
    parser_classes = {}
    for module_info in pkgutil.iter_modules(package.__path__):
        short = module_info.name
        if module_info.ispkg or short.startswith("_") or short in PARSER_DISCOVERY_SKIP_MODULES:
            continue
        full = f"{package.__name__}.{short}"
        try:
            module = importlib.import_module(full)
        except Exception as e:
            _plugin_logger.warning(f"跳过解析器模块 {full}: {e}")
            continue
        for _, member in inspect.getmembers(module, inspect.isclass):
            if member is BaseVideoParser:
                continue
            if member.__module__ != module.__name__:
                continue
            if not issubclass(member, BaseVideoParser):
                continue
            if inspect.isabstract(member):
                continue
            parser_classes[f"{member.__module__}.{member.__name__}"] = member
    return sorted(parser_classes.values(), key=_parser_order_key)


def _build_parser_kwargs(
    parser_class: Type[BaseVideoParser],
    *,
    use_proxy: bool,
    proxy_url: Optional[str],
    cache_dir_available: bool,
    bilibili_cookie_runtime_file: str,
) -> Dict[str, Any]:
    effective_proxy = proxy_url if use_proxy and proxy_url else None
    local_values = {
        "cookie_runtime_enabled": cache_dir_available,
        "configured_cookie": "",
        "admin_assist_enabled": False,
        "credential_path": bilibili_cookie_runtime_file,
        "max_quality": 0,
        "hot_comment_count": 0,
        "use_proxy": bool(effective_proxy),
        "use_parse_proxy": bool(effective_proxy),
        "use_image_proxy": bool(effective_proxy),
        "use_video_proxy": bool(effective_proxy),
        "proxy_url": effective_proxy,
    }
    kwargs = {}
    missing = []
    for name, param in inspect.signature(parser_class).parameters.items():
        if name == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name in local_values:
            kwargs[name] = local_values[name]
        elif param.default is inspect.Parameter.empty:
            missing.append(name)
    if missing:
        raise TypeError(f"缺少自动实例化参数: {', '.join(missing)}")
    return kwargs


def create_parsers(
    *,
    use_proxy: bool,
    proxy_url: Optional[str],
    cache_dir_available: bool,
    bilibili_cookie_runtime_file: str,
) -> List[BaseVideoParser]:
    parsers = []
    for cls in discover_local_parser_classes():
        try:
            kwargs = _build_parser_kwargs(
                cls,
                use_proxy=use_proxy,
                proxy_url=proxy_url,
                cache_dir_available=cache_dir_available,
                bilibili_cookie_runtime_file=bilibili_cookie_runtime_file,
            )
            parser = cls(**kwargs)
        except Exception as e:
            _plugin_logger.warning(f"跳过解析器 {cls.__name__}: {e}")
            continue

        auth_runtime_getter = getattr(parser, "get_auth_runtime", None)
        if callable(auth_runtime_getter):
            try:
                auth_runtime = auth_runtime_getter()
                setattr(auth_runtime, "local_debug_mode", False)
            except Exception:
                pass
        parsers.append(parser)

    if not parsers:
        raise RuntimeError("未发现可用的平台解析器")
    return parsers


def _build_result_entry(
    metadata: Dict[str, Any],
    enable_download: bool,
) -> Dict[str, Any]:
    """将单条 metadata 转为 JSON 输出结构。"""
    if metadata.get("error"):
        return {
            "platform": metadata.get("platform", "unknown"),
            "url": metadata.get("url", metadata.get("source_url", "")),
            "title": None,
            "author": None,
            "desc": None,
            "timestamp": None,
            "videos": [],
            "images": [],
            "error": metadata["error"],
        }

    video_urls_raw = metadata.get("video_urls") or []
    image_urls_raw = metadata.get("image_urls") or []

    video_headers = metadata.get("video_headers") or {}

    videos = []
    if enable_download:
        video_modes = metadata.get("video_modes") or []
        video_sizes = metadata.get("video_sizes") or []
        video_skip_reasons = metadata.get("video_skip_reasons") or []
        video_status_codes = metadata.get("video_status_codes") or []
        file_paths = metadata.get("file_paths") or []
        video_count = metadata.get("video_count", len(video_urls_raw))

        for idx in range(video_count):
            url_list = video_urls_raw[idx] if idx < len(video_urls_raw) else []
            direct_url = strip_media_prefixes(url_list[0]) if url_list else None
            mode = video_modes[idx] if idx < len(video_modes) else "skip"
            size_mb = video_sizes[idx] if idx < len(video_sizes) else None
            skip_reason = video_skip_reasons[idx] if idx < len(video_skip_reasons) else None
            status_code = video_status_codes[idx] if idx < len(video_status_codes) else None
            file_path = file_paths[idx] if idx < len(file_paths) else None

            status = "success" if mode in ("local", "direct") else "skipped"
            entry = {
                "direct_url": direct_url,
                "file_path": file_path,
                "size_mb": round(size_mb, 2) if size_mb is not None else None,
                "mode": mode,
                "status": status,
                "status_code": status_code,
                "skip_reason": skip_reason,
            }
            if mode in ("direct", "skip"):
                entry["headers"] = video_headers
            videos.append(entry)
    else:
        for url_list in video_urls_raw:
            direct_url = strip_media_prefixes(url_list[0]) if url_list else None
            videos.append({
                "direct_url": direct_url,
                "file_path": None,
                "size_mb": None,
                "mode": "not_downloaded",
                "status": "not_downloaded",
                "status_code": None,
                "skip_reason": None,
                "headers": video_headers,
            })

    image_headers = metadata.get("image_headers") or {}

    images = []
    if enable_download:
        image_modes = metadata.get("image_modes") or []
        image_skip_reasons = metadata.get("image_skip_reasons") or []
        image_status_codes = metadata.get("image_status_codes") or []
        file_paths = metadata.get("file_paths") or []
        video_count = metadata.get("video_count", len(video_urls_raw))
        image_count = metadata.get("image_count", len(image_urls_raw))

        for idx in range(image_count):
            url_list = image_urls_raw[idx] if idx < len(image_urls_raw) else []
            direct_url = url_list[0] if url_list else None
            mode = image_modes[idx] if idx < len(image_modes) else "skip"
            skip_reason = image_skip_reasons[idx] if idx < len(image_skip_reasons) else None
            status_code = image_status_codes[idx] if idx < len(image_status_codes) else None
            file_path = file_paths[video_count + idx] if (video_count + idx) < len(file_paths) else None

            status = "success" if mode in ("local", "direct") else "skipped"
            entry = {
                "direct_url": direct_url,
                "file_path": file_path,
                "mode": mode,
                "status": status,
                "status_code": status_code,
                "skip_reason": skip_reason,
            }
            if mode in ("direct", "skip"):
                entry["headers"] = image_headers
            images.append(entry)
    else:
        for url_list in image_urls_raw:
            direct_url = url_list[0] if url_list else None
            images.append({
                "direct_url": direct_url,
                "file_path": None,
                "mode": "not_downloaded",
                "status": "not_downloaded",
                "status_code": None,
                "skip_reason": None,
                "headers": image_headers,
            })

    access_message = metadata.get("access_message")
    timelength_ms = metadata.get("timelength_ms")
    available_length_ms = metadata.get("available_length_ms")
    is_preview = metadata.get("is_preview_only")

    duration_info = None
    if access_message:
        duration_info = access_message
    elif is_preview and available_length_ms:
        full = format_duration_ms(timelength_ms) if timelength_ms else None
        avail = format_duration_ms(available_length_ms)
        duration_info = f"可解析 {avail}" + (f" / 全长 {full}" if full else "")
    elif timelength_ms:
        duration_info = format_duration_ms(timelength_ms)

    return {
        "platform": metadata.get("platform", "unknown"),
        "url": metadata.get("url", metadata.get("source_url", "")),
        "title": metadata.get("title"),
        "author": metadata.get("author"),
        "desc": metadata.get("desc"),
        "timestamp": metadata.get("timestamp"),
        "duration": duration_info,
        "videos": videos,
        "images": images,
        "error": None,
    }


async def run(
    text: str,
    *,
    proxy_url: Optional[str] = None,
    cache_dir: Optional[str] = None,
    enable_download: bool = True,
    debug: bool = False,
) -> Dict[str, Any]:
    """解析文本中的链接并可选下载媒体，返回 JSON 可序列化结果。"""
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        _plugin_logger.setLevel(logging.DEBUG)
    else:
        _plugin_logger.setLevel(logging.WARNING)

    if cache_dir is None:
        cache_dir = LOCAL_MEDIA_DIR
    cache_dir_available = check_cache_dir_available(cache_dir)

    bilibili_cookie_file = ""
    if cache_dir_available:
        bilibili_dir = Config.build_runtime_dir(cache_dir, "bilibili")
        os.makedirs(bilibili_dir, exist_ok=True)
        bilibili_cookie_file = os.path.join(bilibili_dir, "cookie.json")

    use_proxy = bool(proxy_url)
    parsers = create_parsers(
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        cache_dir_available=cache_dir_available,
        bilibili_cookie_runtime_file=bilibili_cookie_file,
    )
    parser_manager = ParserManager(parsers)

    download_manager = DownloadManager(
        max_video_size_mb=0.0,
        large_video_threshold_mb=0.0,
        cache_dir=cache_dir,
        cache_dir_available=cache_dir_available,
        max_concurrent_downloads=3,
    )

    timeout = aiohttp.ClientTimeout(total=Config.DEFAULT_TIMEOUT)
    connector = aiohttp.TCPConnector(
        limit=100, limit_per_host=10, ttl_dns_cache=300,
        force_close=False, enable_cleanup_closed=True,
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            links_with_parser = parser_manager.extract_all_links(text)
            if not links_with_parser:
                return {
                    "success": True,
                    "total_links": 0,
                    "results": [],
                    "summary": {
                        "total_links": 0,
                        "successful_parses": 0,
                        "failed_parses": 0,
                        "total_videos": 0,
                        "total_images": 0,
                        "downloaded_videos": 0,
                        "downloaded_images": 0,
                        "failed_downloads": 0,
                    },
                    "supported_platforms": [p.name for p in parsers],
                }

            metadata_list = await parser_manager.parse_text(
                text, session, links_with_parser=links_with_parser
            )

            if not metadata_list:
                return {
                    "success": False,
                    "error": "解析未返回任何结果",
                    "total_links": len(links_with_parser),
                    "results": [],
                    "summary": {
                        "total_links": len(links_with_parser),
                        "successful_parses": 0,
                        "failed_parses": len(links_with_parser),
                        "total_videos": 0,
                        "total_images": 0,
                        "downloaded_videos": 0,
                        "downloaded_images": 0,
                        "failed_downloads": 0,
                    },
                }

            processed_list = metadata_list
            if enable_download:
                processed_list = []
                for metadata in metadata_list:
                    if metadata.get("error"):
                        processed_list.append(metadata)
                        continue
                    try:
                        processed = await download_manager.process_metadata(
                            session, metadata, proxy_addr=proxy_url
                        )
                        processed_list.append(processed)
                    except Exception as e:
                        _plugin_logger.exception(f"下载处理失败: {metadata.get('url', '')}, {e}")
                        metadata["error"] = str(e)
                        processed_list.append(metadata)

            results = [_build_result_entry(m, enable_download) for m in processed_list]

            successful = sum(1 for r in results if not r.get("error"))
            failed = sum(1 for r in results if r.get("error"))
            total_videos = sum(len(r.get("videos", [])) for r in results)
            total_images = sum(len(r.get("images", [])) for r in results)
            dl_videos = sum(
                1 for r in results for v in r.get("videos", [])
                if v.get("status") == "success"
            )
            dl_images = sum(
                1 for r in results for v in r.get("images", [])
                if v.get("status") == "success"
            )
            failed_dl = sum(
                1 for r in results for v in r.get("videos", []) + r.get("images", [])
                if v.get("status") == "skipped"
            )

            return {
                "success": True,
                "total_links": len(links_with_parser),
                "results": results,
                "summary": {
                    "total_links": len(links_with_parser),
                    "successful_parses": successful,
                    "failed_parses": failed,
                    "total_videos": total_videos,
                    "total_images": total_images,
                    "downloaded_videos": dl_videos,
                    "downloaded_images": dl_images,
                    "failed_downloads": failed_dl,
                },
                "supported_platforms": [p.name for p in parsers],
            }
    finally:
        try:
            await download_manager.shutdown()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="流媒体平台链接解析工具 - 识别社交平台链接并提取/下载媒体"
    )
    parser.add_argument(
        "text", nargs="?", default=None,
        help="包含链接的文本（与 -f / stdin 三选一）",
    )
    parser.add_argument(
        "-f", "--file", default=None,
        help="从文件读取包含链接的文本",
    )
    parser.add_argument(
        "--proxy", default=None,
        help="代理地址，如 http://127.0.0.1:7897",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="媒体文件缓存目录（默认为插件目录下 cache/）",
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="仅解析链接提取元数据和直链，不下载媒体文件",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="格式化 JSON 输出（便于阅读）",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="启用 debug 日志",
    )
    args = parser.parse_args()

    # 确定输入文本
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    text = text.strip()
    if not text:
        print(json.dumps({"success": False, "error": "输入文本为空"}, ensure_ascii=False))
        sys.exit(1)

    cache_dir = args.output_dir if args.output_dir else None

    result = asyncio.run(run(
        text,
        proxy_url=args.proxy,
        cache_dir=cache_dir,
        enable_download=not args.no_download,
        debug=args.debug,
    ))

    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
