"""持仓持久化 —— JSON 文件"""

from __future__ import annotations

import json
from pathlib import Path

from config import settings


class PortfolioStorage:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.portfolio_path
        self._ensure()

    def _ensure(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, holdings: list[dict]):
        self.path.write_text(json.dumps(holdings, ensure_ascii=False, indent=2), encoding="utf-8")
