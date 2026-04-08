"""
LiveKit Engine — browser-based WebRTC calling with automatic recording.

Self-hosted, zero per-minute cost, full control. The livekit-api SDK is
imported lazily so the rest of the platform can start without it.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")


class LiveKitEngine:
    """Manages LiveKit rooms for browser-based calls."""

    def create_room_name(self, call_id: str) -> str:
        return f"call-{call_id}"

    def generate_token(
        self,
        room_name: str,
        participant_identity: str,
        is_agent: bool = False,
    ) -> str:
        """Generate a JWT token for LiveKit room access."""
        try:
            from livekit.api import AccessToken, VideoGrants  # type: ignore

            token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            token.with_identity(participant_identity)
            token.with_name(participant_identity)
            grants = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
            token.with_grants(grants)
            return token.to_jwt()
        except ImportError:
            logger.warning("livekit-api not installed")
            return ""
        except Exception as e:
            logger.error("Token generation failed: %s", e)
            return ""

    async def start_room_recording(self, call_id: str, output_path: str) -> str | None:
        """Start recording a LiveKit room via Egress API."""
        try:
            from livekit.api import LiveKitAPI  # type: ignore

            room_name = self.create_room_name(call_id)
            async with LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) as api:
                egress = await api.egress.start_room_composite_egress(
                    room_name=room_name,
                    audio_only=True,
                    file_outputs=[{"filepath": output_path, "audio_only": True}],
                )
                return egress.egress_id
        except ImportError:
            logger.warning("livekit-api not installed; recording start skipped")
            return None
        except Exception as e:
            logger.error("LiveKit recording start failed: %s", e)
            return None

    async def stop_recording(self, egress_id: str) -> bool:
        """Stop a LiveKit recording."""
        try:
            from livekit.api import LiveKitAPI  # type: ignore

            async with LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) as api:
                await api.egress.stop_egress(egress_id=egress_id)
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.error("LiveKit stop recording failed: %s", e)
            return False
