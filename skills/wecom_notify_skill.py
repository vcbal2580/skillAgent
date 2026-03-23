"""
WeCom (企业微信) Notify Skill
Sends messages to a WeCom group robot via Webhook URL.

Supports:
  - text     : plain text, with optional @mentions
  - markdown : markdown formatted message
  - news     : news card with title, description, url, picurl

Setup:
  In WeCom group → Add Robot → copy the Webhook URL
  Set it in config.yaml:
    wecom:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
"""

import json
import urllib.request
import urllib.error
from typing import Any

from skills.base import BaseSkill
from core.config import config


class WeComNotifySkill(BaseSkill):
    name = "wecom_notify"
    description = (
        "Send a message to a WeCom (企业微信) group via group robot webhook. "
        "Supports text, markdown, and news card formats. "
        "Use this when the user asks to send a WeCom notification or reminder."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "Message content. "
                    "For text: plain string. "
                    "For markdown: markdown formatted string. "
                    "For news: JSON string with keys title, description, url (picurl optional)."
                ),
            },
            "msg_type": {
                "type": "string",
                "enum": ["text", "markdown", "news"],
                "description": "Message format type. Default: text",
            },
            "mentioned_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of WeCom user IDs or mobile numbers to @mention (text type only). "
                    "Use ['@all'] to mention everyone."
                ),
            },
        },
        "required": ["content"],
    }

    # ------------------------------------------------------------------ #

    def execute(self, content: str, msg_type: str = "text",
                mentioned_list: list[str] | None = None, **_) -> str:
        webhook_url = config.get("wecom.webhook_url", "")
        if not webhook_url:
            return (
                "错误：未配置企业微信 Webhook URL。"
                "请在 config.yaml 中设置 wecom.webhook_url。"
            )

        try:
            payload = self._build_payload(content, msg_type, mentioned_list or [])
            result = self._post(webhook_url, payload)
            if result.get("errcode") == 0:
                return f"消息发送成功（类型：{msg_type}）"
            else:
                return f"发送失败：errcode={result.get('errcode')} errmsg={result.get('errmsg')}"
        except urllib.error.URLError as e:
            return f"网络错误：{e.reason}"
        except Exception as e:  # noqa: BLE001
            return f"发送失败：{e}"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _build_payload(
        self,
        content: str,
        msg_type: str,
        mentioned_list: list[str],
    ) -> dict[str, Any]:
        if msg_type == "markdown":
            return {
                "msgtype": "markdown",
                "markdown": {"content": content},
            }

        if msg_type == "news":
            # content should be a JSON string with title/description/url
            try:
                article = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: treat whole content as title
                article = {"title": content, "url": ""}
            return {
                "msgtype": "news",
                "news": {
                    "articles": [
                        {
                            "title": article.get("title", ""),
                            "description": article.get("description", ""),
                            "url": article.get("url", ""),
                            "picurl": article.get("picurl", ""),
                        }
                    ]
                },
            }

        # Default: text
        payload: dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": content},
        }
        if mentioned_list:
            payload["text"]["mentioned_list"] = mentioned_list
        return payload

    @staticmethod
    def _post(url: str, payload: dict) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
