from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import distance, solve

app = FastAPI(title="VRP Solver API", version="1.7.0")

# Allow requests from GitHub Pages and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://schiggy-3000.github.io",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",  # VS Code Live Server
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(solve.router)
app.include_router(distance.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
