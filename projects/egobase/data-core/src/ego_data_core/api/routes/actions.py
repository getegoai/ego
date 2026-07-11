"""Operator action API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ego_data_core.operator import OperatorBridge

router = APIRouter(prefix="/actions", tags=["actions"])

AuthorizationType = Literal["one_time", "session", "policy"]


class ProposeActionRequest(BaseModel):
    automation_id: str = Field(min_length=1)


class AuthorizeActionRequest(BaseModel):
    user_id: str | None = None
    authorization_type: AuthorizationType = "one_time"


class ExecuteActionRequest(BaseModel):
    dry_run: bool = True


@router.post("/propose")
def propose_action(request: ProposeActionRequest) -> dict[str, Any]:
    return OperatorBridge().propose_action(request.automation_id)


@router.post("/{action_id}/authorize")
def authorize_action(
    action_id: str,
    request: AuthorizeActionRequest | None = None,
) -> dict[str, Any]:
    payload = request or AuthorizeActionRequest()
    return OperatorBridge().authorize_action(
        action_id,
        user_id=payload.user_id,
        authorization_type=payload.authorization_type,
    )


@router.post("/{action_id}/execute")
def execute_action(
    action_id: str,
    request: ExecuteActionRequest | None = None,
) -> dict[str, Any]:
    payload = request or ExecuteActionRequest()
    return OperatorBridge().execute_action(action_id, dry_run=payload.dry_run)
