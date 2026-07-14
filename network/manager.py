import base64
import hashlib
import json
import os
import threading
import zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PySide6.QtCore import QObject, Signal

from services.identity import UserIdentity
from .mqtt import MqttRelayPool
from .packet import create_packet, spawn_packet, chat_packet, reaction_packet
from .protocol import PROTOCOL_VERSION


BROKERS = (
    ("broker.emqx.io", 1883),
    ("broker.hivemq.com", 1883),
    ("test.mosquitto.org", 1883),
)
ROOM_SECRET = bytes.fromhex(
    "A46E70F3D8BE2B2C7C9773A92DE47E42D66AA8D14DC8D313F67AE8A74E12095D"
)
ROOM_TOPIC = "bnsneo/v4/" + hashlib.sha256(ROOM_SECRET + b"topic").hexdigest()[:32]
WIRE_PREFIX = b"BNSM2:"
MAX_WIRE_BYTES = 1024 * 1024


class NetworkManager(QObject):
    spawn_received = Signal(dict)
    chat_received = Signal(dict)
    reaction_received = Signal(dict)
    online_changed = Signal(bool)
    history_received = Signal(list)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.identity = UserIdentity()
        self.started = False
        self.internet_available = False
        self.peers = {}
        self._seen_packets = set()
        self._seen_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._cipher = AESGCM(ROOM_SECRET)
        self._relay = MqttRelayPool(
            BROKERS, ROOM_TOPIC, self._on_wire_message, self._on_relay_status
        )

    def start(self):
        if self.started:
            return
        self.started = True
        self._relay.start()

    def stop(self):
        if not self.started:
            return
        self.started = False
        self._relay.stop()
        self.peers.clear()
        self._set_online(False)

    def send_spawn(self, channel_name: str):
        if not self.internet_available:
            return None
        packet = self.identity.sign(spawn_packet(
            channel_name, self.app.get_nickname(), self.identity.user_id
        ))
        return packet if self.broadcast(packet) else None

    def send_chat(self, message: str):
        if not self.internet_available:
            return None
        packet = self.identity.sign(chat_packet(
            self.app.get_nickname(), message, self.identity.user_id
        ))
        return packet if self.broadcast(packet) else None

    def send_reaction(self, message_id: str, value: int):
        if not self.internet_available:
            return None
        packet = self.identity.sign(reaction_packet(
            message_id, self.identity.user_id, value
        ))
        return packet if self.broadcast(packet) else None

    def broadcast(self, packet: dict) -> bool:
        if not self.started or not self.internet_available:
            return False
        try:
            raw = json.dumps(
                packet, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            compressed = zlib.compress(raw, level=6)
            nonce = os.urandom(12)
            encrypted = nonce + self._cipher.encrypt(nonce, compressed, WIRE_PREFIX)
            wire = WIRE_PREFIX + base64.b64encode(encrypted)
            if len(wire) > MAX_WIRE_BYTES:
                return False
            packet_id = str(packet.get("id") or "")
            if not packet_id or not self._remember_packet(packet_id):
                return False
            published = self._relay.publish(wire)
            if not published:
                with self._seen_lock:
                    self._seen_packets.discard(packet_id)
            return published
        except (TypeError, ValueError):
            return False

    def _on_wire_message(self, wire: bytes):
        if not wire.startswith(WIRE_PREFIX) or len(wire) > MAX_WIRE_BYTES:
            return
        try:
            encrypted = base64.b64decode(wire[len(WIRE_PREFIX):], validate=True)
            if len(encrypted) < 29:
                return
            nonce, ciphertext = encrypted[:12], encrypted[12:]
            compressed = self._cipher.decrypt(nonce, ciphertext, WIRE_PREFIX)
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(compressed, MAX_WIRE_BYTES + 1)
            if len(raw) > MAX_WIRE_BYTES or decompressor.unconsumed_tail:
                return
            packet = json.loads(raw.decode("utf-8"))
        except Exception:
            return
        self.receive(packet)

    def _on_relay_status(self, _connection, _connected):
        with self._status_lock:
            online = self.started and self._relay.online_count() > 0
        was_online = self.internet_available
        self._set_online(online)
        if online and (_connected or not was_online):
            self.send_hello()

    def _set_online(self, online: bool):
        online = bool(online)
        if online != self.internet_available:
            self.internet_available = online
            self.online_changed.emit(online)

    def receive(self, packet: dict):
        if not isinstance(packet, dict):
            return
        packet_id = str(packet.get("id") or "")
        if not packet_id or not self._remember_packet(packet_id):
            return

        packet_type = packet.get("type")
        if packet_type not in ("hello", "spawn", "chat", "reaction", "sync"):
            return
        if packet.get("protocol") != PROTOCOL_VERSION or not UserIdentity.verify(packet):
            return

        if packet_type == "hello":
            if packet.get("peer_id") == packet.get("signer_id"):
                self.handle_hello(packet)
        elif packet_type == "spawn":
            if packet.get("author_id") == packet.get("signer_id"):
                self.spawn_received.emit(packet)
        elif packet_type == "chat":
            if packet.get("author_id") == packet.get("signer_id"):
                self.chat_received.emit(packet)
        elif packet_type == "reaction":
            if packet.get("voter_id") == packet.get("signer_id"):
                self.reaction_received.emit(packet)
        elif packet_type == "sync":
            messages = packet.get("messages", [])
            if isinstance(messages, list):
                self.history_received.emit(messages[:100])

    def send_hello(self):
        packet = create_packet(
            "hello", nickname=self.app.get_nickname(), peer_id=self.identity.user_id
        )
        self.broadcast(self.identity.sign(packet))

    def handle_hello(self, packet: dict):
        peer_id = str(packet.get("peer_id") or "unknown")
        first_seen = peer_id not in self.peers
        self.peers[peer_id] = {
            "id": peer_id,
            "nickname": str(packet.get("nickname") or "Неизвестный"),
            "connected": True,
        }
        if first_seen and peer_id != self.identity.user_id:
            self.send_history()

    def send_history(self):
        if not self.internet_available:
            return
        packet = create_packet("sync", messages=self.app.chat_history.all()[-100:])
        self.broadcast(self.identity.sign(packet))

    def _remember_packet(self, packet_id: str) -> bool:
        with self._seen_lock:
            if packet_id in self._seen_packets:
                return False
            self._seen_packets.add(packet_id)
            if len(self._seen_packets) > 1000:
                self._seen_packets = set(list(self._seen_packets)[-500:])
            return True
