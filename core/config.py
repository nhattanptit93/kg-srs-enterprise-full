import os
from dotenv import load_dotenv

load_dotenv()

SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "8"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
