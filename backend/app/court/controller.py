from threading import Lock
from uuid import UUID

from .demo import DEMO_INPUT
from ..core.llm import ModelError, ModelProvider
from ..models import COURT_STEPS, CourtCase, CourtStep, DebateTurn, Judgment
from .repository import CourtRepository
from . import defense, judge, prosecutor


class CourtNotFound(Exception):
    pass


class CourtConflict(Exception):
    pass


TURN_ROLES = {
    CourtStep.PROSECUTION_1: (prosecutor.speak, 1, "prosecutor"),
    CourtStep.DEFENSE_1: (defense.speak, 1, "defense"),
    CourtStep.PROSECUTION_2: (prosecutor.speak, 2, "prosecutor"),
    CourtStep.DEFENSE_2: (defense.speak, 2, "defense"),
}


class CourtController:
    def __init__(self, repository: CourtRepository, provider: ModelProvider):
        self.repository = repository
        self.provider = provider
        self._in_progress: set[UUID] = set()
        self._lock = Lock()

    def open_case(self, risk_id: str) -> CourtCase:
        snapshot = self.repository.get_input(risk_id)
        if snapshot is None:
            raise CourtNotFound("No completed review input for this risk ID.")
        if self.provider.mode == "demo" and snapshot != DEMO_INPUT:
            from ..services.greenlint import scripted_input
            if snapshot != scripted_input(risk_id):
                raise CourtConflict("Demo mode only supports the predefined example snapshots.")
        return self.repository.create_case(snapshot, self.provider.mode, self.provider.model)

    def get_case(self, case_id: UUID) -> CourtCase:
        case = self.repository.get_case(case_id)
        if case is None:
            raise CourtNotFound("Case not found.")
        return case

    def advance(self, case_id: UUID, expected_step: CourtStep) -> CourtCase:
        with self._lock:
            if case_id in self._in_progress:
                raise CourtConflict("An advance request is already running for this case.")
            self._in_progress.add(case_id)
        try:
            return self._advance(case_id, expected_step)
        finally:
            with self._lock:
                self._in_progress.remove(case_id)

    def _advance(self, case_id: UUID, expected_step: CourtStep) -> CourtCase:
        case = self.get_case(case_id)
        if self._is_saved(case, expected_step):
            return case
        if case.next_step != expected_step:
            raise CourtConflict(f"The next step is {case.next_step or 'already completed'}.")
        if (case.mode, case.model) != (self.provider.mode, self.provider.model):
            raise CourtConflict("Resume this case using the mode and model recorded when it was opened.")

        result = self._run_step(case, expected_step)
        allowed_sources = {citation.source_id for citation in case.snapshot.citations}
        if set(result.source_ids) - allowed_sources:
            raise ModelError("A role cited a source outside the case snapshot.")

        step_index = COURT_STEPS.index(expected_step)
        is_last = expected_step == CourtStep.JUDGMENT
        next_step = None if is_last else COURT_STEPS[step_index + 1]
        self.repository.commit_step(case_id, expected_step, next_step, result)
        return self.get_case(case_id)

    @staticmethod
    def _is_saved(case: CourtCase, step: CourtStep) -> bool:
        if step == CourtStep.JUDGMENT:
            return case.judgment is not None
        return any(turn.step == step for turn in case.turns)

    def _run_step(self, case: CourtCase, step: CourtStep) -> DebateTurn | Judgment:
        snapshot = case.snapshot
        context = {
            "risk_id": snapshot.risk_id,
            "case_facts": snapshot.model_dump(
                mode="json",
                exclude={"risk_id", "review_id", "asset_version_id", "assessment", "reason"},
            ),
            "earlier_turns": [turn.model_dump(mode="json") for turn in case.turns],
        }
        if step == CourtStep.JUDGMENT:
            return judge.review(self.provider, context)

        reply_to = case.turns[-1].step if case.turns else None
        context["reply_to"] = reply_to
        context["initial_assessment"] = {"code": snapshot.assessment, "reason": snapshot.reason}
        run_role, round_number, role = TURN_ROLES[step]
        output = run_role(self.provider, step, context)
        if output.responds_to != reply_to:
            raise ModelError("The response must reference the immediately preceding opposing turn.")
        return DebateTurn(
            **output.model_dump(),
            step=step,
            round=round_number,
            role=role,
        )
