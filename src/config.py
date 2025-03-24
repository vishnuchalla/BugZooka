import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", None)
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", None)
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", None)

INFERENCE_ENDPOINTS = {
    "Ansible": os.getenv("ANSIBLE_INFERENCE_URL", "https://mistral-7b-instruct-v0-3-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "OpenShift": os.getenv("OPENSHIFT_INFERENCE_URL", "https://deepseek-r1-distill-qwen-14b-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "Docling": os.getenv("DOCLING_INFERENCE_URL", "https://docling-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
    "Generic": os.getenv("GENERIC_INFERENCE_URL", "https://mistral-7b-instruct-v0-3-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443"),
}

MODEL_MAP = {
    "Ansible": os.getenv("ANSIBLE_MODEL", "mistral-7b-instruct"),
    "OpenShift": os.getenv("OPENSHIFT_MODEL", "deepseek-r1-distill-qwen-14b"),
    "Docling": os.getenv("DOCLING_MODEL", None),
    "Generic": os.getenv("GENERIC_MODEL", "mistral-7b-instruct"),
}

INFERENCE_TOKENS = {
    "Ansible": os.getenv("ANSIBLE_INFERENCE_TOKEN", ""),
    "OpenShift": os.getenv("OPENSHIFT_INFERENCE_TOKEN", ""),
    "Docling": os.getenv("DOCLING_INFERENCE_TOKEN", ""),
    "Generic": os.getenv("GENERIC_INFERENCE_TOKEN", ""),
}
