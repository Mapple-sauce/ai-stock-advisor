"""个股新闻监控 —— 轮询新消息、检测重要变动、触发通知和报告更新

典型用法:
    from analysis.monitor import NewsMonitor
    monitor = NewsMonitor()
    monitor.start_monitoring(["002594", "601012"], interval_minutes=60)
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Any

from config import settings
from data.news import get_stock_news
from report.notifier import send_wechat_markdown

# ── 重要新闻关键词 ──
_IMPORTANT_KW = [
    "业绩", "预增", "预减", "扭亏", "亏损", "首亏",
    "重组", "并购", "收购", "增发", "配股",
    "监管", "处罚", "调查", "立案", "退市", "ST",
    "战略", "合作", "中标", "交付", "量产", "获批",
    "减持", "增持", "回购", "分红", "送转",
    "专利", "突破", "认证", "准入",
    "人事变动", "董事长", "总经理",
]

# ── 情绪关键词 ──
_POSITIVE_KW = ["中标", "突破", "量产", "获批", "认证", "增持", "回购", "扭亏",
                "战略", "合作", "交付", "专利", "准入", "预增"]
_NEGATIVE_KW = ["处罚", "调查", "立案", "亏损", "预减", "首亏", "减持",
                "退市", "ST", "监管", "人事变动"]


class NewsMonitor:
    """个股新闻监控 —— 轮询新消息、检测重要变动、触发通知"""

    def __init__(self, state_file: str = "data/monitor_state.json"):
        self.last_check: dict[str, str] = {}      # {symbol: last_check_time}
        self.seen_ids: dict[str, set[str]] = {}   # {symbol: set(news_id)}
        self.state_file = Path(state_file)
        self.load_state()

    # ════════════════════════════════════════════════════════════
    #  公共方法
    # ════════════════════════════════════════════════════════════

    def start_monitoring(self, symbols: list[str], interval_minutes: int = 60):
        """开始监控一组股票

        Args:
            symbols: 股票代码列表
            interval_minutes: 轮询间隔（分钟）
        """
        print(f"\n{'█'*60}")
        print(f"  🔔 个股新闻监控已启动")
        print(f"  📡 监控: {', '.join(symbols)}")
        print(f"  ⏱ 间隔: {interval_minutes} 分钟")
        print(f"{'█'*60}\n")

        # 初始化监控状态
        for s in symbols:
            if s not in self.seen_ids:
                self.seen_ids[s] = set()

        try:
            while True:
                any_update = False
                for symbol in symbols:
                    updates = self.check_updates(symbol)
                    if updates:
                        any_update = True
                        self.update_and_notify(symbol, updates)

                if not any_update:
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"  [{now}] 无新消息")

                self.save_state()
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print("\n  ⏹ 监控已停止")
            self.save_state()

    def check_updates(self, symbol: str) -> list[dict]:
        """检查某个股票是否有新新闻

        Returns:
            新增的新闻列表（已去重）
        """
        news_list = get_stock_news(symbol, max_results=15)
        if not news_list:
            return []

        new_news = []
        for n in news_list:
            news_id = self._make_id(n)
            if news_id and news_id not in self.seen_ids.get(symbol, set()):
                # 添加情绪评分
                n["sentiment"] = self._classify_sentiment(str(n.get("title", "")))
                n["is_important"] = self.is_significant(n)
                new_news.append(n)
                self.seen_ids.setdefault(symbol, set()).add(news_id)

        self.last_check[symbol] = datetime.datetime.now().isoformat()
        return new_news

    def is_significant(self, news: dict) -> bool:
        """判断一条新闻是否重要（需要更新报告 + 推送）

        重要条件:
        - 标题包含预定义的重大关键词
        - 或情绪为"强烈正面"或"强烈负面"
        """
        title = str(news.get("title", ""))
        sentiment = news.get("sentiment", "")

        # 关键词匹配
        if any(kw in title for kw in _IMPORTANT_KW):
            return True

        # 极端情绪
        if sentiment in ("强烈正面", "强烈负面"):
            return True

        return False

    def update_and_notify(self, symbol: str, new_news: list[dict]):
        """触发报告更新 + 推送通知"""
        # 计算重要新闻
        important = [n for n in new_news if n.get("is_important")]
        minor = [n for n in new_news if not n.get("is_important")]

        # ── 构造推送消息 ──
        lines = [
            f"## 🔔 <font color=\"warning\">{symbol} 新消息提醒</font>",
            f"**检测到 {len(new_news)} 条新消息**",
            "",
        ]

        if important:
            lines.append("### 📢 重要消息")
            for n in important[:5]:
                sentiment_icon = "🟢" if n.get("sentiment") in ("正面", "强烈正面") else \
                    "🔴" if n.get("sentiment") in ("负面", "强烈负面") else "⚪"
                title = str(n.get("title", ""))
                time_str = str(n.get("time", ""))[:16]
                lines.append(f"- {sentiment_icon} [{time_str}] {title}")

        if minor:
            lines.append(f"\n📰 其他消息 ({len(minor)} 条)")
            for n in minor[:3]:
                title = str(n.get("title", ""))[:40]
                lines.append(f"- {title}")

        # 报告更新状态
        lines.extend([
            "",
            "---",
            f"📄 最新报告已更新: `reports/` 目录",
            "",
            "> 点击查看完整分析 | 回复 m 查看菜单",
        ])

        content = "\n".join(lines)
        print(f"\n  🔔 [{symbol}] {len(new_news)} 条新消息"
              f" ({len(important)} 条重要)")
        for n in important[:5]:
            print(f"    📢 {n.get('sentiment', '')} {str(n.get('title', ''))[:60]}")

        # 推送
        send_wechat_markdown(content)

    # ════════════════════════════════════════════════════════════
    #  状态持久化
    # ════════════════════════════════════════════════════════════

    def save_state(self):
        """保存监控状态到 JSON 文件"""
        data = {
            "last_check": self.last_check,
            "seen_ids": {k: list(v) for k, v in self.seen_ids.items()},
            "saved_at": datetime.datetime.now().isoformat(),
        }
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ⚠️ 保存监控状态失败: {e}")

    def load_state(self):
        """加载监控状态"""
        if not self.state_file.exists():
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.last_check = data.get("last_check", {})
            self.seen_ids = {
                k: set(v) for k, v in data.get("seen_ids", {}).items()
            }
            saved = data.get("saved_at", "?")
            print(f"  📋 加载监控状态: {len(self.seen_ids)} 只股票 (上次保存: {saved})")
        except Exception as e:
            print(f"  ⚠️ 加载监控状态失败: {e}")

    # ════════════════════════════════════════════════════════════
    #  内部辅助
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _make_id(news: dict) -> str:
        """生成新闻唯一 ID（基于标题 + 时间）"""
        title = str(news.get("title", "")).strip()
        time_str = str(news.get("time", "")).strip()
        if title:
            return f"{time_str}:{title[:50]}"
        return ""

    @staticmethod
    def _classify_sentiment(title: str) -> str:
        """对新闻标题做简单情绪分类"""
        title_lower = title

        pos_count = sum(1 for kw in _POSITIVE_KW if kw in title_lower)
        neg_count = sum(1 for kw in _NEGATIVE_KW if kw in title_lower)

        if pos_count >= 2:
            return "强烈正面"
        elif pos_count == 1 and neg_count == 0:
            return "正面"
        elif neg_count >= 2:
            return "强烈负面"
        elif neg_count == 1 and pos_count == 0:
            return "负面"
        return "中性"
