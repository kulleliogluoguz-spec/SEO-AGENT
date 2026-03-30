"""
Slack Notifier Connector.

Sends notifications for approvals, reports, and alerts.
MOCK mode logs to console. REAL mode uses Slack API.
"""
import structlog
from app.core.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class SlackConnector:
    """Sends Slack notifications."""

    def __init__(self) -> None:
        self._mock_mode = settings.slack_mock_mode

    async def send_approval_request(
        self,
        title: str,
        description: str,
        approval_url: str,
        risk_level: str = "medium",
    ) -> bool:
        if self._mock_mode:
            logger.info("slack.mock_approval", title=title, risk=risk_level)
            return True
        return await self._send_message(
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Approval Required:* {title}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": description}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Risk: *{risk_level}* | <{approval_url}|Review>"}},
            ]
        )

    async def send_report_ready(self, report_title: str, report_url: str) -> bool:
        if self._mock_mode:
            logger.info("slack.mock_report", title=report_title)
            return True
        return await self._send_message(
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": f"📊 *Report ready:* {report_title}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"<{report_url}|View Report>"}},
            ]
        )

    async def _send_message(self, blocks: list[dict]) -> bool:
        if not settings.slack_bot_token:
            logger.warning("slack.no_token_configured")
            return False
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                    json={"channel": "#growth-alerts", "blocks": blocks},
                )
                return r.json().get("ok", False)
        except Exception as e:
            logger.error("slack.send_failed", error=str(e))
            return False
