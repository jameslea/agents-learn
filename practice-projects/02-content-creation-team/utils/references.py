import re

from sop_artifacts import DraftContent
from utils.url_utils import unique_urls


REFERENCE_HEADING = "## 参考资料"
BARE_URL_RE = re.compile(r"^(?:[-*]\s*)?(https?://\S+)\s*$")


def parse_reference_urls(markdown: str) -> dict[int, str]:
    """解析形如 '[1] https://example.com' 的参考资料条目。"""
    references: dict[int, str] = {}
    for match in re.finditer(r"^\[(\d+)\]\s+(\S+)\s*$", markdown, re.MULTILINE):
        references[int(match.group(1))] = match.group(2)
    return references


def normalize_draft_references(draft: DraftContent) -> DraftContent:
    """移除未使用参考资料，按正文引用顺序连续重编号，并同步 citations。"""
    content = draft.content_markdown
    if REFERENCE_HEADING not in content:
        return draft

    body, reference_section = content.split(REFERENCE_HEADING, 1)
    cited_numbers = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    if not cited_numbers:
        return draft

    existing_references = _parse_reference_section(reference_section)
    used_numbers = [number for number in sorted(cited_numbers) if number in existing_references]
    number_mapping = {
        old_number: new_number
        for new_number, old_number in enumerate(used_numbers, 1)
    }

    normalized_body = _renumber_body_citations(body, number_mapping)
    kept_urls: list[str] = []
    kept_reference_lines: list[str] = []
    for old_number in used_numbers:
        new_number = number_mapping[old_number]
        url = existing_references[old_number]
        kept_reference_lines.append(f"[{new_number}] {url}")
        kept_urls.append(url)

    if not kept_reference_lines:
        return draft

    normalized_content = (
        normalized_body.rstrip()
        + "\n\n"
        + REFERENCE_HEADING
        + "\n"
        + "\n".join(kept_reference_lines)
    )
    return draft.model_copy(
        update={
            "content_markdown": normalized_content,
            "citations": unique_urls(kept_urls),
        }
    )


def _parse_reference_section(reference_section: str) -> dict[int, str]:
    """解析参考资料章节中的编号和 URL；裸 URL 会按出现顺序补编号。"""
    existing_references: dict[int, str] = {}
    next_number = 1
    for line in reference_section.splitlines():
        stripped = line.strip()
        numbered_match = re.match(r"^\[(\d+)\]\s+(\S+)\s*$", stripped)
        if numbered_match:
            number = int(numbered_match.group(1))
            existing_references[number] = numbered_match.group(2)
            next_number = max(next_number, number + 1)
            continue

        bare_url_match = BARE_URL_RE.match(stripped)
        if bare_url_match:
            while next_number in existing_references:
                next_number += 1
            existing_references[next_number] = bare_url_match.group(1)
            next_number += 1
    return existing_references


def _renumber_body_citations(body: str, number_mapping: dict[int, int]) -> str:
    """按新编号替换正文中的引用标记。"""
    def replace_citation(match: re.Match[str]) -> str:
        old_number = int(match.group(1))
        if old_number not in number_mapping:
            return match.group(0)
        return f"[{number_mapping[old_number]}]"

    return re.sub(r"\[(\d+)\]", replace_citation, body)
