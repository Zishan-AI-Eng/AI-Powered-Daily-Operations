import os
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agents.graph import agent_graph
from adapters.hubspot_client import (
	fetch_explorer_candidate,
	fetch_explorer_candidates,
	fetch_explorer_companies,
	fetch_explorer_deals,
)
from utils.logger import get_logger


logger = get_logger(__name__)
SERVICE_VERSION = "1.1.0"

app = FastAPI(
	title="AI-Powered Daily Operations API",
	version="1.0.0",
	description="REST API for the autonomous recruitment operations agent.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		origin.strip()
		for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
		if origin.strip()
	],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)

crm_agent_graph = agent_graph()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
	"""Attach a stable request ID to every response for frontend support tracing."""
	request_id = request.headers.get("x-request-id", str(uuid4()))
	request.state.request_id = request_id
	response = await call_next(request)
	response.headers["x-request-id"] = request_id
	return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	"""Return a consistent validation error shape for dashboard clients."""
	request_id = getattr(request.state, "request_id", str(uuid4()))
	return JSONResponse(
		status_code=422,
		content={
			"error": "validation_error",
			"message": "The request payload is invalid.",
			"details": exc.errors(),
			"request_id": request_id,
		},
	)


class ChatRequest(BaseModel):
	"""Request body for an agent conversation turn."""

	message: str = Field(..., min_length=1, description="The user's operational request.")
	thread_id: str | None = Field(
		default=None,
		min_length=1,
		description="Optional conversation identifier for state-aware graph execution.",
	)


class ChatResponse(BaseModel):
	"""Response returned after the agent completes its turn."""

	response: str
	thread_id: str
	request_id: str


class HealthResponse(BaseModel):
	status: str
	service: str
	version: str
	timestamp: datetime


class ReadinessResponse(HealthResponse):
	dependencies: dict[str, str]


class HistoryMessage(BaseModel):
	role: str
	content: str


class HistoryResponse(BaseModel):
	thread_id: str
	messages: list[HistoryMessage]
	count: int


class CandidateExplorerItem(BaseModel):
	id: str | None
	firstname: str | None
	lastname: str | None
	email: str | None
	phone: str | None
	hs_lead_status: str | None
	hubspot_owner_id: str | None


class CompanyExplorerItem(BaseModel):
	id: str | None
	name: str | None
	domain: str | None
	industry: str | None
	city: str | None
	phone: str | None
	hubspot_owner_id: str | None


class DealExplorerItem(BaseModel):
	id: str | None
	dealname: str | None
	amount: str | None
	dealstage: str | None
	closedate: str | None
	hubspot_owner_id: str | None


ExplorerItem = TypeVar("ExplorerItem")


class ExplorerPage(BaseModel, Generic[ExplorerItem]):
	items: list[ExplorerItem]
	total: int
	page: int
	limit: int


def _raise_hubspot_error(result: Any, resource: str) -> None:
	"""Translate an adapter error string into an appropriate API response."""
	if not isinstance(result, str):
		return
	status_code = 404 if "not found" in result.lower() else 502
	logger.error("HubSpot %s explorer request returned an error: %s", resource, result)
	raise HTTPException(status_code=status_code, detail={"error": result, "resource": resource})


def _message_content_to_text(content: Any) -> str:
	"""Normalize LangChain text or content blocks into an API string."""
	if isinstance(content, str):
		return content
	if isinstance(content, list):
		text_blocks = [
			block.get("text", "")
			for block in content
			if isinstance(block, dict) and block.get("text")
		]
		if text_blocks:
			return "\n".join(text_blocks)
	return str(content)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
	"""Process one user request through the autonomous operations graph."""
	thread_id = request.thread_id or str(uuid4())
	request_id = getattr(http_request.state, "request_id", str(uuid4()))
	logger.info("Chat request received: request_id=%s thread_id=%s", request_id, thread_id)

	try:
		config = {
			"configurable": {"thread_id": thread_id},
			"recursion_limit": 25,
		}
		result = crm_agent_graph.invoke(
			{"messages": [HumanMessage(content=request.message)]},
			config=config,
		)
		logger.info("Agent graph executed: request_id=%s thread_id=%s", request_id, thread_id)

		messages = result.get("messages", [])
		if not messages:
			raise RuntimeError("Agent graph returned no messages.")

		response_text = _message_content_to_text(messages[-1].content)
		logger.info("Chat response sent: request_id=%s thread_id=%s", request_id, thread_id)
		return ChatResponse(response=response_text, thread_id=thread_id, request_id=request_id)
	except Exception as exc:
		logger.exception("Agent graph execution failed: request_id=%s thread_id=%s", request_id, thread_id)
		raise HTTPException(
			status_code=500,
			detail={
				"error": "agent_execution_failed",
				"message": "The operations agent could not process the request.",
				"thread_id": thread_id,
				"request_id": request_id,
			},
		) from exc


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
	"""Return a lightweight liveness response."""
	return HealthResponse(
		status="ok",
		service="ai-operations-integrator",
		version=SERVICE_VERSION,
		timestamp=datetime.now(timezone.utc),
	)


@app.get("/api/ready", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
	"""Report whether required runtime configuration is present."""
	dependencies = {
		"google_llm": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
		"hubspot": "configured" if os.getenv("HUBSPOT_API_KEY") else "missing",
	}
	status = "ok" if all(value == "configured" for value in dependencies.values()) else "degraded"
	return ReadinessResponse(
		status=status,
		service="ai-operations-integrator",
		version=SERVICE_VERSION,
		timestamp=datetime.now(timezone.utc),
		dependencies=dependencies,
	)


@app.get("/api/threads/{thread_id}/messages", response_model=HistoryResponse)
def thread_history(thread_id: str, limit: int = 100) -> HistoryResponse:
	"""Return the latest checkpointed conversation for a thread."""
	if not thread_id.strip():
		raise HTTPException(status_code=400, detail="thread_id cannot be empty")
	if limit < 1 or limit > 500:
		raise HTTPException(status_code=400, detail="limit must be between 1 and 500")

	try:
		state = crm_agent_graph.get_state({"configurable": {"thread_id": thread_id}})
		messages = state.values.get("messages", []) if state else []
		history = [
			HistoryMessage(
				role=getattr(message, "type", "unknown"),
				content=_message_content_to_text(getattr(message, "content", "")),
			)
			for message in messages[-limit:]
		]
		return HistoryResponse(thread_id=thread_id, messages=history, count=len(history))
	except Exception as exc:
		logger.exception("Thread history lookup failed: thread_id=%s", thread_id)
		raise HTTPException(status_code=500, detail="Unable to retrieve thread history") from exc


@app.get("/api/candidates", response_model=ExplorerPage[CandidateExplorerItem])
def get_candidates(
	search: str | None = Query(default=None, min_length=1, max_length=100),
	page: int = Query(default=1, ge=1, le=10000),
	limit: int = Query(default=25, ge=1, le=100),
) -> ExplorerPage[CandidateExplorerItem]:
	"""Return paginated live candidate data from HubSpot."""
	result = fetch_explorer_candidates(page=page, limit=limit, search=search)
	_raise_hubspot_error(result, "candidates")
	return ExplorerPage[CandidateExplorerItem](
		items=result["items"], total=result["total"], page=page, limit=limit
	)


@app.get("/api/candidates/{candidate_id}", response_model=CandidateExplorerItem)
def get_candidate(
	candidate_id: str = Path(..., min_length=1, max_length=100),
) -> CandidateExplorerItem:
	"""Return one live candidate from HubSpot by contact ID."""
	result = fetch_explorer_candidate(candidate_id)
	_raise_hubspot_error(result, "candidate")
	return CandidateExplorerItem.model_validate(result)


@app.get("/api/companies", response_model=ExplorerPage[CompanyExplorerItem])
def get_companies(
	search: str | None = Query(default=None, min_length=1, max_length=100),
	page: int = Query(default=1, ge=1, le=10000),
	limit: int = Query(default=25, ge=1, le=100),
) -> ExplorerPage[CompanyExplorerItem]:
	"""Return paginated live company data from HubSpot."""
	result = fetch_explorer_companies(page=page, limit=limit, search=search)
	_raise_hubspot_error(result, "companies")
	return ExplorerPage[CompanyExplorerItem](
		items=result["items"], total=result["total"], page=page, limit=limit
	)


@app.get("/api/deals", response_model=ExplorerPage[DealExplorerItem])
def get_deals(
	stage: str | None = Query(default=None, min_length=1, max_length=100),
	page: int = Query(default=1, ge=1, le=10000),
	limit: int = Query(default=25, ge=1, le=100),
) -> ExplorerPage[DealExplorerItem]:
	"""Return paginated live deal data from HubSpot."""
	result = fetch_explorer_deals(page=page, limit=limit, stage=stage)
	_raise_hubspot_error(result, "deals")
	return ExplorerPage[DealExplorerItem](
		items=result["items"], total=result["total"], page=page, limit=limit
	)


if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
