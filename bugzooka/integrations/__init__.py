"""External service integrations."""

from bugzooka.integrations.inference_client import (
    # Core client
    InferenceClient,
    get_inference_client,
    # Exceptions
    InferenceAPIUnavailableError,
    AgentAnalysisLimitExceededError,
    # Convenience functions
    analyze_log,
    # Agentic functions
    execute_tool_call,
    analyze_with_agentic,
    analyze_log_with_tools,
)

__all__ = [
    # Core client
    "InferenceClient",
    "get_inference_client",
    # Exceptions
    "InferenceAPIUnavailableError",
    "AgentAnalysisLimitExceededError",
    # Convenience functions
    "analyze_log",
    # Agentic functions
    "execute_tool_call",
    "analyze_with_agentic",
    "analyze_log_with_tools",
]
