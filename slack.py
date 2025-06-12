import os
import re
import logging
import signal
import sys
import time
import argparse
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from src.config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, get_product_config
from src.prompts import ERROR_FILTER_PROMPT
from src.log_summarizer import download_prow_logs, search_errors_in_file, generate_prompt, download_url_to_log
from src.inference import ask_inference_api, analyze_log
from slack_sdk import WebClient
from src.utils import extract_job_details, get_slack_message_blocks
from src.prow_analyzer import analyze_prow_artifacts
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    handlers=[
        logging.FileHandler("slack_fetcher.log"),  # Log to a file
        logging.StreamHandler(sys.stdout)  # Log to console
    ]
)

class SlackMessageFetcher:
    """Continuously fetches new messages from a Slack channel and logs them."""

    def __init__(self, channel_id, poll_interval=600):
        """Initialize Slack client and channel details."""
        self.SLACK_BOT_TOKEN = SLACK_BOT_TOKEN
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

    def fetch_messages(self, **kwargs):
        """Fetches only the latest messages from the Slack channel."""
        try:
            product = kwargs["product"]
            ci_system = kwargs["ci"]
            product_config = kwargs["product_config"]
            params = {"channel": self.CHANNEL_ID, "limit": 1}
            if self.last_seen_timestamp:
                params["oldest"] = self.last_seen_timestamp  # Fetch only new messages

            response = self.client.conversations_history(**params)
            messages = response.get("messages", [])

            if messages:
                new_messages = []
                for msg in reversed(messages):  # Oldest first
                    ts = msg.get("ts")  # Message timestamp
                    logging.debug(f"Checking message with timestamp: {ts}")

                    replies = self.client.conversations_replies(channel=self.CHANNEL_ID, ts=ts)
                    if (self.last_seen_timestamp is None or float(ts) > float(self.last_seen_timestamp)) and len(replies["messages"]) == 1:
                        new_messages.append(msg)
                    else:
                        logging.debug(f"Skipping message with timestamp {ts} due to timestamp filter or replies count")

                if new_messages:
                    max_ts = self.last_seen_timestamp or "0"
                    for msg in new_messages:
                        user = msg.get("user", "Unknown")
                        text = msg.get("text", "No text available")
                        ts = msg.get("ts")
                        logging.info(f"📩 New message from {user}: {text} at ts {ts}")

                        if float(ts) > float(max_ts):
                            max_ts = ts

                        if 'failure' not in text.lower():
                            logging.info("Not a failure job. Hence skipping it")
                            continue  # Continue processing other messages instead of return

                        if ci_system == "PROW":
                            job_url, job_name = extract_job_details(text)
                            directory_path = download_prow_logs(job_url)
                            errors_list, requires_llm = analyze_prow_artifacts(directory_path, job_name)
                        else:
                            # Pre-assumes the other ci system is ansible
                            url_pattern = r"<([^>]+)>"
                            match = re.search(url_pattern, text)
                            if match:
                                url = match.group(1)
                                logging.info(f"Ansible job url: {url}")
                                directory_path = download_url_to_log(url, "/build-log.txt")
                                errors_list = search_errors_in_file(directory_path + "/build-log.txt")
                                requires_llm = True  # Assuming you want LLM for ansible too?

                        if requires_llm:
                            error_prompt = ERROR_FILTER_PROMPT["user"].format(error_list="\n".join(errors_list)[:8192])
                            response = ask_inference_api(
                                messages=[
                                    {"role": "system", "content": ERROR_FILTER_PROMPT["system"]},
                                    {"role": "user", "content": error_prompt},
                                    {"role": "assistant", "content": ERROR_FILTER_PROMPT["assistant"]}
                                ],
                                url=product_config["endpoint"]["GENERIC"],
                                api_token=product_config["token"]["GENERIC"],
                                model=product_config["model"]["GENERIC"]
                            )

                            # Convert JSON response to a Python list
                            errors_list = response.split("\n")

                        errors_list_string = "\n".join(errors_list)[:8192]
                        message_block = get_slack_message_blocks(
                                markdown_header=":checking: *Error Logs Preview*\n",
                                preformatted_text=errors_list_string
                            )
                        logging.info("Posting error logs preview to Slack")
                        self.client.chat_postMessage(
                            channel=self.CHANNEL_ID,
                            text="Error Logs Preview",
                            blocks=message_block,
                            thread_ts=max_ts
                        )

                        error_prompt = generate_prompt(errors_list)
                        error_summary = ask_inference_api(
                            messages=error_prompt,
                            url=product_config["endpoint"]["GENERIC"],
                            api_token=product_config["token"]["GENERIC"],
                            model=product_config["model"]["GENERIC"]
                        )

                        llm = ChatOpenAI(
                            model_name=product_config["model"]["GENERIC"],
                            openai_api_key=product_config["token"]["GENERIC"],
                            base_url=product_config["endpoint"]["GENERIC"] + "/v1"
                        )

                        product_tool = Tool(
                            name="Product Log Analyzer",
                            func=analyze_log(product, product_config),
                            description="Use this tool for product related log summaries. Provide input as JSON with 'log_summary', 'product', and 'product_config'."
                        )
                        generic_tool = Tool(
                            name="Generic Log Analyzer",
                            func=analyze_log("GENERIC", product_config),
                            description="Use this tool for any general log summaries. Provide input as JSON with 'log_summary', 'product', and 'product_config'."
                        )
                        TOOLS = [product_tool, generic_tool]

                        agent = initialize_agent(
                            tools=TOOLS,
                            llm=llm,
                            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                            verbose=True,
                            handle_parsing_errors=True,
                        )
                        if product:
                            response = agent.run(f"This log is classified as product. Please analyze the summary: {error_summary}")
                        else:
                            response = agent.run(f"This log is classified as generic. Please analyze the summary: {error_summary}")

                        message_block = get_slack_message_blocks(
                                markdown_header=":fast_forward: *Implications to understand*\n",
                                preformatted_text=response
                            )
                        logging.info("Posting analysis summary to Slack")
                        self.client.chat_postMessage(
                            channel=self.CHANNEL_ID,
                            text="Implications summary",
                            blocks=message_block,
                            thread_ts=max_ts
                        )

                    logging.info(f"Updating last_seen_timestamp from {self.last_seen_timestamp} to {max_ts}")
                    self.last_seen_timestamp = max_ts

                else:
                    logging.info("⏳ No new messages.")

        except Exception as e:
            logging.error(f"Error fetching messages: {e}")

        except SlackApiError as e:
            logging.error(f"❌ Slack API Error: {e.response['error']}")
        except Exception as e:
            logging.error(f"⚠️ Unexpected Error: {str(e)}")

    def run(self, **kwargs):
        """
        Continuously fetch only new messages every X seconds until interrupted.

        :param kwargs: arguments to run the application.
        """
        logging.info(f"🚀 Starting Slack Message Fetcher for Channel: {self.CHANNEL_ID}")
        try:
            while self.running:
                self.fetch_messages(**kwargs)
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

# export PYTHONPATH=$(pwd)/src:$PYTHONPATH
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slack Log Analyzer Bot")

    parser.add_argument("--product", type=str, default=os.environ.get("PRODUCT"), help="Product type (e.g., openshift, ansible)")
    parser.add_argument("--ci", type=str, default=os.environ.get("CI"), help="CI system name")

    args = parser.parse_args()
    missing_args = []
    if not args.product:
        missing_args.append("product or PRODUCT")
    if not args.ci:
        missing_args.append("ci or CI")
    if missing_args:
        logging.error(f"Missing required arguments or env vars: {', '.join(missing_args)}")
        sys.exit(1)
    
    kwargs = {
        "product": args.product.upper(),
        "ci": args.ci.upper(),
        "product_config": get_product_config(product_name=args.product.upper()),
    }

    fetcher = SlackMessageFetcher(channel_id=SLACK_CHANNEL_ID, poll_interval=10)
    fetcher.run(**kwargs)
