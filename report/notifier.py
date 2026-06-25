"""通知推送"""

from __future__ import annotations

from config import settings
from httpx import Client, Timeout


def send_wechat_markdown(content: str) -> bool:
    """推送到企业微信群机器人"""
    if not settings.wechat_webhook_url:
        print("⚠️ WECHAT_WEBHOOK_URL 未配置, 跳过推送")
        return False

    # 企业微信 Markdown 有长度限制 (4096)
    if len(content) > 4000:
        content = content[:3900] + "\n\n> ...内容较长, 请在 GitHub Actions 日志中查看完整报告"

    payload = {"msgtype": "markdown", "markdown": {"content": content}}

    try:
        with Client(timeout=Timeout(10.0)) as client:
            resp = client.post(settings.wechat_webhook_url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") == 0:
                print("✅ 企业微信推送成功")
                return True
            print(f"⚠️ 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False


def send_report(report: str, title: str = "AI 报告") -> None:
    """发送报告到配置的渠道"""
    preview = f"## {title}\n\n{report[:600]}"
    send_wechat_markdown(preview)
