"""
Lightweight workflow pipeline engine with dependency-aware step execution.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


StepFn = Callable[[dict[str, Any]], Any]


@dataclass
class PipelineStep:
    """A single pipeline step."""

    name: str
    fn: StepFn
    depends_on: list[str] = field(default_factory=list)


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

        while len(executed) < len(self.steps):
            progressed = False
            for step in self.steps:
                if step.name in executed:
                    continue
                if not all(dep in executed for dep in step.depends_on):
                    continue

                result = step.fn(ctx)
                ctx[step.name] = result
                executed.add(step.name)
                progressed = True

            if not progressed:
                missing = [
                    s.name for s in self.steps
                    if s.name not in executed
                ]
                raise RuntimeError(
                    f"Pipeline '{self.name}' cannot progress, unresolved dependencies: {missing}"
                )

        return ctx
