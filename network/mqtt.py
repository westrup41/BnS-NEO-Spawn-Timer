import queue
import select
import socket
import threading
import time
import uuid


def _mqtt_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def _remaining_length(length: int) -> bytes:
    output = bytearray()
    while True:
        byte = length % 128
        length //= 128
        if length:
            byte |= 0x80
        output.append(byte)
        if not length:
            return bytes(output)


def _packet(header: int, body: bytes) -> bytes:
    return bytes((header,)) + _remaining_length(len(body)) + body


class MqttConnection:
    def __init__(self, host, port, topic, on_message, on_status):
        self.host = host
        self.port = port
        self.topic = topic
        self.on_message = on_message
        self.on_status = on_status
        self.client_id = "bnsneo-" + uuid.uuid4().hex[:12]
        self.outgoing = queue.Queue(maxsize=500)
        self.stop_event = threading.Event()
        self.thread = None
        self.socket = None
        self.connected = False
        self.last_error = ""
        self.last_message_at = 0.0
        self.last_connected_at = 0.0
        self.connect_latency_ms = None
        self.reconnect_count = 0

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._run, name=f"mqtt-{self.host}", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self._close_socket()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        self.thread = None
        self._set_connected(False)

    def publish(self, payload: bytes, retain: bool = False):
        try:
            self.outgoing.put_nowait((time.monotonic(), payload, bool(retain)))
            return True
        except queue.Full:
            return False

    def _run(self):
        retry_delay = 1
        while not self.stop_event.is_set():
            try:
                self._connect()
                retry_delay = 1
                self._io_loop()
            except (OSError, ValueError, ConnectionError) as exc:
                self.last_error = str(exc)
                self.reconnect_count += 1
            finally:
                self._set_connected(False)
                self._close_socket()
            if not self.stop_event.wait(retry_delay):
                retry_delay = min(20, retry_delay * 2)

    def _connect(self):
        started = time.monotonic()
        sock = socket.create_connection((self.host, self.port), timeout=7)
        sock.settimeout(3)
        self.socket = sock
        variable = _mqtt_string("MQTT") + bytes((4, 2)) + (30).to_bytes(2, "big")
        sock.sendall(_packet(0x10, variable + _mqtt_string(self.client_id)))
        header, body = self._read_packet()
        if header >> 4 != 2 or len(body) != 2 or body[1] != 0:
            raise ConnectionError("MQTT connection rejected")
        subscribe = (1).to_bytes(2, "big") + _mqtt_string(self.topic) + b"\x00"
        sock.sendall(_packet(0x82, subscribe))
        header, _body = self._read_packet()
        if header >> 4 != 9:
            raise ConnectionError("MQTT subscription rejected")
        sock.settimeout(3)
        self._set_connected(True)
        self.connect_latency_ms = round((time.monotonic() - started) * 1000)
        self.last_connected_at = time.time()
        self.last_error = ""

    def _io_loop(self):
        last_network_activity = time.monotonic()
        while not self.stop_event.is_set():
            sock = self.socket
            if sock is None:
                raise ConnectionError("MQTT socket closed")
            try:
                created, payload, retain = self.outgoing.get_nowait()
                if time.monotonic() - created > 30:
                    continue
                body = _mqtt_string(self.topic) + payload
                sock.sendall(_packet(0x31 if retain else 0x30, body))
                last_network_activity = time.monotonic()
            except queue.Empty:
                pass

            readable, _, _ = select.select([sock], [], [], 0.25)
            if readable:
                header, body = self._read_packet()
                last_network_activity = time.monotonic()
                if header >> 4 == 3:
                    self._handle_publish(header, body)

            if time.monotonic() - last_network_activity >= 20:
                sock.sendall(b"\xC0\x00")
                last_network_activity = time.monotonic()

    def _handle_publish(self, header: int, body: bytes):
        if len(body) < 2:
            return
        topic_length = int.from_bytes(body[:2], "big")
        offset = 2 + topic_length
        if offset > len(body):
            return
        qos = (header >> 1) & 0x03
        packet_id = None
        if qos:
            if offset + 2 > len(body):
                return
            packet_id = body[offset:offset + 2]
            offset += 2
        self.last_message_at = time.time()
        self.on_message(self, body[offset:])
        if qos == 1 and packet_id:
            self.socket.sendall(b"\x40\x02" + packet_id)

    def _read_packet(self):
        first = self._read_exact(1)[0]
        multiplier = 1
        remaining = 0
        for _ in range(4):
            byte = self._read_exact(1)[0]
            remaining += (byte & 127) * multiplier
            if not byte & 128:
                break
            multiplier *= 128
        else:
            raise ValueError("Invalid MQTT packet length")
        if remaining > 1024 * 1024:
            raise ValueError("MQTT packet is too large")
        return first, self._read_exact(remaining)

    def _read_exact(self, length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            sock = self.socket
            if sock is None:
                raise ConnectionError("MQTT socket closed")
            chunk = sock.recv(length - len(chunks))
            if not chunk:
                raise ConnectionError("MQTT socket closed")
            chunks.extend(chunk)
        return bytes(chunks)

    def _set_connected(self, connected: bool):
        connected = bool(connected)
        if connected != self.connected:
            self.connected = connected
            self.on_status(self, connected)

    def _close_socket(self):
        sock, self.socket = self.socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


class MqttRelayPool:
    def __init__(self, brokers, topic, on_message, on_status):
        self.connections = [
            MqttConnection(host, port, topic, on_message, on_status)
            for host, port in brokers
        ]

    def start(self):
        for connection in self.connections:
            connection.start()

    def stop(self):
        for connection in self.connections:
            connection.stop()

    def publish(self, payload: bytes, retain: bool = False):
        online = self.online_count() > 0
        accepted = False
        for connection in self.connections:
            accepted = connection.publish(payload, retain=retain) or accepted
        return online and accepted

    def online_count(self):
        return sum(connection.connected for connection in self.connections)

    def reconnect(self):
        self.stop()
        self.start()

    def diagnostics(self):
        return [{
            "host": item.host,
            "port": item.port,
            "connected": item.connected,
            "latency_ms": item.connect_latency_ms,
            "last_message_at": item.last_message_at,
            "last_connected_at": item.last_connected_at,
            "last_error": item.last_error,
            "reconnect_count": item.reconnect_count,
        } for item in self.connections]
