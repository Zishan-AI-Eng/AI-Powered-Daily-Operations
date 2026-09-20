import os 
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START ,END , MessagesState
from langchain.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.logger import get_logger
from typing import TypedDict
from agents.tools import crm_tools


logger = get_logger(__name__)

load_dotenv()  # Load environment variables from .env file

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


llm = ChatGoogleGenerativeAI(
    model='gemini-3.5-flash',
    api_key=GOOGLE_API_KEY,
    temperature=0.2
    )




llm_with_tools = llm.bind_tools(crm_tools)  # Bind the CRM tools to the LLM


def agent_node(state: MessagesState):
    """
    Agent Node for processing messages through the LLM with tools.
    """
    
    logger.info("Agent Node Invoked: Processing messages through the LLM with tools.")
    response = llm_with_tools.invoke(state['messages'])
    
    return {'messages': [response]}


def agent_graph():
    """
    Constructs the agent graph for the CRM workflow.
    """
    
    workflow = StateGraph(MessagesState)

    workflow.add_node('agent',agent_node)
    workflow.add_node('tools', ToolNode(crm_tools))

    workflow.add_edge(START, 'agent')
    workflow.add_conditional_edges(
        'agent',
        tools_condition
        
    )
    workflow.add_edge("tools", "agent")

    crm_agent_graph = workflow.compile()
    
    return crm_agent_graph




