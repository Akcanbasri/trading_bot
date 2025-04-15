"""
TradeLogger kullanım örneği.

Bu örnek, TradeLogger sınıfının trade işlemlerini loglamak için
nasıl kullanılacağını gösterir.
"""
import os
import sys
import time
from datetime import datetime
import pandas as pd
from loguru import logger

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.trade_logger import TradeLogger, get_trade_logger
from src.config import settings


def simulate_trade_cycle():
    """
    Bir ticaret döngüsü simüle eder ve loglar.
    """
    # TradeLogger özel örneği oluştur
    logger = TradeLogger(log_dir="logs/example")
    
    # Sembol ve işlem detayları
    symbol = "BTCUSDT"
    quantity = 0.01
    entry_price = 50000.0
    
    # Şu anki zaman
    now = datetime.now()
    
    # 1. Sinyal algılama logla
    logger.log_signal(
        symbol=symbol,
        signal_type="LONG",
        source="RSI_Middle_Band",
        price=entry_price,
        strength=80.5,
        indicators={
            "rsi": 32.5,
            "rsi_ema": 45.2,
            "momentum": "positive"
        }
    )
    
    # Kısa bekleme
    time.sleep(1)
    
    # 2. İşlem açma logla
    order_id = "12345678"
    logger.log_trade_open(
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        price=entry_price,
        order_id=order_id,
        signals={
            "RSI_Middle_Band": "LONG",
            "RSI": "NEUTRAL"
        },
        risk_reward=2.5,  # Ek bilgi
        strategy="trend_following"  # Ek bilgi
    )
    
    # Bekle - işlemin açık kaldığı süre
    time.sleep(2)
    
    # 3. Kapanış sinyali logla
    exit_price = 51000.0
    logger.log_signal(
        symbol=symbol,
        signal_type="CLOSE_LONG",
        source="RSI_Middle_Band",
        price=exit_price,
        strength=65.0,
        indicators={
            "rsi": 68.2,
            "rsi_ema": 60.1,
            "momentum": "neutral"
        }
    )
    
    # Bekle - sinyal ve işlem arasında geçen süre
    time.sleep(1)
    
    # 4. İşlem kapama logla
    pnl = (exit_price - entry_price) * quantity
    pnl_percentage = (exit_price - entry_price) / entry_price * 100
    duration = (datetime.now() - now).total_seconds()
    
    logger.log_trade_close(
        symbol=symbol,
        side="LONG",
        quantity=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        pnl=pnl,
        pnl_percentage=pnl_percentage,
        duration=duration,
        order_id="87654321",
        signals={
            "RSI_Middle_Band": "CLOSE_LONG",
            "RSI": "NEUTRAL"
        },
        trade_duration_hours=duration/3600  # Ek bilgi
    )
    
    # 5. Bilgi mesajı logla
    logger.log_info(f"{symbol} için işlem tamamlandı, PNL: {pnl:.2f} USDT")
    
    # 6. Hata durumu simüle et
    try:
        # Kasıtlı hata oluştur
        result = 1 / 0
    except Exception as e:
        logger.log_error(
            error_message=f"İşlem sırasında hata: {e}",
            symbol=symbol,
            operation="pozisyon_kapatma",
            details={
                "exception": str(e),
                "traceback": "ZeroDivisionError: division by zero"
            }
        )
    
    # 7. Uyarı mesajı
    logger.log_warning(
        f"{symbol} için stop loss seviyesi çok yakın",
        symbol=symbol,
        current_price=exit_price,
        stop_loss=exit_price * 0.98
    )
    
    # Log kayıtlarını görüntüle
    print("\nKayıtlar başarıyla oluşturuldu!")
    print(f"Log dosyası: {logger.log_file_path}")
    
    # JSON detayları görüntüle
    base_name = os.path.basename(logger.log_file_path)
    file_name, ext = os.path.splitext(base_name)
    json_file_path = os.path.join(logger.log_dir, f"{file_name}_details.json")
    print(f"Detaylı JSON: {json_file_path}")
    
    # Bugünün trade'lerini göster
    trades = logger.get_today_trades()
    print(f"\nBugünün işlemleri: {len(trades)} adet")


def use_singleton_logger():
    """
    Singleton logger örneğini kullanır.
    """
    # Singleton logger örneğini al
    logger = get_trade_logger()
    
    # Bilgi mesajı logla
    logger.log_info("Singleton logger örneği çalışıyor")
    
    # Örnek sinyal
    logger.log_signal(
        symbol="ETHUSDT",
        signal_type="SHORT",
        source="RSI",
        price=3000.0,
        strength=75.0
    )
    
    print("\nSingleton logger örneği başarıyla kullanıldı!")
    print(f"Log dosyası: {logger.log_file_path}")


def main():
    """
    TradeLogger örneğini çalıştırır.
    """
    logger.info("TradeLogger örneği başlatılıyor...")
    
    # Ticaret döngüsü simülasyonu
    simulate_trade_cycle()
    
    # Singleton örneği kullanımı
    use_singleton_logger()
    
    logger.info("TradeLogger örneği tamamlandı.")


if __name__ == "__main__":
    # Log ayarları
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Ana fonksiyonu çalıştır
    main() 