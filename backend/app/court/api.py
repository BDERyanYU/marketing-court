from uuid import UUID

from fastapi import APIRouter, HTTPException

from .controller import CourtController
from .models import AdvanceRequest, CourtCase, CourtInput, Identifier
from .repository import CourtRepository


def build_router(repository: CourtRepository, controller: CourtController) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["Court"])

    @router.put("/court-inputs/{risk_id}", response_model=CourtInput)
    def register_review_input(risk_id: Identifier, snapshot: CourtInput) -> CourtInput:
        if risk_id != snapshot.risk_id:
            raise HTTPException(status_code=422, detail="The path and body risk IDs must match.")
        repository.register_input(snapshot)
        return snapshot

    @router.post("/risks/{risk_id}/appeals", status_code=201, response_model=CourtCase)
    def open_appeal(risk_id: Identifier) -> CourtCase:
        return controller.open_case(risk_id)

    @router.get("/cases/{case_id}", response_model=CourtCase)
    def read_case(case_id: UUID) -> CourtCase:
        return controller.get_case(case_id)

    @router.post("/cases/{case_id}/advance", response_model=CourtCase)
    def advance_case(case_id: UUID, request: AdvanceRequest) -> CourtCase:
        return controller.advance(case_id, request.expected_step)

    return router
