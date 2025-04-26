"""
Log Throttler sınıfı.

Bu modül, log mesajlarının sıklığını kontrol etmek için kullanılır.
"""

import time
from typing import Dict, Optional
from loguru import logger


class LogThrottler:
    """
    Log Throttler sınıfı.

    Log mesajlarının sıklığını kontrol etmek için kullanılır.
    """

    def __init__(self, default_interval: float = 60.0):
        """
        Log Throttler sınıfını başlatır.

        Args:
            default_interval: Varsayılan log aralığı (saniye)
        """
        self.default_interval = default_interval
        self.last_log_time: Dict[str, float] = {}
        self.intervals: Dict[str, float] = {}

    def set_interval(self, log_type: str, interval: float) -> None:
        """
        Belirli bir log tipi için aralık ayarlar.

        Args:
            log_type: Log tipi
            interval: Log aralığı (saniye)
        """
        self.intervals[log_type] = interval

    def log(self, log_type: str, message: str, level: str = "info") -> None:
        """
        Log mesajı yazar.

        Args:
            log_type: Log tipi
            message: Log mesajı
            level: Log seviyesi (info, debug, warning, error)
        """
        current_time = time.time()
        last_time = self.last_log_time.get(log_type, 0)
        interval = self.intervals.get(log_type, self.default_interval)

        if current_time - last_time >= interval:
            if level == "info":
                logger.info(message)
            elif level == "debug":
                logger.debug(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
            else:
                logger.info(message)

            self.last_log_time[log_type] = current_time
