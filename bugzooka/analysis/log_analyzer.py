import logging
import re
import asyncio
from functools import partial
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from langchain.agents import AgentType, initialize_agent
from langchain_community.chat_models.openai import ChatOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from bugzooka.core.constants import (
    MAX_CONTEXT_SIZE,
    MAX_AGENTIC_ITERATIONS,
)
from bugzooka.analysis.prompts import ERROR_FILTER_PROMPT
from bugzooka.analysis.log_summarizer import (
    download_prow_logs,
    search_errors_in_file,
    generate_prompt,
    download_url_to_log,
)
from bugzooka.integrations.inference_client import (
    InferenceClient,
    analyze_log,
    analyze_log_with_tools,
    AgentAnalysisLimitExceededError,
    InferenceAPIUnavailableError,
)
from bugzooka.integrations import mcp_client as mcp_module
from bugzooka.integrations.mcp_client import initialize_global_resources_async
from bugzooka.core.config import ANALYSIS_MODE, get_inference_config, get_prompt_config
from bugzooka.analysis.prow_analyzer import analyze_prow_artifacts
from bugzooka.core.utils import extract_job_details

logger = logging.getLogger(__name__)

class SingleStringInput(BaseModel):
    """Schema for tools that accept a single string argument."""
    query: str = Field(description="The full error summary text to analyze.")


def product_log_wrapper(query: str, product: str) -> str:
    """Wraps analyze_log for product-specific analysis to accept 'query' keyword argument."""
    inference_config = get_inference_config()
    prompt_config = get_prompt_config(product)
    return analyze_log(inference_config, prompt_config, query)


def generic_log_wrapper(query: str) -> str:
    """Wraps analyze_log for generic analysis to accept 'query' keyword argument."""
    inference_config = get_inference_config()
    prompt_config = get_prompt_config("GENERIC")
    return analyze_log(inference_config, prompt_config, query)


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


def filter_errors_with_llm(errors_list, requires_llm, inference_config):
    """Filter errors using LLM."""
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

        client = InferenceClient(
            base_url=inference_config["url"],
            api_key=inference_config["token"],
            model=inference_config["model"],
            verify_ssl=inference_config["verify_ssl"],
            timeout=inference_config["timeout"],
        )

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


def run_agent_analysis(error_summary, product, inference_config):
    """Run agent analysis on the error summary."""
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
    def _run_agent_analysis():
        if ANALYSIS_MODE == "gemini":
            logger.info("Using Gemini analysis mode")
            try:
                # Execute async MCP initialization and Gemini analysis
                return asyncio.run(_run_gemini_analysis_async(error_summary, product))
            except Exception as e:
                logger.error("Unexpected error during Gemini analysis: %s", str(e), exc_info=True)
                raise InferenceAPIUnavailableError(
                    f"Unhandled error during Gemini analysis: {type(e).__name__}: {str(e)}"
                ) from e
        else:
            logger.info("Using agent-based analysis mode")
            try:
                return asyncio.run(_run_fallback_agent_analysis_async(error_summary, product, inference_config))
            except Exception as e:
                logger.error("Unexpected error during async agent execution: %s", str(e), exc_info=True)
                raise InferenceAPIUnavailableError(
                    f"Unhandled error during agent analysis: {type(e).__name__}: {str(e)}"
                ) from e

    async def _run_gemini_analysis_async(error_summary, product):
        """Run Gemini analysis with MCP tool support."""
        # Initialize MCP client if not already initialized
        if mcp_module.mcp_client is None:
            await initialize_global_resources_async()

        # Create custom tools for product-specific and generic analysis
        product_tool = StructuredTool(
            name="analyze_product_log",
            func=partial(product_log_wrapper, product=product),
            description=f"Analyze {product} logs from error summary. Input should be the error summary.",
            args_schema=SingleStringInput
        )

        generic_tool = StructuredTool(
            name="analyze_generic_log",
            func=generic_log_wrapper,
            description="Analyze general logs from error summary. Input should be the error summary.",
            args_schema=SingleStringInput
        )

        # Combine custom tools with MCP tools
        tools = [product_tool, generic_tool] + mcp_module.mcp_tools

        # Graceful degradation: if no MCP tools loaded, log warning
        if not mcp_module.mcp_tools:
            logger.warning(
                "No MCP tools available for Gemini. "
                "Continuing with basic analysis tools only."
            )

        logger.info("Gemini mode: Using %d tools (%d MCP tools)",
                   len(tools), len(mcp_module.mcp_tools))

        # Get prompt config for this product
        prompt_config = get_prompt_config(product)

        # Call with tools (await since it's async)
        response = await analyze_log_with_tools(
            prompt_config=prompt_config,
            error_summary=error_summary,
            tools=tools if tools else None
        )

        return response

    async def _run_fallback_agent_analysis_async(error_summary, product, inference_config):
        """Fallback to agent-based analysis if direct Gemini call fails."""

        if mcp_module.mcp_client is None:
            await initialize_global_resources_async()

        llm = ChatOpenAI(
            model=inference_config["model"],
            api_key=inference_config["token"],
            base_url=inference_config["url"] + "/v1",
        )

        # Use StructuredTool to enforce the single string input schema (query: str)
        product_tool = StructuredTool(
            name="analyze_product_log",
            func=partial(product_log_wrapper, product=product),
            description=f"Analyze {product} logs from error summary. Input should be the error summary.",
            args_schema=SingleStringInput
        )

        generic_tool = StructuredTool(
            name="analyze_generic_log",
            func=generic_log_wrapper,
            description="Analyze general logs from error summary. Input should be the error summary.",
            args_schema=SingleStringInput
        )

        TOOLS = [product_tool, generic_tool] + mcp_module.mcp_tools

        agent = initialize_agent(
            tools=TOOLS,
            llm=llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=MAX_AGENTIC_ITERATIONS,
        )

        query = (
            f"Please analyze this {product} specific error"
            f" summary: {error_summary} using the most appropriate"
            f" tool (product-specific or generic or any other)"
            f" and provide me potential next steps to debug"
            f" this issue as a final answer"
        )

        response = await agent.arun(query)

        if "Agent stopped due to iteration limit or time limit" in response:
            raise AgentAnalysisLimitExceededError(
                "Agent analysis exceeded iteration or time limits"
            )

        return response

    return _run_agent_analysis()
