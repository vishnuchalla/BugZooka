import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

INFERENCE_ENDPOINTS = {
    "Ansible": os.getenv("ANSIBLE_INFERENCE_URL", "https://deepseek-r1-distill-qwen-14b-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "OpenShift": os.getenv("OPENSHIFT_INFERENCE_URL", "https://mistral-7b-instruct-v0-3-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "Docling": os.getenv("DOCLING_INFERENCE_URL", "https://docling-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "Generic": os.getenv("GENERIC_INFERENCE_URL", "https://mistral-7b-instruct-v0-3-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
}

INFERENCE_TOKENS = {
    "Ansible": os.getenv("ANSIBLE_INFERENCE_TOKEN", ""),
    "OpenShift": os.getenv("OPENSHIFT_INFERENCE_TOKEN", ""),
    "Docling": os.getenv("DOCLING_INFERENCE_TOKEN", ""),
    "Generic": os.getenv("GENERIC_INFERENCE_TOKEN", ""),
}