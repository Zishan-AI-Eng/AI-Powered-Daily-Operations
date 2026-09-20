import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agents.graph import agent_graph
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


if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
