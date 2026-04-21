from fastapi import FastAPI

app = FastAPI(title="Checkmate", description="AI code review bot", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "checkmate", "docs": "/docs"}
