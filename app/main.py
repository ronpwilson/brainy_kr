from fastapi import FastAPI

app = FastAPI(
    title="RBI Grade B AI Study Assistant",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}
