"""Pydantic models for the planning agent."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field



class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class PlanStep(BaseModel):
    id: str = Field(..., description="Unique identifier for the step (e.g., 'step-1')")
    title: str = Field(..., description="Short title of the step")
    description: str = Field(..., description="Detailed description of what needs to be done")
    status: StepStatus = Field(default=StepStatus.PENDING)


class Plan(BaseModel):
    title: str
    overview: str = Field(..., description="Executive summary of the plan")
    steps: list[PlanStep]



class ActionType(str, Enum):
    NONE = "NONE"
    PROPOSE = "PROPOSE"
    CREATE = "CREATE"
    UPDATE = "UPDATE"


# ── Structured agent response ───

class AgentResponse(BaseModel):
    thought: str = Field(..., description="Internal reasoning about the user's request and state.")
    response_to_user: str = Field(
        ...,
        description="The natural language response to show the user. Ask clarifying questions here if needed.",
    )
    action: ActionType = Field(
        ...,
        description="PROPOSE = present a plan preview for user confirmation. CREATE = finalize a proposed plan after user approval. UPDATE = modify an existing confirmed plan. NONE = just chatting.",
    )
    plan: Optional[Plan] = Field(
        default=None,
        description="The full plan object. Required if action is PROPOSE, CREATE, or UPDATE. Leave null if action is NONE.",
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="A brief summary of the changes made to the plan. Required if action is UPDATE, PROPOSE, or CREATE.",
    )
    plan_summary: Optional[str] = Field(
        default=None,
        description="A concise, readable summary of the plan. Required when action is PROPOSE, CREATE, or UPDATE. Highlight the goal, key milestones, and total number of steps.",
    )
    conversation_summary: Optional[str] = Field(
        default=None,
        description="An executive summary of the entire conversation so far — decisions made, requirements gathered, current state. Always populate this.",
    )


# ── Conversation models ────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_blocked: bool = False


# ── Plan version tracking ───

class PlanVersion(BaseModel):
    version: int
    plan: Plan
    change_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Session state ────

class Session(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    plan_name: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    current_plan: Optional[Plan] = None
    pending_plan: Optional[Plan] = Field(
        default=None,
        description="A proposed plan awaiting user confirmation. Promoted to current_plan on approval.",
    )
    plan_versions: list[PlanVersion] = Field(default_factory=list)
    user_preferences: dict = Field(default_factory=dict)
    compressed_context: Optional[str] = None
    conversation_summary: Optional[str] = None
    plan_summary: Optional[str] = None
    change_summary: Optional[str] = None
    turn_count: int = 0


# ── API request / response models ────

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    plan: Optional[Plan] = None
    action: ActionType
    change_summary: Optional[str] = None
    plan_summary: Optional[str] = None
    conversation_summary: Optional[str] = None
    turn_count: int
    plan_version: Optional[int] = None
    awaiting_confirmation: bool = False
