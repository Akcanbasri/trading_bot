"""
Trade Logger module.

Bu modül, trade işlemlerini terminale ve dosyaya loglamak için kullanılan
TradeLogger sınıfını içerir.
"""
import os
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import json
from loguru import logger

from src.config import settings


class LogType(Enum):
    """Log tipleri."""
    TRADE_OPEN = "TRADE_OPEN"           # İşlem açma
    TRADE_CLOSE = "TRADE_CLOSE"         # İşlem kapama
    SIGNAL = "SIGNAL"                   # Sinyal algılama
    ERROR = "ERROR"                     # Hata durumu
    INFO = "INFO"                       # Bilgi mesajı
    WARNING = "WARNING"                 # Uyarı mesajı
    SYSTEM = "SYSTEM"                   # Sistem mesajı


class TradeLogger:
    """
    Trade işlemlerini terminale ve bir .txt dosyasına loglar.
    İşlem açma, kapama, sinyal algılama ve hata durumları için farklı
    formatlarda log mesajları oluşturur.
    """

    def __init__(
        self, 
        log_dir: str = "logs",
        log_file: Optional[str] = None,
        console_output: bool = True,
        detailed_file_logs: bool = True
    ):
        """
        TradeLogger sınıfını başlatır.
        
        Args:
            log_dir: Log dosyalarının kaydedileceği dizin
            log_file: Log dosyası adı (None ise tarih ile otomatik oluşturulur)
            console_output: Terminale de yazdırılıp yazdırılmayacağı
            detailed_file_logs: Detaylı log oluşturulup oluşturulmayacağı
        """
        self.log_dir = log_dir
        self.console_output = console_output
        self.detailed_file_logs = detailed_file_logs
        
        # Log dizinini oluştur
        os.makedirs(log_dir, exist_ok=True)
        
        # Log dosyası adını belirle
        if log_file is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
            log_file = f"trades_{current_date}.txt"
        
        self.log_file_path = os.path.join(log_dir, log_file)
        
        # İlk başlatma mesajı
        self._write_to_file(f"=== TRADE LOGGER BAŞLATILDI: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        logger.info(f"Trade Logger başlatıldı, log dosyası: {self.log_file_path}")
    
    def log_trade_open(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float, 
        order_id: Optional[str] = None,
        signals: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> None:
        """
        Yeni bir işlem açıldığında log kaydı oluşturur.
        
        Args:
            symbol: İşlem yapılan coin sembolü
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: İşlem miktarı
            price: İşlem fiyatı
            order_id: Emir ID'si
            signals: İşleme neden olan sinyaller
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        message = f"[{current_time}] {LogType.TRADE_OPEN.value} | {symbol} | {side} | Miktar: {quantity:.8f} | Fiyat: {price:.8f}"
        
        if order_id:
            message += f" | Order ID: {order_id}"
        
        # Konsolda göster
        if self.console_output:
            icon = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
            direction = "LONG" if side == "BUY" else "SHORT" if side == "SELL" else "UNKNOWN"
            colored_message = f"{icon} İŞLEM AÇILDI: {direction} {quantity:.8f} {symbol} @ {price:.8f}"
            logger.info(colored_message)
        
        # Dosyaya yaz
        self._write_to_file(message)
        
        # Detaylı log
        if self.detailed_file_logs:
            details = {
                "type": LogType.TRADE_OPEN.value,
                "time": current_time,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_id": order_id,
                "signals": signals,
                **kwargs
            }
            self._write_details_to_file(details)
    
    def log_trade_close(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percentage: float,
        duration: Optional[float] = None,
        order_id: Optional[str] = None,
        signals: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> None:
        """
        Bir işlem kapatıldığında log kaydı oluşturur.
        
        Args:
            symbol: İşlem yapılan coin sembolü
            side: Kapatılan pozisyon yönü ("LONG" veya "SHORT")
            quantity: İşlem miktarı
            entry_price: Giriş fiyatı
            exit_price: Çıkış fiyatı
            pnl: Kar/zarar (USDT)
            pnl_percentage: Kar/zarar yüzdesi
            duration: İşlem süresi (saniye)
            order_id: Emir ID'si
            signals: İşleme neden olan sinyaller
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        message = f"[{current_time}] {LogType.TRADE_CLOSE.value} | {symbol} | {side} | Miktar: {quantity:.8f} | Giriş: {entry_price:.8f} | Çıkış: {exit_price:.8f} | PNL: {pnl:.8f} ({pnl_percentage:.2f}%)"
        
        if duration:
            # Süreyi okunabilir formata dönüştür
            hours, remainder = divmod(duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(hours)}s {int(minutes)}d {int(seconds)}s"
            message += f" | Süre: {duration_str}"
        
        if order_id:
            message += f" | Order ID: {order_id}"
        
        # Konsolda göster
        if self.console_output:
            icon = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            colored_message = f"{icon} İŞLEM KAPATILDI: {side} {quantity:.8f} {symbol} | PNL: {pnl:.8f} ({pnl_percentage:.2f}%)"
            logger.info(colored_message)
        
        # Dosyaya yaz
        self._write_to_file(message)
        
        # Detaylı log
        if self.detailed_file_logs:
            details = {
                "type": LogType.TRADE_CLOSE.value,
                "time": current_time,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "duration": duration,
                "order_id": order_id,
                "signals": signals,
                **kwargs
            }
            self._write_details_to_file(details)
    
    def log_signal(
        self, 
        symbol: str, 
        signal_type: str, 
        source: str,
        price: Optional[float] = None,
        strength: Optional[float] = None,
        indicators: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Bir sinyal algılandığında log kaydı oluşturur.
        
        Args:
            symbol: Sinyal algılanan coin sembolü
            signal_type: Sinyal tipi (LONG, SHORT, NEUTRAL, vb.)
            source: Sinyal kaynağı (gösterge adı vb.)
            price: Sinyal anındaki fiyat
            strength: Sinyal gücü (0-100)
            indicators: Gösterge değerleri
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        message = f"[{current_time}] {LogType.SIGNAL.value} | {symbol} | {signal_type} | Kaynak: {source}"
        
        if price:
            message += f" | Fiyat: {price:.8f}"
        
        if strength:
            message += f" | Güç: {strength:.2f}"
        
        # Konsolda göster
        if self.console_output:
            icon = "⬆️" if signal_type == "LONG" else "⬇️" if signal_type == "SHORT" else "⏹️"
            colored_message = f"{icon} SİNYAL: {signal_type} {symbol} ({source})"
            if strength:
                colored_message += f" | Güç: {strength:.2f}"
            logger.debug(colored_message)
        
        # Dosyaya yaz
        self._write_to_file(message)
        
        # Detaylı log
        if self.detailed_file_logs:
            details = {
                "type": LogType.SIGNAL.value,
                "time": current_time,
                "symbol": symbol,
                "signal_type": signal_type,
                "source": source,
                "price": price,
                "strength": strength,
                "indicators": indicators,
                **kwargs
            }
            self._write_details_to_file(details)
    
    def log_error(
        self, 
        error_message: str, 
        symbol: Optional[str] = None, 
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Bir hata durumunda log kaydı oluşturur.
        
        Args:
            error_message: Hata mesajı
            symbol: İlgili coin sembolü
            operation: Hata oluşan işlem
            details: Hata detayları
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        message = f"[{current_time}] {LogType.ERROR.value}"
        
        if symbol:
            message += f" | {symbol}"
        
        if operation:
            message += f" | {operation}"
        
        message += f" | {error_message}"
        
        # Konsolda göster
        if self.console_output:
            colored_message = f"❌ HATA: {error_message}"
            if symbol:
                colored_message += f" | {symbol}"
            if operation:
                colored_message += f" | {operation}"
            logger.error(colored_message)
        
        # Dosyaya yaz
        self._write_to_file(message)
        
        # Detaylı log
        if self.detailed_file_logs:
            error_details = {
                "type": LogType.ERROR.value,
                "time": current_time,
                "symbol": symbol,
                "operation": operation,
                "error_message": error_message,
                "details": details,
                **kwargs
            }
            self._write_details_to_file(error_details)
    
    def log_info(self, message: str, **kwargs) -> None:
        """
        Bilgi mesajı loglar.
        
        Args:
            message: Bilgi mesajı
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        log_message = f"[{current_time}] {LogType.INFO.value} | {message}"
        
        # Konsolda göster
        if self.console_output:
            logger.info(f"ℹ️ {message}")
        
        # Dosyaya yaz
        self._write_to_file(log_message)
        
        # Detaylı log
        if self.detailed_file_logs and kwargs:
            info_details = {
                "type": LogType.INFO.value,
                "time": current_time,
                "message": message,
                **kwargs
            }
            self._write_details_to_file(info_details)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """
        Uyarı mesajı loglar.
        
        Args:
            message: Uyarı mesajı
            **kwargs: Ek bilgiler
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Temel log mesajı
        log_message = f"[{current_time}] {LogType.WARNING.value} | {message}"
        
        # Konsolda göster
        if self.console_output:
            logger.warning(f"⚠️ {message}")
        
        # Dosyaya yaz
        self._write_to_file(log_message)
        
        # Detaylı log
        if self.detailed_file_logs and kwargs:
            warning_details = {
                "type": LogType.WARNING.value,
                "time": current_time,
                "message": message,
                **kwargs
            }
            self._write_details_to_file(warning_details)
    
    def _write_to_file(self, message: str) -> None:
        """
        Mesajı log dosyasına yazar.
        
        Args:
            message: Yazılacak mesaj
        """
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as file:
                file.write(message + "\n")
        except Exception as e:
            logger.error(f"Log dosyasına yazılırken hata oluştu: {e}")
    
    def _write_details_to_file(self, details: Dict[str, Any]) -> None:
        """
        Detaylı bilgileri ayrı bir JSON dosyasına yazar.
        
        Args:
            details: Yazılacak detaylar
        """
        try:
            # Ana log dosyasının adından JSON dosyası adı oluştur
            base_name = os.path.basename(self.log_file_path)
            file_name, ext = os.path.splitext(base_name)
            json_file_path = os.path.join(self.log_dir, f"{file_name}_details.json")
            
            # Varolan dosyayı yükle veya yeni bir liste oluştur
            if os.path.exists(json_file_path):
                with open(json_file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                    except json.JSONDecodeError:
                        data = []
            else:
                data = []
            
            # Yeni detayları ekle
            data.append(details)
            
            # Dosyaya geri yaz
            with open(json_file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Detaylı log yazılırken hata oluştu: {e}")
    
    def get_today_trades(self) -> List[Dict[str, Any]]:
        """
        Bugünkü işlemleri döndürür.
        
        Returns:
            List[Dict[str, Any]]: Bugünkü işlemler
        """
        try:
            base_name = os.path.basename(self.log_file_path)
            file_name, ext = os.path.splitext(base_name)
            json_file_path = os.path.join(self.log_dir, f"{file_name}_details.json")
            
            if os.path.exists(json_file_path):
                with open(json_file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                        # Sadece işlem kayıtlarını filtrele
                        trades = [
                            item for item in data 
                            if item.get("type") in [LogType.TRADE_OPEN.value, LogType.TRADE_CLOSE.value]
                        ]
                        return trades
                    except json.JSONDecodeError:
                        return []
            return []
        except Exception as e:
            logger.error(f"İşlem geçmişi okunurken hata oluştu: {e}")
            return []
    
    def get_today_signals(self) -> List[Dict[str, Any]]:
        """
        Bugünkü sinyalleri döndürür.
        
        Returns:
            List[Dict[str, Any]]: Bugünkü sinyaller
        """
        try:
            base_name = os.path.basename(self.log_file_path)
            file_name, ext = os.path.splitext(base_name)
            json_file_path = os.path.join(self.log_dir, f"{file_name}_details.json")
            
            if os.path.exists(json_file_path):
                with open(json_file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                        # Sadece sinyal kayıtlarını filtrele
                        signals = [
                            item for item in data 
                            if item.get("type") == LogType.SIGNAL.value
                        ]
                        return signals
                    except json.JSONDecodeError:
                        return []
            return []
        except Exception as e:
            logger.error(f"Sinyal geçmişi okunurken hata oluştu: {e}")
            return []
    
    def get_today_errors(self) -> List[Dict[str, Any]]:
        """
        Bugünkü hataları döndürür.
        
        Returns:
            List[Dict[str, Any]]: Bugünkü hatalar
        """
        try:
            base_name = os.path.basename(self.log_file_path)
            file_name, ext = os.path.splitext(base_name)
            json_file_path = os.path.join(self.log_dir, f"{file_name}_details.json")
            
            if os.path.exists(json_file_path):
                with open(json_file_path, "r", encoding="utf-8") as file:
                    try:
                        data = json.load(file)
                        # Sadece hata kayıtlarını filtrele
                        errors = [
                            item for item in data 
                            if item.get("type") == LogType.ERROR.value
                        ]
                        return errors
                    except json.JSONDecodeError:
                        return []
            return []
        except Exception as e:
            logger.error(f"Hata geçmişi okunurken hata oluştu: {e}")
            return []


# Singleton örnek oluştur
_trade_logger_instance = None

def get_trade_logger() -> TradeLogger:
    """
    TradeLogger sınıfının singleton örneğini döndürür.
    
    Returns:
        TradeLogger: Logger örneği
    """
    global _trade_logger_instance
    
    if _trade_logger_instance is None:
        # Logger dizinini ayarlardan al
        log_dir = settings.LOG_CONFIG.get("log_dir", "logs")
        
        # Yeni bir örnek oluştur
        _trade_logger_instance = TradeLogger(log_dir=log_dir)
    
    return _trade_logger_instance 