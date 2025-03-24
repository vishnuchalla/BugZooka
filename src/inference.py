import requests
from src.config import INFERENCE_ENDPOINTS, INFERENCE_TOKENS, MODEL_MAP
from src.prompts import OPENSHIFT_PROMPT, ANSIBLE_PROMPT, GENERIC_APP_PROMPT

def ask_inference_api(
    messages, url, api_token, model,
    top_p=0.95, frequency_penalty=1.03, temperature=0.01,
    max_tokens=512, organization=None, cache=None, verbose=False
):
    """
    Sends a request to the inference API with configurable parameters.

    :param messages: List of message dictionaries with 'role' and 'content'.
    :param url: Inference API base URL.
    :param api_token: API authentication token.
    :param model: Model to use for inference (default: gpt-4).
    :param top_p: Nucleus sampling probability (default: 0.95).
    :param frequency_penalty: Penalty for frequent tokens (default: 1.03).
    :param temperature: Controls randomness (default: 0.01).
    :param max_tokens: Maximum tokens to generate (default: 512).
    :param organization: Optional organization ID.
    :param cache: Optional cache settings.
    :param verbose: If True, prints additional logs.
    :return: AI response text or an error message.
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "verbose": True,
    }
    
    # Add optional parameters if they are provided
    if organization:
        payload["organization"] = organization
    if cache is not None:
        payload["cache"] = cache

    if verbose:
        print("Sending request with payload:", payload)

    try:
        response = requests.post(f"{url}/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
    
    except requests.exceptions.RequestException as e:
        return f"Request failed: {e}"

def analyze_openshift_log(log_summary):
    """Calls OpenShift's dedicated LLM."""
    messages = [
        {"role": "system", "content": OPENSHIFT_PROMPT["system"]},
        {"role": "user", "content": OPENSHIFT_PROMPT["user"].format(summary=log_summary)},
        {"role": "assistant", "content": OPENSHIFT_PROMPT["assistant"]}
    ]
    response = ask_inference_api(messages=messages, url=INFERENCE_ENDPOINTS["OpenShift"], api_token=INFERENCE_TOKENS["OpenShift"], model=MODEL_MAP["OpenShift"], max_tokens=1024)
    return response

def analyze_ansible_log(log_summary):
    """Calls Ansible's dedicated LLM."""
    messages = [
        {"role": "system", "content": ANSIBLE_PROMPT["system"]},
        {"role": "user", "content": ANSIBLE_PROMPT["user"].format(summary=log_summary)},
        {"role": "assistant", "content": ANSIBLE_PROMPT["assistant"]}
    ]
    response = ask_inference_api(messages=messages, url=INFERENCE_ENDPOINTS["Ansible"], api_token=INFERENCE_TOKENS["Ansible"], model=MODEL_MAP["Ansible"], max_tokens=1024)
    return response

def analyze_generic_log(log_summary):
    """Calls a general-purpose LLM for logs that don’t match OpenShift or Ansible."""
    messages = [
        {"role": "system", "content": GENERIC_APP_PROMPT["system"]},
        {"role": "user", "content": GENERIC_APP_PROMPT["user"].format(summary=log_summary)},
        {"role": "assistant", "content": GENERIC_APP_PROMPT["assistant"]}
    ]
    response = ask_inference_api(messages=messages, url=INFERENCE_ENDPOINTS["Generic"], api_token=INFERENCE_TOKENS["Generic"], model=MODEL_MAP["Generic"], max_tokens=1024)
    return response
