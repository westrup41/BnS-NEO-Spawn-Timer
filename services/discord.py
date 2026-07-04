import json
import urllib.request
import urllib.error

def post_discord_webhook(webhook_url: str, content: str, allow_everyone: bool = True):
    payload = {
        "content": content,
        "allowed_mentions": {"parse": ["everyone", "roles"] if allow_everyone else []},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BNS-NEO-Spawn-Timer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = getattr(response, "status", response.getcode())
            if status in (200, 204):
                return True, ""
            return False, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:260]
        except Exception:
            detail = ""
        return False, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, str(exc)