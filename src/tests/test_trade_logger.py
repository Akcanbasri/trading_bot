"""
TradeLogger sınıfı için test dosyası.

Bu dosya, TradeLogger sınıfının işlevlerini test eder.
"""
import os
import sys
import json
import time
import unittest
from unittest.mock import patch, mock_open
from datetime import datetime, date
import tempfile
import shutil

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.trade_logger import TradeLogger, LogType, get_trade_logger


class TestTradeLogger(unittest.TestCase):
    """TradeLogger sınıfı için test sınıfı."""
    
    def setUp(self):
        """Her test öncesi çalışacak hazırlık fonksiyonu."""
        # Geçici log dizini oluştur
        self.temp_dir = tempfile.mkdtemp()
        self.logger = TradeLogger(log_dir=self.temp_dir)
    
    def tearDown(self):
        """Her test sonrası çalışacak temizlik fonksiyonu."""
        # Geçici dizini temizle
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Logger başlatma testi."""
        # Log dizini doğru şekilde oluşturulmuş mu?
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Log dosyası doğru formatta mı?
        today = date.today().strftime("%Y-%m-%d")
        self.assertTrue(self.logger.log_file_path.endswith(f"{today}.log"))
    
    def test_custom_log_file(self):
        """Özel log dosyası adı testi."""
        custom_file = "custom_log.log"
        logger = TradeLogger(log_dir=self.temp_dir, log_file=custom_file)
        
        # Özel dosya adı kullanılmış mı?
        self.assertTrue(logger.log_file_path.endswith(custom_file))
    
    def test_log_trade_open(self):
        """Trade açma logu testi."""
        # Trade aç
        self.logger.log_trade_open(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            price=50000.0,
            order_id="123456"
        )
        
        # Log dosyası oluşturulmuş mu?
        self.assertTrue(os.path.exists(self.logger.log_file_path))
        
        # JSON detay dosyası oluşturulmuş mu?
        base_name = os.path.basename(self.logger.log_file_path)
        file_name, ext = os.path.splitext(base_name)
        json_file_path = os.path.join(self.temp_dir, f"{file_name}_details.json")
        self.assertTrue(os.path.exists(json_file_path))
        
        # JSON içeriğini doğrula
        with open(json_file_path, 'r') as f:
            details = json.load(f)
            # En az bir kayıt var mı?
            self.assertTrue(len(details) > 0)
            # Son kaydın türü TRADE_OPEN mi?
            last_entry = details[-1]
            self.assertEqual(last_entry["log_type"], LogType.TRADE_OPEN.name)
            self.assertEqual(last_entry["symbol"], "BTCUSDT")
    
    def test_log_trade_close(self):
        """Trade kapama logu testi."""
        # Trade kapat
        self.logger.log_trade_close(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.1,
            entry_price=50000.0,
            exit_price=51000.0,
            pnl=100.0,
            pnl_percentage=2.0,
            duration=3600,
            order_id="654321"
        )
        
        # Log dosyasını ve JSON detaylarını doğrula
        base_name = os.path.basename(self.logger.log_file_path)
        file_name, ext = os.path.splitext(base_name)
        json_file_path = os.path.join(self.temp_dir, f"{file_name}_details.json")
        
        with open(json_file_path, 'r') as f:
            details = json.load(f)
            last_entry = details[-1]
            self.assertEqual(last_entry["log_type"], LogType.TRADE_CLOSE.name)
            self.assertEqual(last_entry["symbol"], "BTCUSDT")
            self.assertEqual(last_entry["pnl"], 100.0)
    
    def test_log_signal(self):
        """Sinyal logu testi."""
        # Sinyal logla
        self.logger.log_signal(
            symbol="BTCUSDT",
            signal_type="LONG",
            source="RSI",
            price=50000.0,
            strength=75.0
        )
        
        # JSON detaylarını doğrula
        base_name = os.path.basename(self.logger.log_file_path)
        file_name, ext = os.path.splitext(base_name)
        json_file_path = os.path.join(self.temp_dir, f"{file_name}_details.json")
        
        with open(json_file_path, 'r') as f:
            details = json.load(f)
            last_entry = details[-1]
            self.assertEqual(last_entry["log_type"], LogType.SIGNAL.name)
            self.assertEqual(last_entry["signal_type"], "LONG")
            self.assertEqual(last_entry["source"], "RSI")
    
    def test_log_error(self):
        """Hata logu testi."""
        # Hata logla
        self.logger.log_error(
            error_message="Test error",
            symbol="BTCUSDT",
            operation="test_operation"
        )
        
        # JSON detaylarını doğrula
        base_name = os.path.basename(self.logger.log_file_path)
        file_name, ext = os.path.splitext(base_name)
        json_file_path = os.path.join(self.temp_dir, f"{file_name}_details.json")
        
        with open(json_file_path, 'r') as f:
            details = json.load(f)
            last_entry = details[-1]
            self.assertEqual(last_entry["log_type"], LogType.ERROR.name)
            self.assertEqual(last_entry["error_message"], "Test error")
    
    def test_log_info_warning(self):
        """Bilgi ve uyarı logları testi."""
        # Bilgi logla
        self.logger.log_info("Test info message")
        
        # Uyarı logla
        self.logger.log_warning("Test warning message")
        
        # JSON detaylarını doğrula
        base_name = os.path.basename(self.logger.log_file_path)
        file_name, ext = os.path.splitext(base_name)
        json_file_path = os.path.join(self.temp_dir, f"{file_name}_details.json")
        
        with open(json_file_path, 'r') as f:
            details = json.load(f)
            # Son iki kaydı kontrol et
            info_entry = details[-2]
            warning_entry = details[-1]
            self.assertEqual(info_entry["log_type"], LogType.INFO.name)
            self.assertEqual(info_entry["message"], "Test info message")
            self.assertEqual(warning_entry["log_type"], LogType.WARNING.name)
            self.assertEqual(warning_entry["message"], "Test warning message")
    
    def test_get_today_trades(self):
        """Bugünün trade'lerini getirme testi."""
        # Birkaç trade aç ve kapat
        self.logger.log_trade_open(symbol="BTCUSDT", side="BUY", quantity=0.1, price=50000.0, order_id="1")
        self.logger.log_trade_close(symbol="BTCUSDT", side="LONG", quantity=0.1, entry_price=50000.0, 
                                   exit_price=51000.0, pnl=100.0, pnl_percentage=2.0, duration=3600, order_id="2")
        self.logger.log_trade_open(symbol="ETHUSDT", side="SELL", quantity=1.0, price=3000.0, order_id="3")
        
        # Bugünün trade'lerini al
        trades = self.logger.get_today_trades()
        
        # Doğru sayıda trade dönüyor mu?
        self.assertEqual(len(trades), 3)
        
        # İçerik doğru mu?
        trade_types = [trade["log_type"] for trade in trades]
        self.assertEqual(trade_types.count(LogType.TRADE_OPEN.name), 2)
        self.assertEqual(trade_types.count(LogType.TRADE_CLOSE.name), 1)
    
    def test_get_today_signals(self):
        """Bugünün sinyallerini getirme testi."""
        # Birkaç sinyal logla
        self.logger.log_signal(symbol="BTCUSDT", signal_type="LONG", source="RSI", price=50000.0, strength=75.0)
        self.logger.log_signal(symbol="ETHUSDT", signal_type="SHORT", source="MA", price=3000.0, strength=65.0)
        
        # Bugünün sinyallerini al
        signals = self.logger.get_today_signals()
        
        # Doğru sayıda sinyal dönüyor mu?
        self.assertEqual(len(signals), 2)
        
        # İçerik doğru mu?
        signal_symbols = [signal["symbol"] for signal in signals]
        self.assertIn("BTCUSDT", signal_symbols)
        self.assertIn("ETHUSDT", signal_symbols)
    
    def test_get_today_errors(self):
        """Bugünün hatalarını getirme testi."""
        # Birkaç hata logla
        self.logger.log_error(error_message="Error 1", symbol="BTCUSDT", operation="op1")
        self.logger.log_error(error_message="Error 2", symbol="ETHUSDT", operation="op2")
        
        # Bugünün hatalarını al
        errors = self.logger.get_today_errors()
        
        # Doğru sayıda hata dönüyor mu?
        self.assertEqual(len(errors), 2)
        
        # İçerik doğru mu?
        error_msgs = [error["error_message"] for error in errors]
        self.assertIn("Error 1", error_msgs)
        self.assertIn("Error 2", error_msgs)
    
    def test_singleton_logger(self):
        """Singleton logger testi."""
        # İki kez singleton logger al
        logger1 = get_trade_logger()
        logger2 = get_trade_logger()
        
        # Aynı nesne olmalılar
        self.assertIs(logger1, logger2)
        
        # Farklı bir logger oluştur
        custom_logger = TradeLogger(log_dir=self.temp_dir)
        
        # Singleton logger ile aynı olmamalı
        self.assertIsNot(custom_logger, logger1)


if __name__ == "__main__":
    unittest.main() 