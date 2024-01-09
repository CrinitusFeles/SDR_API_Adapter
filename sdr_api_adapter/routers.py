

from fastapi import APIRouter
# from loguru import logger
from sdr_api_adapter.sdr_model import sdr

router = APIRouter(prefix="/sdr", tags=["SDR"])

@router.get('/config')
async def get_config():
    return sdr.get_config()

@router.post('/send')
async def send(data: str) -> None:
    return sdr.send(data.encode('utf-8'))

@router.get('/last_msg')
async def get_last_msg():
    return sdr.last_msg

@router.post('/start')
async def start() -> None:
    return sdr.start()

@router.post('/stop')
async def stop() -> None:
    return sdr.stop()

@router.post('/restart')
async def restart() -> None:
    return sdr.restart()
