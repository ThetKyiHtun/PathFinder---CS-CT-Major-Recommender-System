"""Local API Gateway stand-in for PathFinder.

Serves the AWS Lambda handler over HTTP so the React client can be tested
end-to-end without AWS. Standard library only.

Usage:
    python local_server.py [port]

Endpoints:
    POST /recommend   -> invokes lambda_handler.lambda_handler
    OPTIONS /recommend -> CORS preflight (Access-Control-Allow-Origin: *)
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lambda"))

import lambda_handler  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    server_version = "PathFinderLocal/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        if self.path.split("?")[0] != "/recommend":
            self.send_error(404)
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path.split("?")[0] != "/recommend":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"

        event = {"body": raw, "headers": dict(self.headers)}
        response = lambda_handler.lambda_handler(event, {})
        body = response["body"].encode("utf-8")

        self.send_response(response["statusCode"])
        for key, value in response.get("headers", {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3001
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("PathFinder local API listening on http://localhost:%d/recommend" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
