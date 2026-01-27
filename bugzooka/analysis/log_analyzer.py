import logging
import re
import asyncio
from functools import partial
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from bugzooka.core.constants import MAX_CONTEXT_SIZE
from bugzooka.analysis.prompts import ERROR_FILTER_PROMPT
from bugzooka.analysis.log_summarizer import (
    download_prow_logs,
    search_errors_in_file,
    generate_prompt,
    download_url_to_log,
)
from bugzooka.integrations.inference_client import (
    get_inference_client,
    analyze_log,
    analyze_log_with_tools,
    AgentAnalysisLimitExceededError,
    InferenceAPIUnavailableError,
)
from bugzooka.integrations import mcp_client as mcp_module
from bugzooka.integrations.mcp_client import initialize_global_resources_async
from bugzooka.core.config import get_inference_config, get_prompt_config
from bugzooka.analysis.prow_analyzer import analyze_prow_artifacts
from bugzooka.core.utils import extract_job_details

logger = logging.getLogger(__name__)

class SingleStringInput(BaseModel):
    """Schema for tools that accept a single string argument."""
    query: str = Field(description="The full error summary text to analyze.")


def product_log_wrapper(query: str, product: str) -> str:
    """Wraps analyze_log for product-specific analysis to accept 'query' keyword argument."""
    prompt_config = get_prompt_config(product)
    return analyze_log(prompt_config, query)


def generic_log_wrapper(query: str) -> str:
    """Wraps analyze_log for generic analysis to accept 'query' keyword argument."""
    prompt_config = get_prompt_config("GENERIC")
    return analyze_log(prompt_config, query)


def download_and_analyze_logs(text, ci_system):
    """Extract job details, download and analyze logs based on CI system."""
    if ci_system == "PROW":
        job_url, job_name = extract_job_details(text)
        if job_url is None or job_name is None:
            return None, None, None, None
        directory_path = download_prow_logs(job_url)
        (
            errors_list,
            categorization_message,
            requires_llm,
            is_install_issue,
        ) = analyze_prow_artifacts(directory_path, job_name)
    else:
        # Pre-assumes the other ci system is ansible
        url_pattern = r"<([^>]+)>"
        match = re.search(url_pattern, text)
        if not match:
            return None, None, None, None
        url = match.group(1)
        logger.info("Ansible job url: %s", url)
        directory_path = download_url_to_log(url, "/build-log.txt")
        errors_list = search_errors_in_file(directory_path + "/build-log.txt")
        categorization_message = ""
        requires_llm = True  # Assuming you want LLM for ansible too?
        is_install_issue = False

    return errors_list, categorization_message, requires_llm, is_install_issue


def filter_errors_with_llm(errors_list, requires_llm):
    """Filter errors using LLM."""
    inference_config = get_inference_config()
    retry_config = inference_config.get("retry", {})

    @retry(
        stop=stop_after_attempt(retry_config["max_attempts"]),
        wait=wait_exponential(
            multiplier=retry_config["backoff"],
            min=retry_config["delay"],
            max=retry_config["max_delay"],
        ),
        retry=retry_if_exception_type(
            (InferenceAPIUnavailableError, AgentAnalysisLimitExceededError)
        ),
        reraise=True,
    )
    def _filter_errors():
        current_errors_list = errors_list
        client = get_inference_client()

        if requires_llm:
            error_step = current_errors_list[0]
            error_prompt = ERROR_FILTER_PROMPT["user"].format(
                error_list="\n".join(current_errors_list or [])[:MAX_CONTEXT_SIZE]
            )
            message = client.chat(
                messages=[
                    {"role": "system", "content": ERROR_FILTER_PROMPT["system"]},
                    {"role": "user", "content": error_prompt},
                    {"role": "assistant", "content": ERROR_FILTER_PROMPT["assistant"]},
                ],
            )

            # Convert JSON response to a Python list
            content = message.content or ""
            current_errors_list = [error_step + "\n"] + content.split("\n")

        error_prompt = generate_prompt(current_errors_list)
        message = client.chat(messages=error_prompt)
        return message.content or ""

    return _filter_errors()


async def _run_analysis_async(error_summary, product):
    """Run analysis with MCP tool support."""
    if mcp_module.mcp_client is None:
        await initialize_global_resources_async()

    # Create custom tools for product-specific and generic analysis
    product_tool = StructuredTool(
        name="analyze_product_log",
        func=partial(product_log_wrapper, product=product),
        description=f"Analyze {product} logs from error summary. Input should be the error summary.",
        args_schema=SingleStringInput,
    )

    generic_tool = StructuredTool(
        name="analyze_generic_log",
        func=generic_log_wrapper,
        description="Analyze general logs from error summary. Input should be the error summary.",
        args_schema=SingleStringInput,
    )

    tools = [product_tool, generic_tool] + mcp_module.mcp_tools

    if not mcp_module.mcp_tools:
        logger.warning(
            "No MCP tools available. Continuing with basic analysis tools only."
        )

    logger.info(
        "Using %d tools (%d MCP tools)", len(tools), len(mcp_module.mcp_tools)
    )

    prompt_config = get_prompt_config(product)
    return await analyze_log_with_tools(
        prompt_config=prompt_config,
        error_summary=error_summary,
        tools=tools if tools else None,
    )


def run_agent_analysis(error_summary, product):
    """Run agent analysis on the error summary with retry logic."""
    retry_config = get_inference_config().get("retry", {})

    @retry(
        stop=stop_after_attempt(retry_config["max_attempts"]),
        wait=wait_exponential(
            multiplier=retry_config["backoff"],
            min=retry_config["delay"],
            max=retry_config["max_delay"],
        ),
        retry=retry_if_exception_type(
            (InferenceAPIUnavailableError, AgentAnalysisLimitExceededError)
        ),
        reraise=True,
    )
    def _with_retry():
        try:
            return asyncio.run(_run_analysis_async(error_summary, product))
        except (InferenceAPIUnavailableError, AgentAnalysisLimitExceededError):
            raise
        except Exception as e:
            logger.error("Unexpected error during analysis: %s", str(e), exc_info=True)
            raise InferenceAPIUnavailableError(
                f"Unhandled error during analysis: {type(e).__name__}: {str(e)}"
            ) from e

    return _with_retry()
