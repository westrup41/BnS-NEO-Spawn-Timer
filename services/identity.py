import base64
import ctypes
import hashlib
import json
import os
from ctypes import wintypes

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from paths import APP_DIR


IDENTITY_FILE = APP_DIR / "identity.json"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _dpapi(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise OSError("DPAPI доступен только в Windows")
    source, source_buffer = _blob(data)
    entropy, entropy_buffer = _blob(b"BNS-NEO-Spawn-Timer/identity/v1")
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if protect:
        ok = function(
            ctypes.byref(source), None, ctypes.byref(entropy), None, None,
            0x01, ctypes.byref(target),
        )
    else:
        ok = function(
            ctypes.byref(source), None, ctypes.byref(entropy), None, None,
            0x01, ctypes.byref(target),
        )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


class UserIdentity:
    """Stable Ed25519 identity. The private key is encrypted with Windows DPAPI."""

    def __init__(self, path=IDENTITY_FILE):
        self.path = path
        self.private_key = self._load_or_create()
        self.public_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = base64.b64encode(self.public_bytes).decode("ascii")
        self.user_id = hashlib.sha256(self.public_bytes).hexdigest()[:32]

    def _load_or_create(self):
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            protected = base64.b64decode(payload["private_key"])
            raw = _dpapi(protected, protect=False)
            return Ed25519PrivateKey.from_private_bytes(raw)
        except Exception:
            private_key = Ed25519PrivateKey.generate()
            raw = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            protected = _dpapi(raw, protect=True)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump({"version": 1, "private_key": base64.b64encode(protected).decode("ascii")}, file)
            return private_key

    @staticmethod
    def _canonical(packet):
        unsigned = {
            key: value for key, value in packet.items()
            if key not in {"signature", "reactions", "reaction_proofs"}
        }
        return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign(self, packet):
        signed = dict(packet)
        signed["signer_id"] = self.user_id
        signed["public_key"] = self.public_key
        signed["signature"] = base64.b64encode(
            self.private_key.sign(self._canonical(signed))
        ).decode("ascii")
        return signed

    @classmethod
    def verify(cls, packet):
        try:
            public_bytes = base64.b64decode(packet["public_key"], validate=True)
            expected_id = hashlib.sha256(public_bytes).hexdigest()[:32]
            if packet.get("signer_id") != expected_id:
                return False
            signature = base64.b64decode(packet["signature"], validate=True)
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, cls._canonical(packet))
            return True
        except (KeyError, ValueError, TypeError, InvalidSignature):
            return False
