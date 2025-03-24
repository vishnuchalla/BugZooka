ERROR_SUMMARIZATION_PROMPT = {
    "system": "You are an AI assistant specializing in analyzing logs to detect failures.",
    "user": "I have scanned log files and found potential error logs. Here is the list:\n\n{error_list}\n\n"
            "Analyze these errors further and return the most critical erorrs or failures.\nYour response should be in plain text.",
    "assistant": "Sure! Here are the most relevant logs:"
}

OPENSHIFT_PROMPT = {
    "system": "You are an expert in OpenShift, Kubernetes, and cloud infrastructure. "
              "Your task is to analyze logs and summaries related to OpenShift environments. "
              "Given a log summary, identify the root cause, potential fixes, and affected components. "
              "Be precise and avoid generic troubleshooting steps. Prioritize OpenShift-specific debugging techniques.",
    
    "user": "Here is the log summary from an OpenShift environment:\n\n{summary}\n\n"
            "Based on this summary, provide a structured breakdown of:\n"
            "- The OpenShift component likely affected (e.g., etcd, kube-apiserver, ingress, SDN, Machine API)\n"
            "- The probable root cause\n"
            "- Steps to verify the issue further\n"
            "- Suggested resolution, including OpenShift-specific commands or configurations.",
    
    "assistant": "**Affected Component:** <Identified component>\n\n"
                 "**Probable Root Cause:** <Describe why this issue might be occurring>\n\n"
                 "**Verification Steps:**\n"
                 "- <Step 1>\n"
                 "- <Step 2>\n"
                 "- <Step 3>\n\n"
                 "**Suggested Resolution:**\n"
                 "- <OpenShift CLI commands>\n"
                 "- <Relevant OpenShift configurations>"
}

ANSIBLE_PROMPT = {
    "system": "You are an expert in Ansible automation, playbook debugging, and infrastructure as code (IaC). "
              "Your task is to analyze log summaries related to Ansible execution, playbook failures, and task errors. "
              "Given a log summary, identify the root cause, affected tasks, and potential fixes. "
              "Prioritize Ansible-specific debugging techniques over generic troubleshooting.",

    "user": "Here is the log summary from an Ansible execution:\n\n{summary}\n\n"
            "Based on this summary, provide a structured breakdown of:\n"
            "- The failed Ansible task and module involved\n"
            "- The probable root cause\n"
            "- Steps to reproduce or verify the issue\n"
            "- Suggested resolution, including relevant playbook changes or command-line fixes.",

    "assistant": "**Failed Task & Module:** <Identified task and module>\n\n"
                 "**Probable Root Cause:** <Describe why the failure occurred>\n\n"
                 "**Verification Steps:**\n"
                 "- <Step 1>\n"
                 "- <Step 2>\n"
                 "- <Step 3>\n\n"
                 "**Suggested Resolution:**\n"
                 "- <Ansible CLI commands>\n"
                 "- <Playbook modifications or configuration changes>"
}

GENERIC_APP_PROMPT = {
    "system": "You are an expert in diagnosing and troubleshooting application failures, logs, and errors. "
              "Your task is to analyze log summaries from various applications, identify the root cause, "
              "and suggest relevant fixes based on best practices. "
              "Focus on application-specific failures rather than infrastructure or environment issues.",

    "user": "Here is a log summary from an application failure:\n\n{summary}\n\n"
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
                 "- <Relevant logs, metrics, or monitoring tools>"
}
