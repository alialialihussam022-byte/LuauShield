from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from luau_obfuscator import ObfuscationError, obfuscate

ROOT = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/styles.css":
            self._send(200, (ROOT / "styles.css").read_bytes(), "text/css; charset=utf-8")
        elif self.path == "/app.js":
            self._send(200, (ROOT / "app.js").read_bytes(), "text/javascript; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/obfuscate":
            self._send(404, '{"error":"Not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            result = obfuscate(payload.get("source", ""), payload.get("mode", "safe-strings"), payload.get("seed"))
            self._send(200, json.dumps({"code": result.code, "changed": result.changed, "warnings": result.warnings}))
        except (ObfuscationError, ValueError, json.JSONDecodeError) as exc:
            self._send(400, json.dumps({"error": str(exc)}))
        except Exception as exc:
            self._send(500, json.dumps({"error": f"Unexpected server error: {exc}"}))


if __name__ == "__main__":
    print("LuauShield running at http://localhost:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()