import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class AuditChain:
    """Append-only hash chain for tamper-evident execution/audit events."""

    def __init__(self, chain_file: Path):
        self.chain_file = Path(chain_file)
        self.chain_file.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._bootstrap_last_hash()

    def _bootstrap_last_hash(self) -> str:
        if not self.chain_file.exists():
            return "GENESIS"
        try:
            lines = self.chain_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            if not lines:
                return "GENESIS"
            last = json.loads(lines[-1])
            return str(last.get("event_hash", "GENESIS"))
        except Exception:
            return "GENESIS"

    @staticmethod
    def _canonical(obj: Dict[str, Any]) -> str:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def append(self, event_type: str, payload: Dict[str, Any], event_time_utc: Optional[str] = None) -> Dict[str, Any]:
        ts = event_time_utc or datetime.now(timezone.utc).isoformat()
        body = {
            "event_type": event_type,
            "event_time_utc": ts,
            "payload": payload,
            "prev_hash": self._last_hash,
        }
        digest = hashlib.sha256(self._canonical(body).encode("utf-8")).hexdigest()
        row = {
            **body,
            "event_hash": digest,
        }
        with self.chain_file.open("a", encoding="utf-8") as fp:
            fp.write(self._canonical(row) + "\n")
        self._last_hash = digest
        return row


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
