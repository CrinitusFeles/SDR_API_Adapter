

from fastapi import APIRouter
# from loguru import logger
from sdr_api_adapter.gnuradio_adapter import gr

router = APIRouter(prefix="/sdr", tags=["SDR"])

@router.get('/config')
async def get_config():
    return gr.get_config()

@router.post('/send')
async def send(data: str) -> None:
    return gr.send(data.encode('utf-8'))

@router.get('/last_msg')
async def get_last_msg():
    return gr.last_msg

@router.post('/start')
async def start() -> None:
    return gr.start()

@router.post('/stop')
async def stop() -> None:
    return gr.stop()

@router.post('/restart')
async def restart() -> None:
    return gr.restart()

@router.post('/set_tx_mode')
async def set_tx_mode() -> None:
    return gr.set_tx_mode()

@router.post('/set_rx_mode')
async def set_rx_mode() -> None:
    return gr.set_rx_mode()