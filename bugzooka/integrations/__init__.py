"""External service integrations."""

from bugzooka.integrations.inference_client import (
    # Core client
    InferenceClient,
    get_inference_client,
    # Exceptions
    InferenceAPIUnavailableError,
    AgentAnalysisLimitExceededError,
    # Agentic functions
    execute_tool_call,
    analyze_with_agentic,
)

__all__ = [
    # Core client
    "InferenceClient",
    "get_inference_client",
    # Exceptions
    "InferenceAPIUnavailableError",
    "AgentAnalysisLimitExceededError",
    # Agentic functions
    "execute_tool_call",
    "analyze_with_agentic",
]
