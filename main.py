import os
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(override=True)

from agent import run_agent_loop

if __name__ == "__main__":
    try:
        run_agent_loop()
    except KeyboardInterrupt:
        pass
