"""
Pytest configuration file.
"""

import pytest


@pytest.fixture
def mock_slack_post_message():
    """Mock Slack chat_postMessage API call that tracks posted messages."""

    def _mock_slack_post_message(posted_messages):
        def mock_post_message(**kwargs):
            posted_messages.append(
                {
                    "channel": kwargs.get("channel"),
                    "text": kwargs.get("text"),
                    "blocks": kwargs.get("blocks"),
                    "thread_ts": kwargs.get("thread_ts"),
                }
            )
            return {"ok": True, "ts": kwargs.get("thread_ts")}

        return mock_post_message

    return _mock_slack_post_message


@pytest.fixture
def mock_slack_conversations_history():
    """Mock Slack conversations_history API call that returns predefined test messages."""

    def _mock_slack_conversations_history(test_messages):
        def mock_conversations_history(**kwargs):
            return {"ok": True, "messages": test_messages, "has_more": False}

        return mock_conversations_history

    return _mock_slack_conversations_history
