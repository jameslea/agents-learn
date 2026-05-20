from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ValidationError

from runtime_core.artifact.record import ArtifactRecord
from runtime_core.artifact.validation import (
    ArtifactValidationError,
    ArtifactValidationResult,
    _format_validation_errors,
)


class ArtifactStore:
    """内存版 Schema Artifact Store。

    主要职责：
    - 注册 schema 名称和 Pydantic 模型的对应关系。
    - 保存 ArtifactRecord 前校验 payload。
    - 下游读取 artifact 时再次校验 schema 和 validated 状态。
    """

    def __init__(
        self,
        records: Iterable[ArtifactRecord] | None = None,
        schemas: dict[str, type[BaseModel]] | None = None,
    ) -> None:
        self._records: dict[str, ArtifactRecord] = {}
        self._schemas: dict[str, type[BaseModel]] = {}
        if schemas:
            self._schemas.update(schemas)
        for record in records or []:
            self.save(record)

    def register_schema(self, schema_name: str, schema_model: type[BaseModel]) -> None:
        """注册一个 schema 名称，供后续保存和读取时校验。"""
        self._schemas[schema_name] = schema_model

    def save(self, record: ArtifactRecord, *, validate: bool = True) -> ArtifactRecord:
        """保存 artifact。

        validate=True 时，payload 必须符合 record.schema_name 对应的 Pydantic
        模型，否则抛出 ArtifactValidationError，避免无效产物进入交接链路。
        """
        if validate:
            result = self.validate(record)
            if not result.valid:
                raise ArtifactValidationError(result)
            record.validated = True
            record.metadata = {**record.metadata, "validation_errors": []}
        self._records[record.artifact_id] = record
        return record

    def save_model(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        title: str,
        summary: str,
        schema_name: str,
        model: BaseModel,
        producer_step_id: str = "",
        tags: list[str] | None = None,
        path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        """把已通过 Pydantic 构造的 schema model 保存为 ArtifactRecord。"""
        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            title=title,
            summary=summary,
            path=path,
            schema_name=schema_name,
            producer_step_id=producer_step_id,
            tags=tags or [],
            payload=model.model_dump(mode="json"),
            metadata=metadata or {},
        )
        return self.save(record)

    def get(
        self,
        artifact_id: str,
        *,
        expected_schema_name: str | None = None,
        require_validated: bool = True,
    ) -> ArtifactRecord:
        """读取 artifact，并检查 schema 与 validated 状态。"""
        if artifact_id not in self._records:
            raise KeyError(f"Artifact not found: {artifact_id}")
        record = self._records[artifact_id]
        errors: list[str] = []
        if expected_schema_name and record.schema_name != expected_schema_name:
            errors.append(f"schema mismatch: expected {expected_schema_name}, got {record.schema_name}")
        if require_validated and not record.validated:
            errors.append("artifact is not validated")
        if errors:
            raise ArtifactValidationError(
                ArtifactValidationResult(
                    artifact_id=record.artifact_id,
                    schema_name=expected_schema_name or record.schema_name,
                    valid=False,
                    errors=errors,
                )
            )
        return record

    def load_payload(self, artifact_id: str, *, schema_name: str) -> BaseModel:
        """读取 artifact payload，并返回对应的 Pydantic schema 实例。"""
        record = self.get(artifact_id, expected_schema_name=schema_name)
        result = self.validate(record)
        if not result.valid:
            raise ArtifactValidationError(result)
        return self._schemas[schema_name].model_validate(record.payload)

    def validate(self, record: ArtifactRecord) -> ArtifactValidationResult:
        """校验 record.payload 是否满足 record.schema_name。"""
        schema_model = self._schemas.get(record.schema_name)
        if not schema_model:
            return ArtifactValidationResult(
                artifact_id=record.artifact_id,
                schema_name=record.schema_name,
                valid=False,
                errors=[f"unknown schema: {record.schema_name}"],
            )
        try:
            schema_model.model_validate(record.payload)
        except ValidationError as exc:
            return ArtifactValidationResult(
                artifact_id=record.artifact_id,
                schema_name=record.schema_name,
                valid=False,
                errors=_format_validation_errors(exc),
            )
        return ArtifactValidationResult(
            artifact_id=record.artifact_id,
            schema_name=record.schema_name,
            valid=True,
        )

    def list_records(self) -> list[ArtifactRecord]:
        """按插入顺序返回当前 store 中的 artifact。"""
        return list(self._records.values())
