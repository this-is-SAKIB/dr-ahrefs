#!/usr/bin/env python3
"""Serve the standalone checker with a localhost-only Ahrefs proxy.

This avoids browser CORS restrictions without putting an API key in a public
site. The key is sent from the browser to localhost for the current request
and is never stored by this server.
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ahrefs_dr import ApiFailure, request_ratings  # noqa: E402


class CheckerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def log_message(self, format, *args):
        # Do not log request headers or bodies, which could contain the key.
        sys.stderr.write("localhost: " + (format % args) + "\n")

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if self.path != "/api/check":
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/check":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request_body = json.loads(self.rfile.read(length).decode("utf-8"))
            api_key = str(request_body.get("api_key", "")).strip()
            targets = request_body.get("targets", [])
            version = str(request_body.get("version", "dr3"))
            if not api_key:
                self.send_json(400, {"error": "No Ahrefs API key supplied."})
                return
            if version not in {"dr3", "dr4"}:
                self.send_json(400, {"error": "Version must be dr3 or dr4."})
                return
            if not isinstance(targets, list) or not targets or len(targets) > 1000:
                self.send_json(400, {"error": "Targets must be a non-empty list of at most 1,000 items."})
                return
            ratings = request_ratings([str(target) for target in targets], api_key, version)
            browser_ratings = {
                key: {"target": value.get("target", ""), "dr": value.get("domain_rating", "")}
                for key, value in ratings.items()
            }
            self.send_json(200, {"ratings": browser_ratings})
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Request body must be valid JSON."})
        except ApiFailure as error:
            message = str(error)
            status = 429 if "HTTP 429" in message else 502
            self.send_json(status, {"error": message})
        except Exception as error:
            self.send_json(500, {"error": str(error)})


class LocalServer(HTTPServer):
    allow_reuse_address = True


def main():
    port = 8765
    server = LocalServer(("127.0.0.1", port), CheckerHandler)
    print(f"Ahrefs DR Checker running at http://127.0.0.1:{port}/index.html")
    print("The server is localhost-only. Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
