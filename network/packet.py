from datetime import datetime
import uuid

from .protocol import (
    PROTOCOL_VERSION,
    TYPE_CHAT,
    TYPE_SPAWN,
    TYPE_REACTION,
)


def create_packet(packet_type: str, **data):
    return {
        "protocol": PROTOCOL_VERSION,
        "id": str(uuid.uuid4()),
        "type": packet_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }


def spawn_packet(
    channel: str,
    nickname: str,
    author_id: str,
    boss: str = "imperial_tree"
):
    return create_packet(
        TYPE_SPAWN,
        boss=boss,
        channel=channel,
        nickname=nickname,
        author_id=author_id,
        message=f"🚨 Императорское древо скоро появится | {channel}"
    )


def chat_packet(
    nickname: str,
    message: str,
    author_id: str,
):
    return create_packet(
        TYPE_CHAT,
        nickname=nickname,
        author_id=author_id,
        message=message
    )


def reaction_packet(message_id: str, voter_id: str, value: int):
    return create_packet(
        TYPE_REACTION,
        message_id=message_id,
        voter_id=voter_id,
        value=0 if int(value) == 0 else (1 if int(value) > 0 else -1),
    )


def admin_packet(action: str, target: str = "", nickname: str = ""):
    return create_packet("admin", action=action, target=str(target), nickname=str(nickname)[:16])
