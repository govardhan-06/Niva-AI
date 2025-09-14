import os

NIVA_APP_VERSION = "0.0.1"

NIVA_HOST_PROTOCOL = os.getenv("NIVA_HOST_PROTOCOL") or ""
NIVA_HOST = os.getenv("NIVA_HOST") or ""  #TODO: Change to actual host for production

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or ""
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or ""
TWILIO_NUMBER_BUY_MASETER_CODE = os.getenv("TWILIO_NUMBER_BUY_MASETER_CODE") or ""

RINGING_TIMEOUT=os.getenv("RINGING_TIMEOUT") or ""

REDIS_HOST = os.getenv("REDIS_HOST") or ""
REDIS_PORT = os.getenv("REDIS_PORT") or ""

DB_NAME=os.getenv("DB_NAME") or ""
DB_USER=os.getenv("DB_USER") or ""
DB_PASSWORD=os.getenv("DB_PASSWORD") or ""
DB_HOST=os.getenv("DB_HOST") or ""
DB_PORT=os.getenv("DB_PORT") or ""

# PIPECAT_AGENTS_URL=os.getenv("PIPECAT_AGENTS_URL") or ""
PIPECAT_BOT_API_TOKEN=os.getenv("PIPECAT_BOT_API_TOKEN") or ""
# NIVA_APP_URL=os.getenv("NIVA_APP_URL") or ""
PIPECAT_AGENTS_URL="http://localhost:8000/api/v1/pipecat/"
NIVA_APP_URL="http://localhost:8000/api/v1/agent/"
PIPECAT_BOT_API_TOKEN="pipecat_a1b2c3d4e5f67890abcdef1234567890"

GCS_BUCKET_NAME = os.getenv('GCP_BUCKET_NAME') or ""
GCS_BASE_URL = os.getenv('GCS_BASE_URL') or ""
GCP_SA_KEY = os.getenv('GCP_SA_KEY') or ""
GCP_BUCKET_URL = os.getenv('GCP_BUCKET_URL') or ""

GOOGLE_GEMINI_API_KEY= os.getenv('GOOGLE_GEMINI_API_KEY') or ""
GOOGLE_GEMINI_API_KEY="AIzaSyCCqDsolu3XWOTek_5Gpn0aqja7R7HaJcw"

DEEPGRAM_STT_KEY="146d146072f987a39b566e3b8851bab7aaef5783"

FRONTEND_URL=""
