import os
import sys
import io
import argparse

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(override=True)

from agent import run_agent_loop

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cwd", default=None)
    args, _ = parser.parse_known_args()

    if args.cwd and os.path.isdir(args.cwd):
        os.chdir(args.cwd)

    try:
        run_agent_loop()
    except KeyboardInterrupt:
        pass
