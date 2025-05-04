from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from core.openstack_api import openstack_api

app = FastAPI(title="OpenStack Management API",
            description="API for managing OpenStack resources",
            version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    if openstack_api.connect():
        return {"status": "healthy"}
    return {"status": "unhealthy"}, 503