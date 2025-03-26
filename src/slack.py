import os
import re
import logging
import signal
import sys
import time
import json
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from src.config import SLACK_BOT_TOKEN
from src.prompts import ERROR_FILTER_PROMPT
from src.config import INFERENCE_ENDPOINTS, INFERENCE_TOKENS, MODEL_MAP, SLACK_CHANNEL_ID
from src.log_summarizer import download_prow_logs, search_errors_in_file, generate_prompt, download_url_to_log
from src.inference import ask_inference_api, analyze_openshift_log, analyze_ansible_log, analyze_generic_log
from slack_sdk import WebClient
from src.utils import extract_link
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

    def fetch_messages(self):
        """Fetches only the latest messages from the Slack channel."""
        select_agent = {"Openshift": False, "Ansible": False}
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
                        job_url = extract_link(text)
                        if job_url:
                            directory_path = download_prow_logs(job_url)
                            select_agent["Openshift"] = True
                        else:
                           # ansible url link
                           url_pattern = r"<([^>]+)>"
                           match = re.search(url_pattern, text)
                           if match:
                               url = match.group(1)
                               logging.info(f"Ansible job url: {url}")
                               directory_path = download_url_to_log(url, "/build-log.txt")
                               select_agent["Ansible"] = True

                        full_errors_list = search_errors_in_file(directory_path + "/build-log.txt")
                        full_errors_list = list(set(full_errors_list))
                        if len(full_errors_list) > 10:
                            full_errors_list = full_errors_list[:10]
                        error_prompt = ERROR_FILTER_PROMPT["user"].format(error_list="\n".join(full_errors_list))
                        response = ask_inference_api(
                            messages = [
                                {"role": "system", "content": ERROR_FILTER_PROMPT["system"]},
                                {"role": "user", "content": error_prompt},
                                {"role": "assistant", "content": ERROR_FILTER_PROMPT["assistant"]}
                            ],
                            url=INFERENCE_ENDPOINTS["Generic"],
                            api_token=INFERENCE_TOKENS["Generic"],
                            model=MODEL_MAP["Generic"]
                        )

                        # Convert JSON response to a Python list
                        errors_list = response.split("\n")
                        errors_list_string = "\n".join(errors_list)
                        self.client.chat_postMessage(
                            channel=self.CHANNEL_ID,
                            text=(
                                ":checking: *Error Logs Preview*"
                                "\n```"
                                f"\n{errors_list_string}\n"
                                "```"
                            ),
                            thread_ts=ts
                        )
                        error_prompt = generate_prompt(errors_list)
                        error_summary = ask_inference_api(messages=error_prompt, url=INFERENCE_ENDPOINTS["Generic"], api_token=INFERENCE_TOKENS["Generic"], model=MODEL_MAP["Generic"])
                        llm = ChatOpenAI(model_name=MODEL_MAP["Generic"], openai_api_key=INFERENCE_TOKENS["Generic"], base_url=INFERENCE_ENDPOINTS["Generic"]+"/v1")
                        openshift_tool = Tool(
                            name="OpenShift Log Analyzer",
                            func=analyze_openshift_log,
                            description="Use this tool for OpenShift-related log summaries."
                        )
                        ansible_tool = Tool(
                            name="Ansible Log Analyzer",
                            func=analyze_ansible_log,
                            description="Use this tool for Ansible-related log summaries."
                        )
                        generic_tool = Tool(
                            name="Generic Log Analyzer",
                            func=analyze_generic_log,
                            description="Use this tool for general logs not specific to OpenShift or Ansible."
                        )
                        TOOLS = [openshift_tool, ansible_tool, generic_tool]
                        agent = initialize_agent(
                            tools=TOOLS,
                            llm=llm,
                            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                            verbose=True
                        )
                        if select_agent["Openshift"]:
                            response = agent.run(f"The log is classified as Openshift. Analyze the following summary: {error_summary}")
                        elif select_agent["Ansible"]:
                            response = agent.run(f"The log is classified as Ansible. Analyze the following summary: {error_summary}")
                        else:
                            print("No agent is selected, exiting the application...")
                            sys.exit(1)
                        print(response)
                        self.client.chat_postMessage(
                            channel=self.CHANNEL_ID,
                            text=(
                                ":fast_forward: *Implications to understand*"
                                "\n```"
                                f"\n{response}\n"
                                "```"
                            ),
                            thread_ts=ts
                        )
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

# export PYTHONPATH=$(pwd)/src:$PYTHONPATH
if __name__ == "__main__":
    fetcher = SlackMessageFetcher(channel_id=SLACK_CHANNEL_ID, poll_interval=10)
    fetcher.run()
