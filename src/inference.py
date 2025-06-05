import requests


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

def analyze_log(product, product_config):
    """Returns a callable that analyzes logs for a given product."""
    def _wrapped(log_summary):
        messages = [
            {"role": "system", "content": product_config["prompt"][product]["system"]},
            {"role": "user", "content": product_config["prompt"][product]["user"].format(summary=log_summary)},
            {"role": "assistant", "content": product_config["prompt"][product]["assistant"]}
        ]

        return ask_inference_api(
            messages=messages, 
            url=product_config["endpoint"][product], 
            api_token=product_config["token"][product], 
            model=product_config["model"][product], 
            max_tokens=1024
        )
    return _wrapped
