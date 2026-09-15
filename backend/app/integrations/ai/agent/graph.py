"""Small LangGraph loop: model -> optional tools -> model -> end."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.integrations.ai.agent.prompts import SYSTEM_PROMPT
from app.integrations.ai.agent.state import AgentState


class ToolBindableModel(Protocol):
    """Minimal model surface used by the graph and lightweight test doubles."""

    def bind_tools(self, tools: list[BaseTool]) -> Any: ...


@dataclass(frozen=True)
class ToolCallTrace:
    name: str
    arguments: dict[str, Any]
    status: Literal["completed", "failed", "requested"]


@dataclass(frozen=True)
class AgentResult:
    answer: str
    tool_calls: list[ToolCallTrace]


class TimberOpsAgent:
    """Run one stateless, read-only Agent request and expose safe tool traces."""

    def __init__(self, model: ToolBindableModel, tools: list[BaseTool]) -> None:
        self._bound_model = model.bind_tools(tools)
        self._graph = self._build_graph(tools)

    def chat(self, message: str) -> AgentResult:
        final_state = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config={"recursion_limit": 10},
        )
        messages: list[BaseMessage] = final_state["messages"]
        return AgentResult(
            answer=self._final_answer(messages),
            tool_calls=self._tool_call_traces(messages),
        )

    def _build_graph(self, tools: list[BaseTool]) -> Any:
        def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
            response = self._bound_model.invoke(
                [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
            )
            return {"messages": [response]}

        builder = StateGraph(AgentState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", END: END},
        )
        builder.add_edge("tools", "agent")
        return builder.compile()

    @staticmethod
    def _final_answer(messages: list[BaseMessage]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                if isinstance(message.content, str):
                    return message.content
                text_blocks = [
                    str(block.get("text", ""))
                    for block in message.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "".join(text_blocks)
        return "无法生成可确认的回答。"

    @staticmethod
    def _tool_call_traces(messages: list[BaseMessage]) -> list[ToolCallTrace]:
        tool_results = {
            message.tool_call_id: message
            for message in messages
            if isinstance(message, ToolMessage)
        }
        traces: list[ToolCallTrace] = []
        for message in messages:
            if not isinstance(message, AIMessage):
                continue
            for call in message.tool_calls:
                tool_message = tool_results.get(call["id"])
                status: Literal["completed", "failed", "requested"] = "requested"
                if tool_message is not None:
                    status = (
                        "failed"
                        if getattr(tool_message, "status", "success") == "error"
                        else "completed"
                    )
                traces.append(
                    ToolCallTrace(
                        name=call["name"],
                        arguments=dict(call["args"]),
                        status=status,
                    )
                )
        return traces
