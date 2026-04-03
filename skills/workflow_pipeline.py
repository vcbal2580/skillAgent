"""
Lightweight workflow pipeline engine with dependency-aware step execution.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable


StepFn = Callable[[dict[str, Any]], Any]


@dataclass
class PipelineStep:
    """A single pipeline step."""

    name: str
    fn: StepFn
    depends_on: list[str] = field(default_factory=list)
    run_in_parallel: bool = False
    retry_count: int = 0
    timeout_seconds: float | None = None


class WorkflowPipeline:
    """Run a dependency-based pipeline and return final context."""

    def __init__(self, name: str, steps: list[PipelineStep]):
        self.name = name
        self.steps = steps
        self._step_map = {s.name: s for s in steps}
        if len(self._step_map) != len(steps):
            raise ValueError("Step names must be unique")

    def run(self, initial_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx: dict[str, Any] = dict(initial_ctx or {})
        executed: set[str] = set()
        ctx.setdefault("_pipeline_meta", {})

        while len(executed) < len(self.steps):
            ready = [
                step for step in self.steps
                if step.name not in executed and all(dep in executed for dep in step.depends_on)
            ]

            if not ready:
                missing = [
                    s.name for s in self.steps
                    if s.name not in executed
                ]
                raise RuntimeError(
                    f"Pipeline '{self.name}' cannot progress, unresolved dependencies: {missing}"
                )

            progressed = self._run_ready_steps(ctx, ready, executed)

            if not progressed:
                missing = [
                    s.name for s in self.steps
                    if s.name not in executed
                ]
                raise RuntimeError(
                    f"Pipeline '{self.name}' cannot progress, unresolved dependencies: {missing}"
                )

        return ctx

    def _run_ready_steps(self, ctx: dict[str, Any], ready: list[PipelineStep], executed: set[str]) -> bool:
        progressed = False
        parallel_steps = [step for step in ready if step.run_in_parallel]
        serial_steps = [step for step in ready if not step.run_in_parallel]

        for step in serial_steps:
            ctx[step.name] = self._execute_step(step, ctx)
            executed.add(step.name)
            progressed = True

        if parallel_steps:
            with ThreadPoolExecutor(max_workers=len(parallel_steps)) as executor:
                future_map = {
                    executor.submit(self._execute_step, step, ctx): step
                    for step in parallel_steps
                }
                for future, step in future_map.items():
                    ctx[step.name] = future.result()
                    executed.add(step.name)
                    progressed = True

        return progressed

    def _execute_step(self, step: PipelineStep, ctx: dict[str, Any]) -> Any:
        attempts = 0
        last_error: Exception | None = None

        while attempts <= step.retry_count:
            attempts += 1
            started = perf_counter()
            try:
                result = self._run_step_with_timeout(step, ctx)
                duration = perf_counter() - started
                ctx["_pipeline_meta"][step.name] = {
                    "attempts": attempts,
                    "duration_seconds": duration,
                    "status": "ok",
                }
                return result
            except Exception as e:
                last_error = e
                if attempts > step.retry_count:
                    duration = perf_counter() - started
                    ctx["_pipeline_meta"][step.name] = {
                        "attempts": attempts,
                        "duration_seconds": duration,
                        "status": "failed",
                        "error": str(e),
                    }
                    raise RuntimeError(f"Pipeline step '{step.name}' failed: {e}") from e

        raise RuntimeError(f"Pipeline step '{step.name}' failed: {last_error}")

    def _run_step_with_timeout(self, step: PipelineStep, ctx: dict[str, Any]) -> Any:
        if not step.timeout_seconds:
            return step.fn(ctx)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(step.fn, ctx)
            try:
                return future.result(timeout=step.timeout_seconds)
            except FutureTimeoutError as e:
                raise TimeoutError(
                    f"timed out after {step.timeout_seconds}s"
                ) from e
