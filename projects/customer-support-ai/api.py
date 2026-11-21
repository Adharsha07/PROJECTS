"""Local development HTTP API. Not a production server."""
import argparse
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from support import respond
from validation import checked_answer

MAX_BODY = 16384
CONTEXT_KEYS = {"purchase_date", "delivery_date", "country", "category"}

class RequestError(ValueError):
    pass

def answer_request(payload, generator=None):
    """A future trusted server-side generator may supply proposed facts."""
    if not isinstance(payload, dict) or set(payload) - {"question", "context"}:
        raise RequestError("Use only question and optional context fields.")
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise RequestError("question must be nonempty text of at most 2000 characters.")
    context = payload.get("context", {})
    if not isinstance(context, dict) or set(context) - CONTEXT_KEYS:
        raise RequestError("context must contain supported purchase-detail fields only.")
    if any(not isinstance(v, str) or len(v) > 100 for v in context.values()):
        raise RequestError("Context values must be text of at most 100 characters.")
    context = {k: v.strip() for k, v in context.items() if v.strip()}
    evidence = respond(question.strip(), context)
    if evidence["status"] != "answered":
        return dict(evidence, validation="not_applicable", generation="disabled")
    if generator is None:
        return dict(evidence, validation="verified_passage", generation="disabled")
    try:
        candidate = generator(evidence)
    except Exception:
        return dict(evidence, validation="fallback", generation="failed",
                    validation_reason="Generation failed; returning retrieved evidence.")
    return dict(checked_answer(evidence, candidate), generation="structured")

class Handler(BaseHTTPRequestHandler):
    server_version = "PolicyDemo"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def send_json(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/api/answer"):
            data = (Path(__file__).parent / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/health":
            return self.send_json(200, {"status": "ok", "model_connected": False})
        self.send_json(404, {"error": "Route not found."})

    def do_POST(self):
        self.close_connection = True
        if self.path != "/api/answer":
            return self.send_json(404, {"error": "Route not found."})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.send_json(415, {"error": "Send application/json."})
        if self.headers.get("Transfer-Encoding"):
            return self.send_json(400, {"error": "Chunked requests are not supported."})
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.send_json(400, {"error": "Valid Content-Length required."})
        if length <= 0:
            return self.send_json(400, {"error": "Request body required."})
        if length > MAX_BODY:
            return self.send_json(413, {"error": "Request body is too large."})
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self.send_json(400, {"error": "Incomplete request body."})
            payload = json.loads(raw)
            result = answer_request(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, RequestError, RecursionError):
            return self.send_json(400, {"error": "Invalid JSON or request fields."})
        except (TimeoutError, OSError):
            return self.send_json(408, {"error": "Request timed out."})
        except Exception:
            return self.send_json(500, {"error": "Policy service failed; no answer produced."})
        self.send_json(422 if result["status"] == "invalid_input" else 200, result)

    def log_message(self, *_):
        # Never log questions or customer context in this local prototype.
        pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Local policy API: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
