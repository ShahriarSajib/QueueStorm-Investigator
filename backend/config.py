import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-1.5-flash")
PORT: int = int(os.getenv("PORT", "8000"))