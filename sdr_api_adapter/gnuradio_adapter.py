
from threading import Thread
import time
import subprocess

from loguru import logger
from sdr_api_adapter.zmq_control import ZMQ_Controller


class GNURadio_Adapter:
    def __init__(self, **kwargs) -> None:
        self._kwargs = kwargs
        self._running_flag = False
        self.last_msg = None
        self.controller = ZMQ_Controller()
        self.controller.received.subscribe(self.rx_msg_handler)
        self.proc = None
        self.subprocess_args: list[str] = ['python', 'RX_TX.py']
        self.proc_thread: Thread

    def rx_msg_handler(self, data):
        self.last_msg = data

    def get_config(self):
        return self._kwargs

    def set_config(self, **kwargs):
        self._kwargs = kwargs

    def send(self, data: bytes | str | list[int]) -> None:
        self.controller.send_message(data)

    def routine(self):
        self.proc = subprocess.Popen(self.subprocess_args, shell=True)
        # logger.debug(self.proc.stdout.read())  # type: ignore

    def start(self, args: list[str] | None = None) -> None:
        if args:
            self.subprocess_args = args
        if self._running_flag:
            return
        logger.debug(f'run with args: {self.subprocess_args}')
        self.proc_thread = Thread(name='proc', target=self.routine, daemon=True)
        self.proc_thread.start()
        time.sleep(1)
        # logger.info(self.proc.stdout.read())  # type: ignore

    def stop(self) -> None:
        if self._running_flag:
            self.proc.stdin.close()  # type: ignore

    def restart(self) -> None:
        if self._running_flag:
            self.stop()

            self.start()

    def set_tx_mode(self):
        self.controller.set_config({'input_index': 1, 'output_index': 1})

    def set_rx_mode(self):
        self.controller.set_config({'input_index': 0, 'output_index': 0})

gr = GNURadio_Adapter()
gr.start()