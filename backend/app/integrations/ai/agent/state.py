"""State type for the simple message-and-tools graph."""

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Append-only conversation messages for one stateless API request."""
