"""Serve the built UI and the existing API on one loopback-only port."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def create_local_app():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from backend.app.main import create_app

    dist = ROOT / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        raise RuntimeError("页面尚未构建，请通过一键启动入口运行。")
    app = create_app()
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) not in {"/", "/jury"}]

    def frontend_page(relative_path: str):
        # The stable entry URL must always point to the current build's hashed assets.
        return FileResponse(dist / relative_path, headers={"Cache-Control": "no-store"})

    @app.get("/__launcher/status", include_in_schema=False)
    def launcher_status():
        return {"instance": os.environ.get("MARKETING_COURT_LAUNCH_ID", ""), "status": "ready"}

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    def welcome_page():
        return frontend_page("index.html")

    @app.get("/review", include_in_schema=False)
    @app.get("/review/", include_in_schema=False)
    @app.get("/review/index.html", include_in_schema=False)
    def review_page():
        return frontend_page("review/index.html")

    @app.get("/jury", include_in_schema=False)
    @app.get("/jury/", include_in_schema=False)
    @app.get("/jury/index.html", include_in_schema=False)
    def jury_page():
        return frontend_page("jury/index.html")

    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


if __name__ == "__main__":
    import threading
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_local_app(), host="127.0.0.1", port=int(sys.argv[1]), log_level="warning"))
    if "--managed" in sys.argv:
        # EOF follows launcher/window closure, including on Windows where the
        # background Python process does not receive the console close event.
        def watch_launcher():
            sys.stdin.buffer.read()
            server.should_exit = True
        threading.Thread(target=watch_launcher, daemon=True).start()
    server.run()
