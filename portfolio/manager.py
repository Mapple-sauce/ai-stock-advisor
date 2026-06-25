"""持仓管理器"""

from __future__ import annotations

from datetime import date
from portfolio.storage import PortfolioStorage


class PortfolioManager:
    def __init__(self):
        self.storage = PortfolioStorage()

    def get_all(self) -> list[dict]:
        return self.storage.load()

    def add(self, symbol: str, name: str, cost_price: float, quantity: int = 100, reason: str = "") -> dict:
        holding = {
            "symbol": symbol,
            "name": name,
            "cost_price": cost_price,
            "current_price": cost_price,
            "quantity": quantity,
            "buy_date": str(date.today()),
            "reason": reason,
            "pnl_pct": 0.0,
            "hold_days": 0,
        }
        holdings = self.storage.load()
        holdings.append(holding)
        self.storage.save(holdings)
        return holding

    def remove(self, symbol: str) -> bool:
        holdings = self.storage.load()
        new_h = [h for h in holdings if h["symbol"] != symbol]
        if len(new_h) == len(holdings):
            return False
        self.storage.save(new_h)
        return True

    def update_price(self, symbol: str, price: float) -> dict | None:
        holdings = self.storage.load()
        for h in holdings:
            if h["symbol"] == symbol:
                h["current_price"] = price
                cost = h["cost_price"]
                h["pnl_pct"] = round((price - cost) / cost * 100, 2) if cost else 0
                # 计算持仓天数
                try:
                    buy = date.fromisoformat(h.get("buy_date", str(date.today())))
                    h["hold_days"] = (date.today() - buy).days
                except Exception:
                    h["hold_days"] = 0
                self.storage.save(holdings)
                return h
        return None

    def get_summary(self) -> dict:
        holdings = self.get_all()
        if not holdings:
            return {"total": 0, "holdings": [], "total_cost": 0, "total_value": 0, "total_pnl_pct": 0}
        total_cost = sum(h["cost_price"] * h.get("quantity", 100) for h in holdings)
        total_value = sum(h.get("current_price", h["cost_price"]) * h.get("quantity", 100) for h in holdings)
        return {
            "total": len(holdings),
            "holdings": holdings,
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0,
        }
