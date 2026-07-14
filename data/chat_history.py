import json
import threading
import uuid
from datetime import datetime

from config import CHAT_MAX_LENGTH, CHAT_MAX_MESSAGES
from paths import APP_DIR
from services.identity import UserIdentity


CHAT_HISTORY_FILE = APP_DIR / "chat_history.json"


class ChatHistory:
    """Persistent, bounded chat history shared by chat and spawn alerts."""

    def __init__(self, path=CHAT_HISTORY_FILE):
        self.path = path
        self._lock = threading.RLock()
        self._messages = []
        self.load()

    def load(self):
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, list):
                    normalized = [self._normalize(item) for item in data if isinstance(item, dict)]
                    self._messages = [item for item in normalized if item is not None]
                    self._messages = self._messages[-CHAT_MAX_MESSAGES:]
            except Exception:
                self._messages = []

    def _normalize(self, message):
        result = dict(message)
        is_signed = bool(result.get("signature"))
        if is_signed and not UserIdentity.verify(result):
            return None
        result["id"] = str(result.get("id") or uuid.uuid4())
        result["type"] = "spawn" if result.get("type") == "spawn" else "chat"
        if result["type"] == "spawn":
            if not is_signed or result.get("author_id") != result.get("signer_id"):
                return None
        result["nickname"] = str(result.get("nickname") or "Неизвестный")[:40]
        result["author_id"] = str(result.get("author_id") or result["nickname"])
        result["message"] = str(result.get("message") or "")[:CHAT_MAX_LENGTH]
        result["channel"] = str(result.get("channel") or "")
        result["timestamp"] = str(result.get("timestamp") or datetime.now().isoformat())
        proofs = result.get("reaction_proofs", {})
        valid_proofs = {}
        if isinstance(proofs, dict):
            for voter, proof in proofs.items():
                if not isinstance(proof, dict) or not UserIdentity.verify(proof):
                    continue
                if (
                    proof.get("type") != "reaction"
                    or proof.get("message_id") != result["id"]
                    or proof.get("voter_id") != voter
                    or proof.get("signer_id") != voter
                ):
                    continue
                value = int(proof.get("value", 0))
                if value:
                    valid_proofs[str(voter)] = proof
        result["reaction_proofs"] = valid_proofs
        result["reactions"] = {
            voter: 1 if int(proof.get("value", 0)) > 0 else -1
            for voter, proof in valid_proofs.items()
        }
        return result

    def save(self):
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.path.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as file:
                    json.dump(self._messages[-CHAT_MAX_MESSAGES:], file, ensure_ascii=False, indent=2)
                temp_path.replace(self.path)
            except Exception:
                pass

    def add(self, message):
        normalized = self._normalize(message)
        if normalized is None or not normalized["message"]:
            return None
        with self._lock:
            for item in self._messages:
                if item["id"] != normalized["id"]:
                    continue
                changed = False
                for voter, proof in normalized.get("reaction_proofs", {}).items():
                    if item.setdefault("reaction_proofs", {}).get(voter) != proof:
                        item["reaction_proofs"][voter] = proof
                        item.setdefault("reactions", {})[voter] = 1 if int(proof.get("value", 0)) > 0 else -1
                        changed = True
                if changed:
                    self.save()
                    return dict(item)
                return None
            self._messages.append(normalized)
            self._messages = self._messages[-CHAT_MAX_MESSAGES:]
            self.save()
        return dict(normalized)

    def get_vote(self, message_id, voter_id):
        with self._lock:
            for message in self._messages:
                if message["id"] == str(message_id):
                    return int(message.get("reactions", {}).get(str(voter_id), 0))
        return 0

    def apply_reaction(self, packet):
        """Store a verified signed vote as the source of the displayed counter."""
        if not UserIdentity.verify(packet):
            return False
        message_id = str(packet.get("message_id", ""))
        voter_id = str(packet.get("voter_id", ""))
        if packet.get("type") != "reaction" or packet.get("signer_id") != voter_id:
            return False
        value = int(packet.get("value", 0))
        with self._lock:
            for message in self._messages:
                if message["id"] != str(message_id) or message["type"] != "spawn":
                    continue
                reactions = message.setdefault("reactions", {})
                proofs = message.setdefault("reaction_proofs", {})
                if value == 0:
                    reactions.pop(voter_id, None)
                    proofs.pop(voter_id, None)
                else:
                    reactions[voter_id] = 1 if value > 0 else -1
                    proofs[voter_id] = dict(packet)
                self.save()
                return True
        return False

    def all(self):
        with self._lock:
            return [dict(item, reactions=dict(item.get("reactions", {}))) for item in self._messages]

    def reputation(self, author_id):
        with self._lock:
            return sum(
                sum(message.get("reactions", {}).values())
                for message in self._messages
                if message.get("type") == "spawn" and message.get("author_id") == str(author_id)
            )
