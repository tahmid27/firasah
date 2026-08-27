from fastapi import FastAPI

app = FastAPI(title="Firasah API")


@app.get("/health")
def health():
    return {"status": "ok"}
