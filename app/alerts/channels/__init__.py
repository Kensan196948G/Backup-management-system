"""
Notification Channels
Provides various channels for sending notifications
"""

from .email import EmailChannel
from .slack import SlackChannel

__all__ = ["EmailChannel", "SlackChannel"]
