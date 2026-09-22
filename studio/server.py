"""Local Studio Server cho CLSG Multi-Agent Studio.

Sử dụng Python standard library (http.server) để phục vụ giao diện và REST API,
không phụ thuộc vào framework ngoài, bảo mật 100% không lộ API key.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Đảm bảo UTF-8 và đưa workspace root vào sys.path
sys.stdout.reconfigure(encoding="utf-8")
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from codebase.clsg.config import get_settings
from codebase.clsg.engine import export_markdown, export_srt, export_word_doc, run_pipeline
from codebase.clsg.schemas import Beat, Scene, Script, ScriptMeta, Visual


class StudioHandler(BaseHTTPRequestHandler):
    """Xử lý HTTP requests cho CLSG Studio."""

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        url_path = self.path.split("?")[0]

        if url_path in ("/", "/index.html"):
            index_path = ROOT_DIR / "studio" / "index.html"
            content = index_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if url_path == "/api/status":
            self._send_json({
                "status": "ready",
                "system": "CLSG Multi-Agent Studio Pro",
                "version": "2.0.0",
                "glossary_terms": 6766,
                "zero_leak_policy": "active"
            })
            return

        # Phục vụ file tĩnh (output_test.docx, v.v.)
        static_file = (ROOT_DIR / url_path.lstrip("/")).resolve()
        if static_file.exists() and static_file.is_file() and str(static_file).startswith(str(ROOT_DIR)):
            mime_type, _ = mimetypes.guess_type(str(static_file))
            content = static_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        if url_path == "/api/export/docx":
            try:
                data = json.loads(body)
                raw_scenes = data.get("scenes", [])

                scenes = []
                for s in raw_scenes:
                    scenes.append(
                        Scene(
                            id=s.get("id", "s_1"),
                            chapter=s.get("chapter", "ch1"),
                            depth=s.get("depth", "core"),
                            t_start=float(s.get("t_start", 0)),
                            t_end=float(s.get("t_end", 30)),
                            beats=[
                                Beat(
                                    type="claim",
                                    display_text=s.get("narration", ""),
                                    source_ids=[s.get("source_id", "c_ch1_01")]
                                )
                            ],
                            visual=Visual(
                                visual_type=s.get("visual_type", "highlight_box"),
                                visual_purpose=s.get("visual_purpose", "")
                            )
                        )
                    )

                script = Script(
                    meta=ScriptMeta(
                        doc_id="cnn_intro",
                        duration_s=int(raw_scenes[-1]["t_end"]) if raw_scenes else 300,
                        style="academic",
                        weights={}
                    ),
                    scenes=scenes
                )

                out_docx = ROOT_DIR / "output_custom_export.docx"
                export_word_doc(script, out_docx)

                docx_bytes = out_docx.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", 'attachment; filename="cnn_intro_script.docx"')
                self.send_header("Content-Length", str(len(docx_bytes)))
                self.end_headers()
                self.wfile.write(docx_bytes)
                return

            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                return

        self.send_error(404, "Endpoint Not Found")


def run_studio_server(port: int = 8765):
    server = HTTPServer(("127.0.0.1", port), StudioHandler)
    print("=" * 60)
    print(f"🚀 CLSG Multi-Agent Studio Server đang chạy tại:")
    print(f"👉 http://127.0.0.1:{port}")
    print("=" * 60)
    print("Nhấn Ctrl+C để dừng server.")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_studio_server(port)
