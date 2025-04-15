"""
Logging için yardımcı modül.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from loguru import logger


def setup_logger(log_level: str = None):
    """
    Loguru logger'ı yapılandırır.
    
    Args:
        log_level: Ayarlanacak log seviyesi (INFO, DEBUG, ERROR, etc.)
        
    Returns:
        configured logger
    """
    # .env'den log seviyesini oku, eğer parametre olarak verilmediyse
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Log dizini
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Log dosya adı (tarih format)
    log_file = log_dir / f"trading_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Mevcut konfigürasyonu temizle
    logger.remove()
    
    # Konsol logger formatı
    logger.add(
        sys.stderr, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level
    )
    
    # Dosya logger formatı
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="100 MB",
        retention="30 days"
    )
    
    # Hata durumlarını yakalamak için exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Yakalanmamış hata!")
    
    sys.excepthook = handle_exception
    
    return logger 