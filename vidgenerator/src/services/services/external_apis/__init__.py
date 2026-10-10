"""
External API Services Integration
Integrates with Hedy, SeaGOAT, Fake News Detector, Hypertxt, Vertech Academy
"""

from .seagoat_service import SeaGOATService
from .fake_news_detector import FakeNewsDetector
from .hedy_service import HedyService

__all__ = ['SeaGOATService', 'FakeNewsDetector', 'HedyService']

