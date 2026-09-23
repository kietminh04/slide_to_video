"""Local Studio Server cho CLSG Multi-Agent Studio.

Sử dụng Python standard library (http.server) để phục vụ giao diện và REST API,
không phụ thuộc vào framework ngoài, bảo mật 100% không lộ API key.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    """Xử lý HTTP requests cho CLSG Studio đa luồng."""

    def log_message(self, format, *args):
        # Log gọn gàng
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        url_path = urllib.parse.unquote(self.path.split("?")[0])

        if url_path in ("/", "/index.html"):
            index_path = ROOT_DIR / "studio" / "index.html"
            content = index_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")
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

        # Phục vụ file tĩnh (output_test.docx, output_clustering, v.v.)
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
        import urllib.parse
        url_path = urllib.parse.unquote(self.path.split("?")[0])
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        if url_path == "/api/export/docx":
            try:
                data = json.loads(body)
                raw_scenes = data.get("scenes", [])
                doc_name = data.get("filename", "bai_giang_script.docx")

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
                        doc_id=data.get("doc_id", "lecture_script"),
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
                self.send_header("Content-Disposition", f'attachment; filename="{doc_name}"')
                self.send_header("Content-Length", str(len(docx_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(docx_bytes)
                return

            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                return

        if url_path == "/api/generate":
            try:
                import base64
                data = json.loads(body)
                filename = data.get("filename", "tai_lieu_hoc.pdf")
                file_b64 = data.get("file_base64", "")
                proj_name = data.get("project_name", "")
                proj_desc = data.get("project_desc", "")
                target_duration = int(data.get("target_duration", 300))
                target_wpm = int(data.get("target_wpm", 140))

                uploads_dir = ROOT_DIR / "studio" / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                target_file = uploads_dir / filename

                if file_b64:
                    if "," in file_b64:
                        file_b64 = file_b64.split(",", 1)[1]
                    target_file.write_bytes(base64.b64decode(file_b64))
                elif not target_file.exists():
                    candidate = ROOT_DIR / filename
                    if candidate.exists():
                        target_file = candidate
                    else:
                        raise ValueError(f"Không tìm thấy tệp {filename} và không có dữ liệu tải lên.")

                from codebase.clsg.studio_generator import generate_studio_project
                proj_data = generate_studio_project(
                    target_file,
                    project_name=proj_name or None,
                    project_desc=proj_desc or None,
                    target_duration_s=target_duration,
                    target_wpm=target_wpm,
                )

                self._send_json(proj_data)
                return
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
                return

        if url_path == "/api/llm/ping":
            try:
                import time
                import urllib.request
                settings = get_settings()
                if not settings.openai_api_key:
                    self._send_json({"error": "Chưa cấu hình OPENAI_API_KEY trong .env"}, status=400)
                    return
                t0 = time.time()
                payload = json.dumps({
                    "model": settings.model_cheap or "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Ping"}],
                    "max_tokens": 2
                }).encode("utf-8")
                base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.openai_api_key}"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    latency = round((time.time() - t0) * 1000)
                    self._send_json({"status": "ok", "latency": latency, "provider": "OpenAI Official"})
                    return
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                return

        if url_path == "/api/llm/chat":
            try:
                import urllib.request
                settings = get_settings()
                req_json = json.loads(body) if body else {}
                client_key = req_json.get("apiKey") or settings.openai_api_key
                client_base = req_json.get("baseUrl") or settings.openai_base_url or "https://api.openai.com/v1"
                
                # Bỏ các trường metadata client trước khi chuyển tiếp sang API LLM
                forward_body = {k: v for k, v in req_json.items() if k not in ["apiKey", "baseUrl", "provider"]}
                
                if not client_key:
                    self._send_json({"error": "Chưa cấu hình API Key. Hãy nhập API Key trong Cấu Hình AI hoặc file .env"}, status=400)
                    return
                    
                base_url = client_base.rstrip("/")
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {client_key}"
                }
                
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=json.dumps(forward_body).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    self._send_json(resp_data)
                    return
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                return

        self.send_error(404, "Endpoint Not Found")


def run_studio_server(port: int = 8765):
    server = ThreadingHTTPServer(("0.0.0.0", port), StudioHandler)
    server.daemon_threads = True
    print("=" * 60)
    print(f"🚀 CLSG Multi-Agent Studio Server (Multi-threaded) đang chạy tại:")
    print(f"👉 http://127.0.0.1:{port}")
    print("=" * 60)
    print("Nhấn Ctrl+C để dừng server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_studio_server(port)
