"""
Shared utilities for analysis modules.
"""
from typing import Any


def make_response(success: bool, message: str, **extras: Any) -> dict[str, Any]:
    """
    Create a standardized response dictionary.

    :param success: Whether the operation succeeded
    :param message: Response message
    :param extras: Additional key-value pairs to include
    :return: Response dictionary
    """
    return {"success": success, "message": message, **extras}
