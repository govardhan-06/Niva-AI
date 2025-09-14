import os

NIVA_APP_VERSION = "0.0.1"

REDIS_HOST = os.getenv("REDIS_HOST") or ""
REDIS_PORT = os.getenv("REDIS_PORT") or ""

DB_NAME=os.getenv("DB_NAME") or ""
DB_USER=os.getenv("DB_USER") or ""
DB_PASSWORD=os.getenv("DB_PASSWORD") or ""
DB_HOST=os.getenv("DB_HOST") or ""
DB_PORT=os.getenv("DB_PORT") or ""

PIPECAT_AGENTS_URL=os.getenv("PIPECAT_AGENTS_URL") or ""
PIPECAT_BOT_API_TOKEN=os.getenv("PIPECAT_BOT_API_TOKEN") or ""
NIVA_APP_URL=os.getenv("NIVA_APP_URL") or ""

AWS_BUCKET_NAME=os.getenv("AWS_BUCKET_NAME") or "niva-ai-bucket"
AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID") or ""
AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY") or ""
AWS_REGION=os.getenv("AWS_REGION") or "eu-central-1"

GOOGLE_GEMINI_API_KEY= os.getenv('GOOGLE_GEMINI_API_KEY') or ""

DEEPGRAM_STT_KEY=os.getenv("DEEPGRAM_STT_KEY") or ""