"""Explicit real-provider exercise; requires a running live-mode local API."""

import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def checked(response):
    response.raise_for_status()
    return response.json()


def wait_task(client, task_id):
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        try:
            task = checked(client.get(f"/api/tasks/{task_id}"))
        except httpx.TransportError:
            # Polling is read-only; reconnect without creating another paid task.
            time.sleep(1)
            continue
        if task["status"] == "completed":
            return task["result_id"]
        if task["status"] in ("failed", "interrupted"):
            raise RuntimeError(task["error"])
        time.sleep(1)
    raise TimeoutError("Task exceeded 15 minutes; check its saved server status.")


def main():
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
        health = checked(client.get("/health"))
        if health["mode"] != "live":
            raise RuntimeError("Real exercise requires COURT_MODE=live and a valid server-side model key.")
        project = checked(client.post("/api/projects", json={"name": "Live end-to-end rehearsal"}))
        image = ROOT / "examples" / "eco-bottle.png"
        asset = checked(client.post(f'/api/projects/{project["project_id"]}/assets',
                                   files={"file": (image.name, image.read_bytes(), "image/png")}))
        task = checked(client.post(f'/api/assets/{asset["asset_version_id"]}/reviews'))
        review_id = wait_task(client, task["task_id"])
        review = checked(client.get(f"/api/reviews/{review_id}"))
        risk = next((r for r in review["risks"] if "eco" in r["claim_quote"].lower()), None)
        if risk is None or not risk["anchor_ids"]:
            raise RuntimeError("Expected sample environmental risk with OCR localization was not returned.")
        rewrite = checked(client.post(f'/api/reviews/{review_id}/risks/{risk["risk_id"]}/rewrite'))
        wait_task(client, rewrite["task_id"])
        case = checked(client.post(f'/api/risks/{risk["risk_id"]}/appeals'))
        while case["next_step"]:
            case = checked(client.post(f'/api/cases/{case["case_id"]}/advance',
                                       json={"expected_step": case["next_step"]}))
        assert len(case["turns"]) == 4 and case["judgment"]
        report = checked(client.get(f"/api/reviews/{review_id}/report"))
        target = ROOT / "test-results" / "live-report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Real OCR, review, rewrite and court completed. Report: {target}")


if __name__ == "__main__":
    main()
