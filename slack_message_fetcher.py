import os
import logging
import signal
import sys
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("slack_fetcher.log"),  # Log to a file
        logging.StreamHandler(sys.stdout)  # Log to console
    ]
)

class SlackMessageFetcher:
    """Continuously fetches new messages from a Slack channel and logs them."""

    def __init__(self, channel_id, poll_interval=10):
        """Initialize Slack client and channel details."""
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        self.CHANNEL_ID = channel_id
        self.POLL_INTERVAL = poll_interval  # How often to fetch messages
        self.last_seen_timestamp = None  # Track the latest message timestamp

        if not self.SLACK_BOT_TOKEN:
            logging.error("Missing SLACK_BOT_TOKEN environment variable.")
            sys.exit(1)

        self.client = WebClient(token=self.SLACK_BOT_TOKEN)
        self.running = True  # Control flag for loop

        # Handle SIGINT (Ctrl+C) for graceful exit
        signal.signal(signal.SIGINT, self.shutdown)

    def fetch_messages(self):
        """Fetches only the latest messages from the Slack channel."""
        try:
            params = {"channel": self.CHANNEL_ID, "limit": 1}
            if self.last_seen_timestamp:
                params["oldest"] = self.last_seen_timestamp  # Fetch only new messages

            response = self.client.conversations_history(**params)
            messages = response.get("messages", [])

            if messages:
                new_messages = []
                for msg in reversed(messages):  # Oldest first
                    ts = msg.get("ts")  # Message timestamp
                    if self.last_seen_timestamp is None or float(ts) > float(self.last_seen_timestamp):
                        new_messages.append(msg)

                if new_messages:
                    for msg in new_messages:
                        user = msg.get("user", "Unknown")
                        text = msg.get("text", "No text available")
                        ts = msg.get("ts")
                        logging.info(f"📩 New message from {user}: {text}")
                        self.last_seen_timestamp = ts  # Update latest timestamp
                else:
                    logging.info("⏳ No new messages.")

        except SlackApiError as e:
            logging.error(f"❌ Slack API Error: {e.response['error']}")
        except Exception as e:
            logging.error(f"⚠️ Unexpected Error: {str(e)}")

    def run(self):
        """Continuously fetch only new messages every X seconds until interrupted."""
        logging.info(f"🚀 Starting Slack Message Fetcher for Channel: {self.CHANNEL_ID}")
        try:
            while self.running:
                self.fetch_messages()
                time.sleep(self.POLL_INTERVAL)  # Wait before next fetch
        except Exception as e:
            logging.error(f"Unexpected failure: {str(e)}")
        finally:
            logging.info("👋 Shutting down gracefully.")

    def shutdown(self, signum, frame):
        """Handles graceful shutdown on user interruption."""
        logging.info("🛑 Received exit signal. Stopping message fetcher...")
        self.running = False
        sys.exit(0)

if __name__ == "__main__":
    fetcher = SlackMessageFetcher(channel_id="C08JS8BVDJ8", poll_interval=10)
    fetcher.run()

