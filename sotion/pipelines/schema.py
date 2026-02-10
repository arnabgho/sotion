"""Pipeline YAML schema validation."""

from typing import Any

from pydantic import BaseModel, Field


class PipelineStep(BaseModel):
    """A single step in a pipeline."""
    name: str
    agent_role: str  # 'developer', 'reviewer', 'planner', etc.
    prompt: str  # Template string with {context} placeholders
    timeout_seconds: int = 300
    retry_count: int = 1
    requires_approval: bool = False  # Human must approve before proceeding


class PipelineDefinition(BaseModel):
    """A declarative pipeline definition."""
    name: str
    description: str = ""
    steps: list[PipelineStep]
    context: dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """A running instance of a pipeline."""
    id: str
    pipeline_name: str
    channel_id: str
    current_step: int = 0
    status: str = "running"  # 'running', 'paused', 'completed', 'failed'
    context: dict[str, Any] = Field(default_factory=dict)
    step_results: list[dict[str, Any]] = Field(default_factory=list)


def validate_pipeline_yaml(data: dict[str, Any]) -> PipelineDefinition:
    """Validate a pipeline YAML dict and return a PipelineDefinition."""
    return PipelineDefinition(**data)
