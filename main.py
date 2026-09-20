from uuid import uuid4
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agents.graph import agent_graph
from utils.logger import get_logger


logger = get_logger(__name__)

app = FastAPI(
	title="AI-Powered Daily Operations API",
	version="1.0.0",
	description="REST API for the autonomous recruitment operations agent.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)

crm_agent_graph = agent_graph()


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
def chat(request: ChatRequest) -> ChatResponse:
	"""Process one user request through the autonomous operations graph."""
	thread_id = request.thread_id or str(uuid4())
	logger.info("Chat request received: thread_id=%s", thread_id)

	try:
		config = {"configurable": {"thread_id": thread_id}}
		result = crm_agent_graph.invoke(
			{"messages": [HumanMessage(content=request.message)]},
			config=config,
		)
		logger.info("Agent graph executed: thread_id=%s", thread_id)

		messages = result.get("messages", [])
		if not messages:
			raise RuntimeError("Agent graph returned no messages.")

		response_text = _message_content_to_text(messages[-1].content)
		logger.info("Chat response sent: thread_id=%s", thread_id)
		return ChatResponse(response=response_text, thread_id=thread_id)
	except Exception as exc:
		logger.exception("Agent graph execution failed: thread_id=%s", thread_id)
		raise HTTPException(
			status_code=500,
			detail={
				"error": "agent_execution_failed",
				"message": "The operations agent could not process the request.",
				"thread_id": thread_id,
			},
		) from exc


if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
