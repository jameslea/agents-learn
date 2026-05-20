from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError


class ArtifactValidationResult(BaseModel):
    """一次 artifact schema 校验结果。"""

    artifact_id: str = Field(description="被校验的 artifact id。")
    schema_name: str = Field(description="用于校验的 schema 名称。")
    valid: bool = Field(description="payload 是否通过 schema 校验。")
    errors: list[str] = Field(default_factory=list, description="失败原因列表。")

class ArtifactValidationError(ValueError):
    """artifact 不存在、schema 不匹配或 payload 校验失败时抛出。"""

    def __init__(self, result: ArtifactValidationResult):
        self.result = result
        super().__init__(f"Artifact validation failed: {result.artifact_id}: {result.errors}")

def _format_validation_errors(exc: ValidationError) -> list[str]:
    errors: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", ())) or "<root>"
        errors.append(f"{loc}: {item.get('msg', 'validation error')}")
    return errors
