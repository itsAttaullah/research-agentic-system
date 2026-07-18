"""State mutation with mandatory logging and checkpoint persistence."""

from sra.core.context import RunContext
from sra.core.ports import CheckpointManager, ExecutionLogger
from sra.core.state_machine import assert_transition
from sra.models.enums import AgentState


class StateController:
    """The only runtime service allowed to mutate ``RunContext.state``."""

    def __init__(
        self,
        checkpoints: CheckpointManager,
        logger: ExecutionLogger,
    ) -> None:
        self._checkpoints = checkpoints
        self._logger = logger

    async def transition(self, ctx: RunContext, target: AgentState) -> None:
        """Validate, apply, observe, and persist a state transition."""
        current = ctx.state
        assert_transition(current, target)
        ctx.state = target
        ctx.touch()
        await self._logger.state_transition(
            ctx,
            from_state=current,
            to_state=target,
        )
        await self._checkpoints.save(ctx)

    async def checkpoint(self, ctx: RunContext) -> None:
        """Persist non-transition state changes such as plan or tool history."""
        ctx.touch()
        await self._checkpoints.save(ctx)
