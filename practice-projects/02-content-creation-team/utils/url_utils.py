from collections.abc import Iterable
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """判断是否是普通 HTTP(S) URL。"""
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def unique_urls(urls: Iterable[str]) -> list[str]:
    """URL 去重并保留首次出现顺序。"""
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        normalized = url.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
