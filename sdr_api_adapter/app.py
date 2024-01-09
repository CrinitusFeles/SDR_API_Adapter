import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sdr_api_adapter import routers
from sdr_api_adapter import ws_routers

app = FastAPI(title="SDR Backend API")
app.include_router(routers.router)
app.include_router(ws_routers.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
uvicorn.run(app, host="0.0.0.0", port=80)
