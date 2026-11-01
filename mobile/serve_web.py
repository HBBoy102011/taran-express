# -*- coding: utf-8 -*-
"""Отдаёт собранную веб-версию по HTTP так, как её увидит телефон.

pygbag-игре нужны правильные MIME-типы (иначе wasm не запустится) и заголовки
Cross-Origin-*, поэтому обычный `python -m http.server` не подходит.

    py mobile/serve_web.py [порт]
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "build", "web")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".wasm": "application/wasm",
    ".data": "application/octet-stream",
    ".apk": "application/octet-stream",
    ".json": "application/json",
    ".png": "image/png",
    ".ogg": "audio/ogg",
    ".ttf": "font/ttf",
}


class Handler(SimpleHTTPRequestHandler):
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def end_headers(self):
        # этим заголовкам браузер верит: страница «изолирована», как на хостинге
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=ROOT))
print(f"http://127.0.0.1:{port}/  ->  {ROOT}", flush=True)
srv.serve_forever()
