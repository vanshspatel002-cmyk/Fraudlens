import http.server
import os
import socketserver
import urllib.error
import urllib.request

BACKEND = "http://127.0.0.1:5000"


class Handler(http.server.SimpleHTTPRequestHandler):
    def _proxy(self):
        target = BACKEND + self.path
        length = int(self.headers.get("Content-Length", "0") or 0)
        data = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "connection", "content-length"}
        }
        request = urllib.request.Request(target, data=data, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
                self.send_response(response.status)
                self._copy_headers(response.headers)
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as error:
            body = error.read()
            self.send_response(error.code)
            self._copy_headers(error.headers)
            self.end_headers()
            self.wfile.write(body)
        except Exception as error:
            body = f"Proxy error: {error}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _copy_headers(self, headers):
        for key, value in headers.items():
            if key.lower() not in {"transfer-encoding", "connection"}:
                self.send_header(key, value)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()

        path = self.translate_path(self.path)
        if self.path != "/" and not os.path.exists(path):
            self.path = "/index.html"

        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy()

        self.send_error(404)

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            return self._proxy()

        self.send_response(204)
        self.end_headers()


with socketserver.TCPServer(("127.0.0.1", 5173), Handler) as httpd:
    print("Static site ready at http://127.0.0.1:5173/", flush=True)
    httpd.serve_forever()
