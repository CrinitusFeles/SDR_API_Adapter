
import time
import socket
from queue import Empty, Queue
from threading import Thread
from gnuradio_pmt.pmt import PMT
from gnuradio_pmt.zmq_tags import tags, parse_tags
import zmq
from zmq.utils.monitor import recv_monitor_message, _MonitorMessage
from zmq import Socket
from zmq.error import Again
from zmq.constants import Event as ZMQ_Event
from event.event import Event
from loguru import logger


def event_monitor(sock: Socket, label: str = ''):
        monitor_socket = sock.get_monitor_socket()
        poller = zmq.Poller()
        poller.register(monitor_socket, zmq.POLLIN)
        while True:
            socks = poller.poll()
            if len(socks) > 0:
                data: _MonitorMessage = recv_monitor_message(monitor_socket)
                event: ZMQ_Event = data['event']  # type: ignore
                logger.debug(f'{label} {event.name}')
                if event.name == 'MONITOR_STOPPED':
                    break
            time.sleep(0.1)


class ZMQ_Controller:
    def __init__(self) -> None:
        self.received: Event = Event(dict)
        self.config_port = 5501
        self.msg_port = 5500
        self.client_address = '172.25.111.199:5502'
        self.context = zmq.Context()
        self.msg_queue = Queue()
        self.config_queue = Queue()
        self._running_flag = False

        self.msg_socket: Socket
        self.config_socket: Socket
        self.recv_socket: Socket
        self.msg_worker: Thread
        self.config_worker: Thread
        self.recv_worker: Thread

    def send_message(self, data: str | bytes | list[int]) -> None:
        if self._running_flag:
            self.msg_queue.put_nowait(data)

    def set_config(self, config: dict | str) -> None:
        if self._running_flag:
            self.config_queue.put_nowait(config)

    def msg_routine(self) -> None:
        while self._running_flag:
            try:
                msg: str | bytes | list[int] = self.msg_queue.get(timeout=1)
                tag_data: bytes = tags([(PMT.STRING('packet_len'), PMT.INT32(len(msg)))])
                if isinstance(msg, str):
                    self.msg_socket.send(tag_data + msg.encode('utf-8'))
                elif isinstance(msg, bytes):
                    self.msg_socket.send(tag_data + msg)
                elif isinstance(msg, list):
                    self.msg_socket.send(tag_data + bytes(msg))
                else:
                    logger.error(f'incorrect msg: {msg}')
            except Empty:
                pass
            except Again:
                logger.error('Timeout to send msg data')

    def config_routine(self) -> None:
        while self._running_flag:
            try:
                config: dict | str = self.config_queue.get(timeout=1)
                logger.info(f'sending config: {config}')
                if isinstance(config, dict):
                    self.config_socket.send(PMT.DICT({PMT.STRING(key): PMT.INT32(val)
                                                      for key, val in config.items()}).to_bytes())
                elif isinstance(config, str):
                    self.config_socket.send(PMT.STRING(config).to_bytes())
                else:
                    raise TypeError('incorrect config message type')
            except Empty:
                pass
            except Again:
                logger.error('Timeout to send config data')

    def recv_routine(self) -> None:
        while self._running_flag:
            try:
                msg: bytes = self.recv_socket.recv()
            except Again:
                pass
            else:
                try:
                    tags, payload = parse_tags(msg)
                    logger.debug(f'parsed data: {tags} {payload}')
                    self.received.emit({'tags': tags, 'payload': payload})
                except Exception as err:
                    logger.error(err)
                    logger.debug(f'msg has error {len(msg)}: {msg}')

    def start(self) -> None:
        if self._running_flag:
            return
        self._running_flag = True
        self.msg_socket: Socket = self.context.socket(zmq.PUSH)
        self.config_socket: Socket = self.context.socket(zmq.PUSH)
        self.recv_socket: Socket = self.context.socket(zmq.PULL)
        self.recv_socket.setsockopt(zmq.RCVTIMEO, 1000)
        self.config_socket.setsockopt(zmq.SNDTIMEO, 1000)
        self.msg_socket.setsockopt(zmq.SNDTIMEO, 1000)
        self.msg_socket.bind(f"tcp://0.0.0.0:{self.msg_port}")
        self.config_socket.bind(f"tcp://0.0.0.0:{self.config_port}")
        self.recv_socket.connect(f"tcp://{self.client_address}")
        self.msg_worker = Thread(name='msg_routine', target=self.msg_routine, daemon=True)
        self.config_worker = Thread(name='config_routine', target=self.config_routine, daemon=True)
        self.recv_worker = Thread(name='recv_routine', target=self.recv_routine, daemon=True)
        msg_monitor = Thread(name='msg_event_monitor', target=event_monitor,
                             args=(self.msg_socket, 'MSG monitor:'),  daemon=True)
        config_monitor = Thread(name='config_event_monitor', target=event_monitor,
                                args=(self.config_socket, 'CONFIG monitor:'), daemon=True)
        recv_monitor = Thread(name='recv_event_monitor', target=event_monitor,
                              args=(self.recv_socket, 'RECV monitor:'), daemon=True)
        self.msg_worker.start()
        self.config_worker.start()
        self.recv_worker.start()
        msg_monitor.start()
        config_monitor.start()
        recv_monitor.start()
        logger.info('zmq controller started')

    def stop(self) -> None:
        if not self._running_flag:
            return
        self._running_flag = False
        self.msg_worker.join(2)
        self.config_worker.join(2)
        self.recv_worker.join(2)
        self.config_socket.close()
        self.recv_socket.close()
        self.msg_socket.close()
        logger.info('zmq controller stopped')


if __name__ == '__main__':
    controller = ZMQ_Controller()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
