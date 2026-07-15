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
from services.admin import verify_admin_packet
from services.admin import sign_admin_packet
from .packet import admin_packet


BROKERS = (
    ("broker.emqx.io", 1883),
    ("broker-cn.emqx.io", 1883),
    ("broker.hivemq.com", 1883),
    ("test.mosquitto.org", 1883),
    ("mqtt.eclipseprojects.io", 1883),
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
    admin_received = Signal(dict)

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
        self._reconnect_lock = threading.Lock()
        self._global_cipher = AESGCM(ROOM_SECRET)
        self._room_code = str(
            getattr(app.settings, "online_room_code", "")
            if getattr(app.settings, "online_room_private", False) else ""
        )
        self._cipher = AESGCM(self._derive_room_secret(self._room_code))
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
        with self._reconnect_lock:
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
            wire = self._encode(packet, self._cipher)
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

    def _encode(self, packet: dict, cipher) -> bytes:
        raw = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(raw, level=6)
        nonce = os.urandom(12)
        encrypted = nonce + cipher.encrypt(nonce, compressed, WIRE_PREFIX)
        return WIRE_PREFIX + base64.b64encode(encrypted)

    def send_admin_command(self, action: str, target: str = "", nickname: str = ""):
        if not self.started or not self.internet_available:
            return False
        try:
            command = sign_admin_packet(admin_packet(action, target, nickname))
            commands = list(getattr(self.app.settings, "admin_commands", []))[-999:] + [command]
            snapshot = create_packet("admin", action="state", commands=commands)
            packet = sign_admin_packet(snapshot)
            wire = self._encode(packet, self._global_cipher)
            if len(wire) > MAX_WIRE_BYTES or not self._remember_packet(packet["id"]):
                return False
            accepted = self._relay.publish(wire, retain=True)
            if accepted:
                self.admin_received.emit(packet)
            return accepted
        except Exception:
            return False

    def _on_wire_message(self, _connection, wire: bytes):
        if not wire.startswith(WIRE_PREFIX) or len(wire) > MAX_WIRE_BYTES:
            return
        try:
            encrypted = base64.b64decode(wire[len(WIRE_PREFIX):], validate=True)
            if len(encrypted) < 29:
                return
            nonce, ciphertext = encrypted[:12], encrypted[12:]
            used_global_fallback = False
            try:
                compressed = self._cipher.decrypt(nonce, ciphertext, WIRE_PREFIX)
            except Exception:
                # Signed owner moderation commands are sent through the global
                # cipher and remain effective inside private rooms.
                compressed = self._global_cipher.decrypt(nonce, ciphertext, WIRE_PREFIX)
                used_global_fallback = bool(self._room_code)
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(compressed, MAX_WIRE_BYTES + 1)
            if (len(raw) > MAX_WIRE_BYTES or decompressor.unconsumed_tail
                    or decompressor.unused_data or not decompressor.eof):
                return
            packet = json.loads(raw.decode("utf-8"))
        except Exception:
            return
        if used_global_fallback and packet.get("type") != "admin":
            return
        self.receive(packet)

    def _on_relay_status(self, _connection, _connected):
        with self._status_lock:
            online = self.started and self._relay.online_count() > 0
        became_online = self._set_online(online)
        if online and became_online:
            self.send_hello()

    def _set_online(self, online: bool):
        online = bool(online)
        with self._status_lock:
            changed = online != self.internet_available
            if changed:
                self.internet_available = online
        if changed:
            self.online_changed.emit(online)
        return changed and online

    def receive(self, packet: dict):
        if not isinstance(packet, dict):
            return
        packet_id = str(packet.get("id") or "")
        if not packet_id or not self._remember_packet(packet_id):
            return

        packet_type = packet.get("type")
        if packet_type == "admin":
            if verify_admin_packet(packet):
                self.admin_received.emit(packet)
            return
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
                verified_messages = []
                for message in messages[:100]:
                    if not isinstance(message, dict):
                        continue
                    if message.get("type") not in ("chat", "spawn"):
                        continue
                    if message.get("author_id") != message.get("signer_id"):
                        continue
                    if UserIdentity.verify(message):
                        verified_messages.append(message)
                self.history_received.emit(verified_messages)
            commands = packet.get("admin_commands", [])
            if isinstance(commands, list):
                for command in commands[-1000:]:
                    if isinstance(command, dict) and verify_admin_packet(command):
                        self.admin_received.emit(command)

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
        packet = create_packet(
            "sync",
            messages=self.app.chat_history.all()[-100:],
            admin_commands=list(getattr(self.app.settings, "admin_commands", []))[-1000:],
        )
        self.broadcast(self.identity.sign(packet))

    def _remember_packet(self, packet_id: str) -> bool:
        with self._seen_lock:
            if packet_id in self._seen_packets:
                return False
            self._seen_packets.add(packet_id)
            if len(self._seen_packets) > 1000:
                self._seen_packets = set(list(self._seen_packets)[-500:])
            return True

    def diagnostics(self):
        return self._relay.diagnostics()

    def reconnect(self):
        if not self.started or not self._reconnect_lock.acquire(blocking=False):
            return False
        try:
            if not self.started:
                return False
            self._relay.stop()
            if not self.started:
                return False
            self._relay.start()
            return True
        finally:
            self._reconnect_lock.release()

    @staticmethod
    def _derive_room_secret(room_code: str) -> bytes:
        code = str(room_code or "").strip()
        if not code:
            return ROOM_SECRET
        return hashlib.pbkdf2_hmac(
            "sha256", code.encode("utf-8"), b"BNS-NEO/private-room/v1", 200_000, 32
        )

    def set_room(self, room_code: str):
        code = str(room_code or "").strip()[:64]
        if code == self._room_code:
            return
        self._room_code = code
        self._cipher = AESGCM(self._derive_room_secret(code))
        self.peers.clear()
        with self._seen_lock:
            self._seen_packets.clear()
        self._set_online(False)
        if self.started:
            threading.Thread(target=self.reconnect, name="mqtt-room-reconnect", daemon=True).start()

    def room_label(self):
        return "Глобальная" if not self._room_code else "Приватная"
