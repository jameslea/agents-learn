from __future__ import annotations

from typing import Any

from runtime_core.memory.query import MemoryQuery, MemorySearchResult
from runtime_core.memory.record import MemoryRecord, MemoryStatus, utc_now
from runtime_core.memory.rules.scoring import _normalize_tags, _score_memory


class MemoryStore:
    """最小内存记忆库。

    它只覆盖记忆系统的主要机制：写入、验证、检索、排序、失效。
    本阶段不负责持久化、向量检索、多用户隔离或自动记忆抽取。
    所有记录保存在当前 Python 进程内，进程退出后会丢失。
    """

    def __init__(self, records: list[MemoryRecord] | None = None) -> None:
        # 阶段 2 使用内存字典作为最小 store，重点验证记忆生命周期和检索机制。
        # 后续如果需要持久化，可以在不改变 MemoryRecord 的前提下替换为
        # JSON / SQLite / database-backed store。
        self._records: dict[str, MemoryRecord] = {}
        for record in records or []:
            self.add(record)

    def add(self, record: MemoryRecord, *, overwrite: bool = False) -> MemoryRecord:
        """写入一条记忆。默认不允许覆盖同 ID 记录。"""
        if record.memory_id in self._records and not overwrite:
            raise KeyError(f"Memory already exists: {record.memory_id}")
        self._records[record.memory_id] = record
        return record

    def propose(
        self,
        *,
        memory_id: str,
        content: str,
        source: str,
        scope: str = "global",
        tags: list[str] | None = None,
        confidence: float = 0.5,
        sensitive: bool = False,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """提出一条待验证记忆。

        propose 用于模拟 Agent 从任务中发现“可能可复用”的经验。它默认
        `validated=False`，避免未审核内容直接污染上下文。
        """
        return self.add(
            MemoryRecord(
                memory_id=memory_id,
                content=content,
                scope=scope,
                tags=tags or [],
                confidence=confidence,
                validated=False,
                source=source,
                sensitive=sensitive,
                expires_at=expires_at,
                metadata=metadata or {},
            )
        )

    def get(self, memory_id: str) -> MemoryRecord:
        """读取一条记忆。"""
        try:
            return self._records[memory_id]
        except KeyError as exc:
            raise KeyError(f"Memory not found: {memory_id}") from exc

    def validate(
        self,
        memory_id: str,
        *,
        confidence: float | None = None,
        source: str | None = None,
    ) -> MemoryRecord:
        """将一条记忆标记为已验证。"""
        record = self.get(memory_id)
        record.validated = True
        if confidence is not None:
            record.confidence = confidence
        if source is not None:
            record.source = source
        record.updated_at = utc_now()
        return record

    def invalidate(self, memory_id: str, *, reason: str) -> MemoryRecord:
        """将一条记忆失效。失效记忆默认不会进入检索结果。"""
        record = self.get(memory_id)
        record.status = MemoryStatus.INVALIDATED
        record.metadata["invalidated_reason"] = reason
        record.updated_at = utc_now()
        return record

    def replace(
        self,
        *,
        old_memory_id: str,
        new_record: MemoryRecord,
    ) -> MemoryRecord:
        """用新记忆替代旧记忆，并保留替代关系。"""
        old_record = self.invalidate(old_memory_id, reason=f"replaced_by:{new_record.memory_id}")
        new_record.version = old_record.version + 1
        if old_memory_id not in new_record.supersedes:
            new_record.supersedes.append(old_memory_id)
        new_record.updated_at = utc_now()
        return self.add(new_record)

    def list_records(self, *, include_inactive: bool = False) -> list[MemoryRecord]:
        """列出记忆。默认只返回 active 记忆。"""
        records = list(self._records.values())
        if include_inactive:
            return records
        return [record for record in records if record.status == MemoryStatus.ACTIVE]

    def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """按 scope、tag、置信度、验证状态和有效期检索记忆。"""
        results: list[MemorySearchResult] = []
        query_tags = _normalize_tags(query.tags)
        query_scopes = set(query.scopes)

        for record in self._records.values():
            # 先做治理过滤，再算相关性分数。这样未验证、过期、敏感、
            # inactive 或 scope 不匹配的记忆不会因为 tag 命中而进入上下文。
            included, reason = self._can_return(record, query=query, query_scopes=query_scopes)
            if not included:
                continue
            score = _score_memory(record, query_tags=query_tags)
            if query_tags and score <= 0:
                continue
            results.append(MemorySearchResult(record=record, score=score, reason=reason))

        results.sort(key=lambda item: (item.score, item.record.updated_at), reverse=True)
        return results[: query.limit]

    def _can_return(
        self,
        record: MemoryRecord,
        *,
        query: MemoryQuery,
        query_scopes: set[str],
    ) -> tuple[bool, str]:
        if record.status != MemoryStatus.ACTIVE and not query.include_inactive:
            return False, "memory 非 active 状态。"
        if record.scope not in query_scopes:
            return False, "memory scope 不匹配。"
        if record.sensitive and not query.include_sensitive:
            return False, "memory 标记为 sensitive。"
        if not record.validated and not query.include_unvalidated:
            return False, "memory 未验证。"
        if record.confidence < query.min_confidence:
            return False, "memory 置信度低于检索阈值。"
        if record.is_expired() and not query.include_expired:
            return False, "memory 已过期。"
        return True, "memory 通过 scope、tag、验证状态、置信度和有效期检索。"
