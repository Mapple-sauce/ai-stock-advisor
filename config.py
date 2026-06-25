"""全局配置管理"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # ── AI 模型 ──
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "deepseek-chat"))

    # ── Agent 专属模型 (可选覆盖) ──
    technical_model: str = field(default_factory=lambda: os.getenv("TECHNICAL_MODEL", ""))
    fundamental_model: str = field(default_factory=lambda: os.getenv("FUNDAMENTAL_MODEL", ""))
    sentiment_model: str = field(default_factory=lambda: os.getenv("SENTIMENT_MODEL", ""))
    risk_model: str = field(default_factory=lambda: os.getenv("RISK_MODEL", ""))
    chief_model: str = field(default_factory=lambda: os.getenv("CHIEF_MODEL", ""))

    # ── Agent 温度 ──
    agent_temperature: float = field(default_factory=lambda: float(os.getenv("AGENT_TEMPERATURE", "0.3")))
    chief_temperature: float = field(default_factory=lambda: float(os.getenv("CHIEF_TEMPERATURE", "0.2")))

    # ── 通知 ──
    wechat_webhook_url: str = field(default_factory=lambda: os.getenv("WECHAT_WEBHOOK_URL", ""))

    # ── 股票列表 ──
    stock_list: list[str] = field(default_factory=lambda: _parse_list("STOCK_LIST"))
    watch_list: list[str] = field(default_factory=lambda: _parse_list("WATCH_LIST"))

    # ── 运行模式 ──
    run_mode: str = field(default_factory=lambda: os.getenv("RUN_MODE", "all"))
    report_language: str = field(default_factory=lambda: os.getenv("REPORT_LANGUAGE", "zh"))

    # ── 扫描参数 ──
    scan_top_n: int = field(default_factory=lambda: int(os.getenv("SCAN_TOP_N", "10")))

    # ── 路径 ──
    portfolio_path: Path = field(
        default_factory=lambda: Path(os.getenv("PORTFOLIO_PATH", "data/portfolio.json"))
    )

    @property
    def is_ready(self) -> bool:
        if not self.openai_api_key:
            print("❌ 未配置 OPENAI_API_KEY")
            return False
        return True

    def get_agent_model(self, agent_name: str) -> str:
        """获取指定 Agent 的模型, 如果没有专属配置则使用默认模型"""
        override = getattr(self, f"{agent_name}_model", "")
        return override or self.openai_model


def _parse_list(env_key: str) -> list[str]:
    raw = os.getenv(env_key, "")
    return [s.strip() for s in raw.split(",") if s.strip()]


settings = Settings()
