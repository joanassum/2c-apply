from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes_auth import router as auth_router
from routes_profiles import router as profiles_router
from routes_matches import router as matches_router

app = FastAPI(title="JobMatch AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(matches_router)

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("../frontend/index.html")


@app.on_event("startup")
def startup():
    init_db()
