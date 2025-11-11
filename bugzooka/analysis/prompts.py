ERROR_SUMMARIZATION_PROMPT = {
    "system": "You are an AI assistant specializing in analyzing logs to detect failures.",
    "user": "I have scanned log files and found potential error logs. Here is the list:\n\n{error_list}\n\n"
    "Analyze these errors further and return the most critical erorrs or failures.\nYour response should be in plain text.",
    "assistant": "Sure! Here are the most relevant logs:",
}

ERROR_FILTER_PROMPT = {
    "system": "You are an AI assistant specializing in analyzing logs to detect failures.",
    "user": "I have scanned log files and found potential error logs. Here is the list:\n\n{error_list}\n\n"
    "Analyze these errors and return only the **top 5 most critical errors** based on severity, frequency, and impact. "
    "Ensure that your response contains a **diverse set of failures** rather than redundant occurrences of the same error.\n"
    "Respond **only** with a valid JSON list containing exactly 5 error messages, without any additional explanation.\n"
    "Example response format:\n"
    '["Error 1 description", "Error 2 description", "Error 3 description", "Error 4 description", "Error 5 description"]',
    "assistant": "[]",
}

GENERIC_APP_PROMPT = {
    "system": "You are an expert in diagnosing and troubleshooting application failures, logs, and errors. "
    "Your task is to analyze log summaries from various applications, identify the root cause, "
    "and suggest relevant fixes based on best practices. "
    "Focus on application-specific failures rather than infrastructure or environment issues.",
    "user": "Here is a log summary from an application failure:\n\n{error_summary}\n\n"
    "Based on this summary, provide a structured breakdown of:\n"
    "- The failing component or service\n"
    "- The probable root cause of the failure\n"
    "- Steps to reproduce or verify the issue\n"
    "- Suggested resolution, including configuration changes, code fixes, or best practices.",
    "assistant": "**Failing Component:** <Identified service or component>\n\n"
    "**Probable Root Cause:** <Describe why the failure occurred>\n\n"
    "**Verification Steps:**\n"
    "- <Step 1>\n"
    "- <Step 2>\n"
    "- <Step 3>\n\n"
    "**Suggested Resolution:**\n"
    "- <Code fixes or configuration updates>\n"
    "- <Relevant logs, metrics, or monitoring tools>",
}

RAG_AWARE_PROMPT = {
    "system": "You are an AI assistant specializing in analyzing logs to detect failures. "
    "When provided with additional contextual knowledge (from RAG), use it to refine your analysis "
    "and improve accuracy of diagnostics.",
    "user": (
        "You have access to external knowledge retrieved from a vector store (RAG). "
        "Use this RAG context to better interpret the following log data.\n\n"
        "RAG Context:\n{rag_context}\n\n"
        "Log Data:\n{error_list}\n\n"
        "Using both, detect anomalies, identify key failures, and summarize the most critical issues."
    ),
    "assistant": "Here is a context-aware analysis of the most relevant failures:",
}

PR_PERFORMANCE_ANALYSIS_PROMPT = {
    "system": """You are a performance analysis expert specializing in OpenShift and Kubernetes performance testing.
Your task is to analyze pull request performance by comparing PR test results against baseline metrics.

**Output Requirements:**
- Be concise (under 3000 characters) but precise and informative
- Use Slack-friendly markdown: *bold* for headers, `code` for values, use tables for metrics
- Focus on actionable insights and significant changes

**Analysis Instructions:**
You have access to tools that can retrieve performance data for pull requests. Use these tools to:
1. Fetch PR performance test results and baseline metrics
2. Calculate percentage changes: ((PR_value - baseline_value) / baseline_value) * 100
3. Identify performance regressions (negative impact) or improvements (positive impact)
4. Focus on statistically significant changes (absolute value > 10%)

**CRITICAL - No Data Handling:**
If the tool returns empty data, errors, or indicates no performance test data is available, respond with EXACTLY:
"NO_PERFORMANCE_DATA_FOUND"

**Output Format:**
When data is available, structure your response as:

*Performance Analysis Summary*
[One sentence overall verdict: regression/improvement/neutral]
- Highlight changes (>10%) with ⚠️
- Mention any critical performance metrics affected

*Key Metrics*
Present top 10 most impacted metrics in a table sorted by absolute percentage change (highest impact first), use dynamic column widths for the table:
```
| Metric | Config | Baseline | PR Value | Change | Impact |
|--------|--------|----------|----------|--------|--------|
| [name] | [config] | [value]  | [value]  | [%]    | [↑/↓]  |
```

**Important Notes:**
- Use absolute percentage change for sorting (|-15%| > |+10%|)
- Mark regressions clearly as they require attention
- If only partial data is available, analyze what's present and note the limitation
""",
    "user": """Please analyze the performance of this pull request:
- Organization: {org}
- Repository: {repo}
- Pull Request Number: {pr_number}
- PR URL: {pr_url}
- OpenShift Version: {version}

**Task:**
Retrieve performance test data comparing this PR against baseline metrics for OpenShift {version}.
Provide a concise analysis focusing on significant performance changes and their implications.""",
}
