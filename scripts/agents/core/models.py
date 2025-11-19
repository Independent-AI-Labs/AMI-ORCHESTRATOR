"""Unified Pydantic models for LLM orchestration executors."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# Unified execution status
ExecutionStatus = Literal["completed", "feedback", "failed", "timeout"]


class UnifiedExecutionAttempt(BaseModel):
    """Unified execution attempt model replacing ExecutionAttempt, DocAttempt, AuditAttempt, TaskAttempt"""

    attempt_number: int
    worker_output: str
    moderator_output: str | None = None
    timestamp: datetime
    duration: float
    worker_metadata: dict[str, Any] | None = None
    moderator_metadata: dict[str, Any] | None = None


class UnifiedExecutionResult(BaseModel):
    """Unified execution result replacing ExecutionResult, StandardizedResult, DocResult, AuditResult, TaskResult"""

    # Core fields from base ExecutionResult
    item_path: Path
    status: ExecutionStatus
    attempts: list[UnifiedExecutionAttempt] = Field(default_factory=list)
    feedback: str | None = None
    total_duration: float = 0.0
    error: str | None = None

    # DocResult-specific field
    action: Literal["UPDATE", "ARCHIVE", "DELETE"] | None = None

    # AuditResult-specific fields
    violations: list[dict[str, Any]] = Field(default_factory=list)
    audit_execution_time: float = 0.0  # renamed from execution_time to avoid confusion

    # TaskResult-specific - no unique fields beyond what's already in base
    # Using generic metadata for executor-specific data
    executor_metadata: dict[str, Any] | None = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
