"""Pipeline execution engine."""

import asyncio
import uuid
from typing import Any, TYPE_CHECKING

from loguru import logger

from sotion.pipelines.schema import PipelineDefinition, PipelineRun

if TYPE_CHECKING:
    from sotion.orchestrator import SotionOrchestrator


class PipelineEngine:
    """
    Executes declarative pipelines step by step.

    Each step is claimed by an agent with the matching role,
    context is passed between steps, and retries are supported.
    """

    def __init__(self, orchestrator: "SotionOrchestrator"):
        self.orchestrator = orchestrator
        self.active_runs: dict[str, PipelineRun] = {}

    async def start_pipeline(
        self,
        definition: PipelineDefinition,
        channel_id: str,
        initial_context: dict[str, Any] | None = None,
    ) -> PipelineRun:
        """Start a new pipeline run."""
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_name=definition.name,
            channel_id=channel_id,
            context=initial_context or {},
        )
        self.active_runs[run.id] = run

        logger.info(f"Starting pipeline '{definition.name}' (run: {run.id})")

        # Execute steps sequentially
        for i, step in enumerate(definition.steps):
            run.current_step = i
            logger.info(f"Pipeline step {i+1}/{len(definition.steps)}: {step.name}")

            # Find an agent with the matching role
            agent_name = self._find_agent_for_role(step.agent_role)
            if not agent_name:
                run.status = "failed"
                run.step_results.append({
                    "step": step.name,
                    "status": "failed",
                    "error": f"No agent with role '{step.agent_role}' available",
                })
                logger.error(f"No agent for role '{step.agent_role}'")
                break

            # Build the prompt with context
            prompt = step.prompt.format(**run.context)

            # Execute with retry
            result = None
            for attempt in range(step.retry_count + 1):
                try:
                    from sotion.bus.events import InboundMessage

                    msg = InboundMessage(
                        channel="pipeline",
                        sender_id="pipeline",
                        chat_id=channel_id,
                        content=f"[Pipeline: {definition.name}, Step: {step.name}]\n\n{prompt}",
                        message_type="chat",
                        mentions=[agent_name],
                    )
                    responses = await asyncio.wait_for(
                        self.orchestrator.process_message(msg),
                        timeout=step.timeout_seconds,
                    )
                    if responses:
                        result = responses[0].content
                        break
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Step '{step.name}' timed out (attempt {attempt+1})"
                    )
                except Exception as e:
                    logger.error(
                        f"Step '{step.name}' failed (attempt {attempt+1}): {e}"
                    )

            step_result = {
                "step": step.name,
                "agent": agent_name,
                "status": "completed" if result else "failed",
                "output": result,
            }
            run.step_results.append(step_result)

            if not result:
                run.status = "failed"
                break

            # Pass result to context for next step
            run.context[f"step_{i}_output"] = result
            run.context["last_output"] = result

        else:
            run.status = "completed"

        logger.info(
            f"Pipeline '{definition.name}' {run.status} "
            f"({len(run.step_results)} steps)"
        )
        return run

    def _find_agent_for_role(self, role: str) -> str | None:
        """Find an agent with the given role."""
        for name, config in self.orchestrator.agent_configs.items():
            if config.role == role and name in self.orchestrator.agents:
                return name
        return None

    def get_run(self, run_id: str) -> PipelineRun | None:
        return self.active_runs.get(run_id)
