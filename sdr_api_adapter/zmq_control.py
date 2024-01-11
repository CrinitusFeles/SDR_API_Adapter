
import time
import socket
from queue import Queue
from threading import Thread
from gnuradio_pmt.pmt import PMT
from gnuradio_pmt.zmq_tags import tags, parse_tags
import zmq
from zmq.utils.monitor import recv_monitor_message, _MonitorMessage
from zmq import Socket
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
    def __init__(self):
        self.config_port = 5501
        self.msg_port = 5500
        self.client_address = '172.25.111.199:5502'
        self.context = zmq.Context()
        self.msg_socket: Socket = self.context.socket(zmq.PUSH)
        self.config_socket: Socket = self.context.socket(zmq.PUSH)
        self.recv_socket: Socket = self.context.socket(zmq.PULL)
        self.msg_socket.bind(f"tcp://0.0.0.0:{self.msg_port}")
        self.config_socket.bind(f"tcp://0.0.0.0:{self.config_port}")
        self.recv_socket.connect(f"tcp://{self.client_address}")
        self.msg_queue = Queue()
        self.config_queue = Queue()
        self.msg_worker: Thread
        self.config_worker: Thread
        self.recv_worker: Thread
        self.received: Event = Event(dict)
        self._running_flag = False

    def send_message(self, data: str | bytes | list[int]):
        self.msg_queue.put_nowait(data)

    def set_config(self, config: dict):
        self.config_queue.put_nowait(config)

    def msg_routine(self) -> None:
        while self._running_flag:
            msg: str | bytes | list[int] = self.msg_queue.get()
            tag_data: bytes = tags([(PMT.STRING('packet_len'), PMT.INT32(len(msg)))])
            if isinstance(msg, str):
                self.msg_socket.send(tag_data + msg.encode('utf-8'))
            elif isinstance(msg, bytes):
                self.msg_socket.send(tag_data + msg)
            elif isinstance(msg, list):
                self.msg_socket.send(tag_data + bytes(msg))
            else:
                logger.error(f'incorrect msg: {msg}')

    def config_routine(self) -> None:
        while self._running_flag:
            config: dict = self.config_queue.get()
            self.config_socket.send(PMT.DICT({PMT.STRING(key): PMT.INT32(val) for key, val in config}).to_bytes())

    def recv_routine(self) -> None:
        while self._running_flag:
            msg = self.recv_socket.recv()
            try:
                src_fd = msg.get(zmq.SRCFD)  # type: ignore
                logger.debug(f"Socket descriptor of received message: {src_fd}")
                src_sock = socket.socket(fileno=src_fd)
                logger.debug(f"Peer address: {src_sock.getpeername()}")
            except Exception as err:
                logger.error(err)
            logger.debug(f'got_msg {len(msg)}: ', msg)
            tags, payload = parse_tags(msg)
            self.received.emit({'tags': tags, 'payload': payload})

    def start(self):
        if self._running_flag:
            return
        self._running_flag = True
        self.msg_worker = Thread(name='msg_routine', target=self.msg_routine, daemon=True)
        self.config_worker = Thread(name='config_routine', target=self.config_routine, daemon=True)
        self.recv_worker = Thread(name='recv_routine', target=self.recv_routine, daemon=True)
        msg_monitor = Thread(target=event_monitor, args=(self.msg_socket, 'MSG monitor:'), daemon=True)
        config_monitor = Thread(target=event_monitor, args=(self.config_socket, 'CONFIG monitor:'), daemon=True)
        recv_monitor = Thread(target=event_monitor, args=(self.recv_socket, 'RECV monitor:'), daemon=True)
        self.msg_worker.start()
        self.config_worker.start()
        self.recv_worker.start()
        msg_monitor.start()
        config_monitor.start()
        recv_monitor.start()

    def stop(self):
        if self._running_flag:
            self._running_flag = False
            self.config_socket.close()
            self.recv_socket.close()
            self.msg_socket.close()
            self.msg_worker.join(1)
            self.config_worker.join(1)
            self.recv_worker.join(1)


if __name__ == '__main__':
    controller = ZMQ_Controller()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()