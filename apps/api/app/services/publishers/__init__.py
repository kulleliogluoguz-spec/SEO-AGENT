"""
Publisher service layer — channel-specific content publishing abstractions.

Each publisher implements PublisherService and handles:
  - credential validation
  - OAuth scope validation
  - text post publishing
  - media post publishing
  - post status retrieval
  - rate-limit handling
  - audit trail

Usage:
  from app.services.publishers import get_publisher
  publisher = get_publisher("x", user_id)
  result = await publisher.publish_text_post(text="Hello world", user_id=user_id)
"""
from app.services.publishers.base import PublisherService, PublishResult, PublisherStatus
from app.services.publishers.x_publisher import XPublisher
from app.services.publishers.instagram_publisher import InstagramPublisher
from app.services.publishers.tiktok_publisher import TikTokPublisher

PUBLISHER_REGISTRY: dict[str, type[PublisherService]] = {
    "x": XPublisher,
    "twitter": XPublisher,
    "instagram": InstagramPublisher,
    "tiktok": TikTokPublisher,
}


def get_publisher(channel: str, user_id: str) -> PublisherService:
    """Return the publisher instance for a channel, initialized with the user's credentials."""
    cls = PUBLISHER_REGISTRY.get(channel.lower())
    if not cls:
        raise ValueError(f"No publisher available for channel '{channel}'. Available: {list(PUBLISHER_REGISTRY)}")
    return cls(user_id=user_id)


__all__ = [
    "PublisherService", "PublishResult", "PublisherStatus",
    "XPublisher", "InstagramPublisher", "TikTokPublisher",
    "PUBLISHER_REGISTRY", "get_publisher",
]
