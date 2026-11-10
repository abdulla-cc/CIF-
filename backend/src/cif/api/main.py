from fastapi import FastAPI

app = FastAPI(title="CIF")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
