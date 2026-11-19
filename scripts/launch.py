"""Prepare private local tools, then run the UI and API as one service."""

import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "data" / "launcher"
NODE_VERSION = "24.22.3"
NODE_HASHES = {
    "win-x64.zip": "e612af99f626ab415ea225af6bce5c971feb448cb5cae250bb1c3fa50c5f7d9f",
    "win-arm64.zip": "b3cc74a295b39d4f273271e96f58c06dd2b35757ca12abec64c7d0598b434f14",
    "darwin-x64.tar.gz": "977614af0504c81045e7fd85596dbca0e5f951b96681516dadafedcca8c447f7",
    "darwin-arm64.tar.gz": "ff6e17d4874b76d272212b908cc020d6e815fba5a6c7eaaa06add725840307fd",
}
PNPM_VERSION = "10.11.0"
PNPM_SHA512 = "ZUBYP0HMX2KOs9l3Ps7oAvT575kjzEW2mJD7R5kdSwkpZGlOw6T3OKQgyRijMwYsi5JdMS9C5PDCY+tgNVH5dw=="
CREATE_HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def say(message):
    print(message, flush=True)


def run(args, *, cwd=ROOT, env=None):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, creationflags=CREATE_HIDDEN)
    if result.returncode:
        raise RuntimeError("安装或准备步骤失败，请检查上方提示和网络后重新启动。")


def download(url, destination, expected, algorithm="sha256"):
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            digest = hashlib.new(algorithm, destination.read_bytes()).digest()
            actual = base64.b64encode(digest).decode() if algorithm == "sha512" else digest.hex()
            if actual != expected:
                raise RuntimeError("下载文件校验失败，请重新运行。")
            return
        except (OSError, urllib.error.URLError):
            if attempt == 2:
                raise RuntimeError("下载失败，请检查网络后重新运行。") from None
            time.sleep(1)


def prepare_node():
    # Use a working system Node when available; otherwise keep it project-local.
    system = shutil.which("node")
    if system:
        result = subprocess.run([system, "--version"], capture_output=True, text=True, creationflags=CREATE_HIDDEN)
        try:
            if result.returncode == 0 and int(result.stdout.strip().lstrip("v").split(".")[0]) >= 20:
                return Path(system)
        except ValueError:
            pass
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    suffix = ("win-" + arch + ".zip") if os.name == "nt" else ("darwin-" + arch + ".tar.gz")
    folder = TOOLS / ("node-v" + NODE_VERSION + "-" + suffix.removesuffix(".tar.gz").removesuffix(".zip"))
    node = folder / ("node.exe" if os.name == "nt" else "bin/node")
    if not node.is_file():
        say("正在准备网页运行组件……")
        archive = TOOLS / ("node-" + suffix)
        download("https://nodejs.org/dist/v" + NODE_VERSION + "/node-v" + NODE_VERSION + "-" + suffix, archive, NODE_HASHES[suffix])
        if os.name == "nt":
            with zipfile.ZipFile(archive) as contents:
                contents.extractall(TOOLS)
        else:
            with tarfile.open(archive) as contents:
                contents.extractall(TOOLS, filter="data")
        archive.unlink()
    return node


def prepare_pnpm():
    script = TOOLS / "pnpm" / "package" / "bin" / "pnpm.cjs"
    if not script.is_file():
        archive = TOOLS / "pnpm.tgz"
        download("https://registry.npmjs.org/pnpm/-/pnpm-" + PNPM_VERSION + ".tgz", archive, PNPM_SHA512, "sha512")
        script.parent.parent.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as contents:
            contents.extractall(TOOLS / "pnpm", filter="data")
        archive.unlink()
    return script


def fingerprint(paths):
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def needs_portable_ocr():
    # Paddle's native model loader cannot reliably open Unicode Windows paths.
    return (sys.platform == "darwin" and platform.machine() == "x86_64") or (os.name == "nt" and not str(ROOT).isascii())


def read_key():
    # Preserve developer .env files and existing settings; never print a key.
    from dotenv import dotenv_values

    values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
    key_path = ROOT / "data" / "deepseek-api-key.txt"
    key = os.environ.get("DEEPSEEK_API_KEY") or values.get("DEEPSEEK_API_KEY", "")
    existing_file = os.environ.get("DEEPSEEK_API_KEY_FILE") or values.get("DEEPSEEK_API_KEY_FILE")
    if not key and existing_file:
        source = Path(existing_file).expanduser()
        if not source.is_absolute():
            source = ROOT / source
        try:
            key = source.read_text(encoding="utf-8-sig").strip()
        except OSError:
            pass
    if not key and key_path.exists():
        key = key_path.read_text(encoding="utf-8-sig").strip()
    if not key:
        say("首次使用：请粘贴 DeepSeek 密钥，输入时不会显示，按回车确认。")
        key = getpass.getpass("DeepSeek API key: ").strip()
        if not key.startswith("sk-") or any(c.isspace() for c in key):
            raise RuntimeError("密钥格式不正确，请重新启动并粘贴完整密钥。")
        key_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(key + "\n")
    key = key.strip()
    if not key or any(c.isspace() for c in key):
        raise RuntimeError("已保存的密钥格式不正确，请检查本机配置或 data/deepseek-api-key.txt。")
    return key, values


def check_key(key):
    # Listing models does not generate text or consume completion tokens.
    request = urllib.request.Request("https://api.deepseek.com/models", headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            models = json.load(response).get("data", [])
        if "deepseek-flash" not in {model.get("id") for model in models}:
            raise RuntimeError("此账户的模型列表未包含 deepseek-flash，请联系项目维护者。")
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise RuntimeError("DeepSeek 密钥无效或无访问权限。请在 data/deepseek-api-key.txt 中更换密钥后重试。") from None
        raise RuntimeError("DeepSeek 暂时无法连接，请稍后重新启动。") from None
    except (OSError, ValueError):
        raise RuntimeError("无法连接 DeepSeek，请检查网络后重新启动。") from None


def available_port():
    for port in range(5180, 5200):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                pass
    raise RuntimeError("网页端口被占用，请关闭之前的启动窗口后重试。")


def request_json(url):
    with urllib.request.urlopen(url, timeout=1) as response:
        return json.load(response)


def open_existing(*, demo=False, no_browser=False):
    try:
        instance = json.loads((TOOLS / "running.json").read_text(encoding="utf-8"))
        port = int(instance["port"])
        if not 5180 <= port < 5200:
            return False
        url = "http://127.0.0.1:" + str(port)
        status = request_json(url + "/__launcher/status")
        if status.get("instance") != instance["id"]:
            return False
        if request_json(url + "/health").get("mode") != ("demo" if demo else "live"):
            raise RuntimeError("另一种模式正在运行，请先关闭上次的启动窗口。")
        if not no_browser:
            webbrowser.open(url)
        say("网页已经在运行：" + url)
        return True
    except (OSError, ValueError, KeyError):
        return False


def serve(python, env, *, no_browser=False, stop_after=0):
    port, instance_id = available_port(), uuid.uuid4().hex
    env = dict(env, MARKETING_COURT_LAUNCH_ID=instance_id)
    url = "http://127.0.0.1:" + str(port)
    log_path = TOOLS / "server.log"
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(python), str(ROOT / "scripts/local_server.py"), str(port), "--managed"], cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=log, stderr=log, creationflags=CREATE_HIDDEN)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("服务未能启动，请将 data/launcher/server.log 发给维护者查看。")
                try:
                    if request_json(url + "/__launcher/status").get("instance") == instance_id:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.3)
            else:
                raise RuntimeError("启动超时，请查看 data/launcher/server.log。")
            (TOOLS / "running.json").write_text(json.dumps({"id": instance_id, "port": port}), encoding="utf-8")
            say("已启动：" + url + "\n请保持本窗口打开，退出时按 Ctrl+C。")
            if not no_browser:
                webbrowser.open(url)
            if stop_after:
                time.sleep(stop_after)
            else:
                process.wait()
                raise RuntimeError("服务已退出，请查看 data/launcher/server.log 后重新启动。")
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        (TOOLS / "running.json").unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Use isolated demo data without a model key")
    parser.add_argument("--stop-after", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    TOOLS.mkdir(parents=True, exist_ok=True)
    if not args.serve:
        if open_existing(demo=args.demo, no_browser=args.no_browser):
            return
        say("Marketing Court 一键启动\n首次准备可能需要几分钟，请保持联网。")
        env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(ROOT / ".venv"))
        portable_ocr = needs_portable_ocr()
        if sys.platform == "darwin" and portable_ocr and int(platform.mac_ver()[0].split(".")[0]) < 13:
            raise RuntimeError("这台 Intel Mac 需要升级到 macOS 13 或以上，才能安装图片文字识别组件。")
        extra = "ocr-portable" if portable_ocr else "ocr"
        signature = fingerprint([ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "vendor/tinytroupe/pyproject.toml"]) + extra
        marker = TOOLS / "backend-ready.txt"
        python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.exists() or not marker.exists() or marker.read_text() != signature:
            say("正在准备审核与数字人像组件……")
            python_request = "cpython-3.12-windows-x86_64-none" if os.name == "nt" else "3.12"
            run([args.uv, "sync", "--locked", "--python", python_request, "--no-dev", "--extra", extra], env=env)
            marker.write_text(signature)
        command = [python, Path(__file__), "--uv", args.uv, "--serve"]
        if args.no_browser:
            command.append("--no-browser")
        if args.demo:
            command.append("--demo")
        if args.stop_after:
            command.extend(["--stop-after", str(args.stop_after)])
        # Keep the credential prompt attached to the visible launcher console.
        # Inheriting its process group lets Ctrl+C stop both launchers cleanly.
        result = subprocess.run([str(arg) for arg in command], cwd=ROOT, env=env)
        if result.returncode:
            raise RuntimeError("启动未完成，请查看上方提示后重新运行。")
        return

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if args.demo:
        key, values = "", {}
        data_root = ROOT / "data" / "launcher-demo"
        env.update(DATABASE_PATH=str(data_root / "review.sqlite3"), JURY_DB_PATH=str(data_root / "jury.sqlite3"), STORAGE_DIR=str(data_root / "uploads"))
    else:
        key, values = read_key()
        env = dict(values, **env)
        say("正在检查 DeepSeek 连接……")
        check_key(key)
    env.update(MARKETING_COURT_MODE="demo" if args.demo else "live", MARKETING_COURT_DEEPSEEK_MODEL="deepseek-flash", DEEPSEEK_API_KEY=key)
    node = prepare_node()
    env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")
    frontend = ROOT / "frontend"
    sources = [p for folder in [frontend / "src", frontend / "public", frontend / "review", frontend / "jury"] for p in folder.rglob("*") if p.is_file()]
    sources += list(frontend.glob("*.html")) + list(frontend.glob("*.json")) + [frontend / "pnpm-lock.yaml", frontend / "vite.config.ts"]
    signature = fingerprint(sources)
    marker = TOOLS / "frontend-ready.txt"
    if not marker.exists() or marker.read_text() != signature or not (frontend / "dist/index.html").exists():
        say("正在准备网页……")
        pnpm = prepare_pnpm()
        run([node, pnpm, "install", "--frozen-lockfile"], cwd=frontend, env=env)
        run([node, pnpm, "build"], cwd=frontend, env=env)
        marker.write_text(signature)
    python = Path(sys.executable)
    if not args.demo:
        env["MARKETING_COURT_OCR_ENGINE"] = "onnx" if needs_portable_ocr() else "paddle"
        marker = TOOLS / ("ocr-ready-" + env.get("MARKETING_COURT_OCR_ENGINE", "paddle"))
        if not marker.exists():
            say("正在准备图片文字识别并检查坐标，首次需要下载模型……")
            run([python, ROOT / "scripts/warmup-ocr.py"], env=env)
            marker.write_text("ready")
    serve(python, env, no_browser=args.no_browser, stop_after=args.stop_after)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\n已停止，项目数据已保存在本机。")
    except Exception as error:
        # Do not dump request objects, headers or credentials on a failure.
        say("\n" + (str(error) if isinstance(error, RuntimeError) else "启动未完成，请检查网络和文件权限后重试。"))
        sys.exit(1)
