import os
from niva_app.lib.aws_secrets import get_env_var

NIVA_APP_VERSION = "0.0.1"

# Redis configuration
REDIS_HOST = get_env_var("REDIS_HOST", "")
REDIS_PORT = 6379

LOCAL_REDIS_HOST = os.environ.get("LOCAL_REDIS_HOST")
LOCAL_REDIS_PORT = os.environ.get("LOCAL_REDIS_PORT")

# Database configuration
DB_NAME = get_env_var("DB_NAME", "")
DB_USER = get_env_var("DB_USER", "")
DB_PASSWORD = get_env_var("DB_PASSWORD", "")
DB_HOST = get_env_var("DB_HOST", "")
DB_PORT = 5432

LOCAL_DB_NAME = os.environ.get("LOCAL_DB_NAME")
LOCAL_DB_USER = os.environ.get("LOCAL_DB_USER")
LOCAL_DB_PASSWORD = os.environ.get("LOCAL_DB_PASSWORD")
LOCAL_DB_HOST = os.environ.get("LOCAL_DB_HOST")
LOCAL_DB_PORT = os.environ.get("LOCAL_DB_PORT")

# Pipecat configuration
PIPECAT_AGENTS_URL = "http://localhost:8000/api/v1/pipecat/"
PIPECAT_BOT_API_TOKEN = get_env_var("PIPECAT_BOT_API_TOKEN", "")
NIVA_APP_URL = "http://localhost:8000/api/v1/agent/"

# AWS configuration
AWS_BUCKET_NAME = get_env_var("AWS_BUCKET_NAME", "niva-ai-bucket")
AWS_ACCESS_KEY_ID = get_env_var("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = get_env_var("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = get_env_var("AWS_REGION", "eu-central-1")

# API Keys
GOOGLE_GEMINI_API_KEY = get_env_var("GOOGLE_GEMINI_API_KEY", "")  # Kept for backward compatibility
GROQ_API_KEY = get_env_var("GROQ_API_KEY", "")
DEEPGRAM_STT_KEY = get_env_var("DEEPGRAM_STT_KEY", "")