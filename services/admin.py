import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from config import ADMIN_PUBLIC_KEY
from paths import APP_DIR
from services.identity import UserIdentity


ADMIN_KEY_FILE = APP_DIR / "admin_private_key.pem"


def verify_admin_packet(packet: dict) -> bool:
    try:
        if not ADMIN_PUBLIC_KEY or packet.get("type") != "admin":
            return False
        public_bytes = base64.b64decode(ADMIN_PUBLIC_KEY, validate=True)
        if packet.get("admin_public_key") != ADMIN_PUBLIC_KEY:
            return False
        signature = base64.b64decode(packet["admin_signature"], validate=True)
        unsigned = {key: value for key, value in packet.items() if key != "admin_signature"}
        raw = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, raw)
        return True
    except (KeyError, ValueError, TypeError, InvalidSignature):
        return False


def sign_admin_packet(packet: dict, key_path: Path = ADMIN_KEY_FILE) -> dict:
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Неверный тип админ-ключа")
    signed = dict(packet)
    signed["admin_public_key"] = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode("ascii")
    raw = json.dumps(signed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signed["admin_signature"] = base64.b64encode(private_key.sign(raw)).decode("ascii")
    return signed


def create_admin_key(key_path: Path = ADMIN_KEY_FILE) -> str:
    if key_path.exists():
        raise FileExistsError(str(key_path))
    key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    key_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    return base64.b64encode(private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )).decode("ascii")
