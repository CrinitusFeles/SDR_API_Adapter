
from typing import Callable


class SDR_Model:
    def __init__(self, **kwargs) -> None:
        self._kwargs = kwargs
        self.sdr_class = None
        self._running_flag = False
        self.sdr = None
        self.last_msg = None

    def rx_msg_handler(self, data):
        self.last_msg = data

    # def set_rx_handler(self, rx_handler: Callable):
    #     self.rx_handler = rx_handler
    #     if self.sdr:
    #         self.sdr.epy_block_1.rx_handler = rx_handler

    def get_config(self):
        return self._kwargs

    def set_config(self, **kwargs):
        self._kwargs = kwargs

    def send(self, data: bytes) -> None:
        if self.sdr:
            self.sdr.send(data)

    def start(self) -> None:
        if self._running_flag:
            return
        if self.sdr_class:
            self.sdr = self.sdr_class(**self._kwargs)
            self.sdr.epy_block_1.rx_handler = self.rx_msg_handler
            # if self.rx_handler:
            #     self.sdr.rx_msg_handler.subscribe(self.rx_msg_handler)
            #     self.sdr.received.subscribe(self.rx_handler)
        else:
            return

        self.sdr.start()

    def stop(self) -> None:
        if self._running_flag and self.sdr:
            self.sdr.stop()
            self.sdr.wait()
            self.sdr = None

    def restart(self) -> None:
        if self._running_flag:
            self.stop()
            if not self.sdr_class:
                return
            self.sdr = self.sdr_class(**self._kwargs)
            self.sdr.epy_block_1.rx_handler = self.rx_msg_handler
            # if self.rx_handler:
            #     self.sdr.rx_msg_handler.subscribe(self.rx_msg_handler)
            #     self.sdr.received.subscribe(self.rx_handler)
            self.start()

    def set_tx_mode(self):
        if self.sdr:
            self.sdr.set_output_index(1)
            self.sdr.set_input_index(1)

    def set_rx_mode(self):
        if self.sdr:
            self.sdr.set_output_index(0)
            self.sdr.set_input_index(0)

sdr = SDR_Model()