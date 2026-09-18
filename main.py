"""Root entrypoint for QA Agent.

Usage:
    python main.py             # Launches the Web Dashboard at http://127.0.0.1:8000
    python main.py --cli --help # Runs in Command-Line Mode
"""

import os
import sys
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if available
load_dotenv()

# Ensure current directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from qa_agent.cli.main import run_cli
        run_cli()
    else:
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "127.0.0.1")
        url = f"http://{host}:{port}"

        print("=" * 65)
        print("  QA AI Agent - Autonomous Polyglot Test Suite Generator")
        print(f"  Web Dashboard: {url}")
        print(f"  CLI Mode:      python main.py --cli --help")
        print("=" * 65)

        # Open web browser after a brief delay
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(url)

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

        uvicorn.run("qa_agent.server.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

