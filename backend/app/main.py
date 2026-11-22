from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import auth, complaints, wards, analytics, channels as channels_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NagaraAI API",
    description="Bengaluru Civic Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(wards.router)
app.include_router(analytics.router)
app.include_router(channels_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "NagaraAI"}
