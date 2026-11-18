"""FastAPI entry point."""

from fastapi import FastAPI

app = FastAPI(title="AI Marketing Court", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Confirm that the API process is running."""
    return {"status": "ok"}
