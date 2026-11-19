from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..court.controller import CourtController
from ..models import AdvanceRequest, CourtCase, CourtInput, Identifier
from ..court.repository import CourtRepository


def build_router(repository: CourtRepository, controller: CourtController, snapshot_loader=None) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["Court"])

    @router.put("/court-inputs/{risk_id}", response_model=CourtInput)
    def register_review_input(risk_id: Identifier, snapshot: CourtInput) -> CourtInput:
        if risk_id != snapshot.risk_id:
            raise HTTPException(status_code=422, detail="The path and body risk IDs must match.")
        repository.register_input(snapshot)
        return snapshot

    @router.post("/risks/{risk_id}/appeals", status_code=201, response_model=CourtCase)
    def open_appeal(risk_id: Identifier) -> CourtCase:
        if repository.get_input(risk_id) is None and snapshot_loader is not None:
            repository.register_input(snapshot_loader(risk_id))
        return controller.open_case(risk_id)

    @router.get("/risks/{risk_id}/cases", response_model=list[CourtCase])
    def list_cases(risk_id: Identifier):
        return repository.list_cases(risk_id)

    @router.get("/cases/{case_id}", response_model=CourtCase)
    def read_case(case_id: UUID) -> CourtCase:
        return controller.get_case(case_id)

    @router.post("/cases/{case_id}/advance", response_model=CourtCase)
    def advance_case(case_id: UUID, request: AdvanceRequest) -> CourtCase:
        return controller.advance(case_id, request.expected_step)

    return router
