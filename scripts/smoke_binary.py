#!/usr/bin/env python3
"""Native runtime smoke test for a source-free AIMD release package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive")
    args = p.parse_args()
    package = Path(args.archive).resolve()
    executable = "aimd.exe" if os.name == "nt" else "aimd"
    expected = {executable, "README.txt", "ai.md", "config.example.json"}
    with tempfile.TemporaryDirectory(prefix="aimd-smoke-") as temporary:
        root = Path(temporary)
        if package.suffix == ".zip":
            with zipfile.ZipFile(package) as archive:
                assert set(archive.namelist()) == expected
                for name in expected:
                    (root / name).write_bytes(archive.read(name))
        else:
            with tarfile.open(package) as archive:
                assert set(archive.getnames()) == expected
                for name in expected:
                    member = archive.getmember(name)
                    assert member.isfile()
                    (root / name).write_bytes(archive.extractfile(member).read())
        binary = root / executable
        if os.name != "nt":
            binary.chmod(0o755)
        subprocess.run([str(binary), "-h"], check=True, capture_output=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        token = secrets.token_hex(32)
        config = json.loads((root / "config.example.json").read_text(encoding="utf-8"))
        config.update(listen=f"127.0.0.1:{port}", data_dir=str(root / "data"))
        config["types"] = {"smoke": {"tokens": [{"name": "smoke", "token": token, "permissions": "rw"}]}}
        config["embedding"]["endpoint"] = ""
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        log_path = root / "service.log"
        with log_path.open("wb") as log:
            child = subprocess.Popen([str(binary), "-config", str(config_path)], cwd=root, stdout=log, stderr=log)

            def request(path, *, data=None, content_type=None, authenticated=True):
                headers = {}
                if authenticated:
                    headers["Authorization"] = "Bearer " + token
                if content_type:
                    headers["Content-Type"] = content_type
                req = urllib.request.Request(base + path, data=data, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return response.status, response.read()
                except urllib.error.HTTPError as error:
                    return error.code, error.read()

            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError("server exited: " + log_path.read_text(errors="replace"))
                    try:
                        if request("/ai.md", authenticated=False)[0] == 200:
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(0.1)
                else:
                    raise TimeoutError("server did not start")
                markdown = "# 原生平台验证\n中文知识库 smoke probe\n".encode()
                resource = bytes(range(256))
                boundary = "aimd" + secrets.token_hex(8)
                pieces = []
                for field, filename, data in [("document", "note.md", markdown), ("resources", "asset.bin", resource)]:
                    pieces.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), data, b"\r\n"])
                pieces.append(f"--{boundary}--\r\n".encode())
                payload = b"".join(pieces)
                status, body = request("/upload/smoke", data=payload, content_type=f"multipart/form-data; boundary={boundary}")
                assert status == 201, (status, body)
                doc = json.loads(body)["document"]
                assert request(doc["url"])[1] == markdown
                assert request(doc["resources"][0]["url"])[1] == resource
                status, body = request("/search/smoke?" + urllib.parse.urlencode({"q": "知识", "top_k": 5}))
                assert status == 200 and json.loads(body)["fulltext_results"][0]["file_id"] == doc["file_id"], body
                assert request(doc["url"], authenticated=False)[0] == 401
                status, body = request("/upload/smoke", data=payload, content_type=f"multipart/form-data; boundary={boundary}")
                assert status == 200 and json.loads(body)["duplicate"] is True
                print(json.dumps({"native_smoke": "passed", "platform": os.name,
                                  "asset": package.name, "sha256": hashlib.sha256(package.read_bytes()).hexdigest()}))
            finally:
                child.terminate()
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    main()
