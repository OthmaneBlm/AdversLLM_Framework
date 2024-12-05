from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analyze

app = FastAPI(
    title="Storyteller API",
    description="API for portfolio analysis",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(analyze.router, prefix="/api")

@app.get("/health")
async def health():
    return {"message": "Health OK, Server is live"}
