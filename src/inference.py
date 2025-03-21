from langchain_community.utilities.requests import RequestsWrapper
from bot.config import INFERENCE_ENDPOINTS, INFERENCE_API_KEY

# Initialize LangChain request wrapper with authentication
requests_wrapper = RequestsWrapper(headers={"Authorization": f"Bearer {INFERENCE_API_KEY}"})

def detect_product(log_text):
    """Uses LLM to classify the product type from the log."""
    endpoint = INFERENCE_ENDPOINTS["Generic"]
    response = requests_wrapper.post(endpoint, json={"log": log_text, "task": "classify"})
    
    return response.get("product", "Generic")  # Default to generic if no classification

def call_inference(log_text, product):
    """Calls the appropriate inference endpoint using LangChain's structured API."""
    endpoint = INFERENCE_ENDPOINTS.get(product, INFERENCE_ENDPOINTS["Generic"])
    
    structured_prompt = {
        "system": f"You are an expert in analyzing {product} logs. Provide actionable insights.",
        "user": f"Here is a log file from {product}. Identify the root cause and suggest fixes:\n\n{log_text}",
        "assistant": "Sure! Here is the analysis of the log:"
    }

    response = requests_wrapper.post(endpoint, json=structured_prompt)
    return response.get("analysis", "No insights available.")  # Default if no response
