"""External service integrations."""

from bugzooka.integrations.inference_client import (
    # Core client
    InferenceClient,
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
