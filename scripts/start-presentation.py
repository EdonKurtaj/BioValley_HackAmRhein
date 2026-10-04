#!/usr/bin/env python3
"""Build and run the presentation website, API, and source collector together."""

import argparse
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import sys
from threading import Thread
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def open_when_ready(url):
    """Open the website only after the server can serve its built HTML."""
    for _ in range(100):
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (URLError, OSError):
            time.sleep(0.2)
    print(f"Browser did not open automatically. Open {url}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-collector", action="store_true",
                        help="use a separately running API requester")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    npm = shutil.which("npm")
    if not npm:
        parser.error("Node.js/npm is required to build the website.")
    # Fail before building or starting a second collector if a server is running.
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))
    except OSError:
        parser.error(f"Port {args.port} is already in use. Stop the existing server or use --port 8001.")
    os.chdir(PROJECT_ROOT)
    frontend = PROJECT_ROOT / "frontend"
    if not (frontend / "node_modules").is_dir():
        print("Installing the declared frontend dependencies…", flush=True)
        subprocess.run([npm, "ci"], cwd=frontend, check=True)
    print("Building the presentation website…", flush=True)
    subprocess.run([npm, "run", "build"], cwd=frontend, check=True)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Presentation: {url}\nPress Ctrl+C to stop the server and API requester.", flush=True)
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    sys.argv = ["risk_assessment.server", "--port", str(args.port)]
    if args.no_collector:
        sys.argv.append("--no-collector")
    if not args.no_browser:
        Thread(target=open_when_ready, args=(url,), daemon=True).start()
    # Reuse the server's collector lifecycle and Ctrl+C cleanup in this process.
    runpy.run_module("risk_assessment.server", run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print("Website setup/build failed; server was not started.", file=sys.stderr)
        sys.exit(error.returncode)
    except KeyboardInterrupt:
        pass
