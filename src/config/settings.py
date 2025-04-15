"""
Settings module for trading bot.

Bu modül, ticaret botunun yapılandırma ayarlarını yönetir.
Ayarlar .env dosyasından veya config.json dosyasından okunabilir.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dotenv import load_dotenv

# Projenin kök dizinini bul
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# .env dosyasını yükle (varsa)
load_dotenv(ROOT_DIR / ".env")

# Varsayılan yapılandırma değerleri
DEFAULT_CONFIG = {
    # Genel bot ayarları
    "BOT_MODE": "test",  # "live", "test" veya "paper"
    "EXCHANGE": "binance",
    "BASE_CURRENCY": "USDT",
    "LOG_LEVEL": "INFO",
    
    # Log ayarları
    "LOG_CONFIG": {
        "log_dir": "logs",
        "console_output": True,
        "detailed_file_logs": True
    },
    
    # Risk yönetimi ayarları
    "RISK_MANAGEMENT": {
        "max_open_positions": 3,
        "max_position_size_usd": 100.0,
        "max_position_size_percentage": 5.0,  # Toplam bakiyenin yüzdesi
        "max_daily_loss_percentage": 5.0,     # Günlük maksimum kayıp (%)
        "max_total_loss_percentage": 20.0,    # Toplam maksimum kayıp (%)
        "default_stop_loss_percentage": 2.0,  # Varsayılan stop loss (%)
        "default_take_profit_percentage": 4.0,# Varsayılan take profit (%)
        "default_leverage": 1,               # Varsayılan kaldıraç (1x = spot)
        "risk_reward_ratio": 2.0,            # Risk/Ödül oranı
        "enable_trailing_stop": False,        # Trailing stop
        "trailing_stop_activation_percentage": 1.0, # Trailing stop etkinleştirme (%)
        "trailing_stop_callback_percentage": 0.5,   # Trailing stop callback (%)
    },
    
    # Trade stratejisi ayarları
    "STRATEGY": {
        "name": "rsi_strategy",
        "timeframe": "1h",
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        "parameters": {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "ema_fast_period": 9,
            "ema_slow_period": 21
        }
    },
    
    # API ayarları
    "API": {
        "binance": {
            "api_key": "",
            "api_secret": "",
            "testnet": True  # Testnet kullanımı
        },
        "telegram": {
            "bot_token": "",
            "chat_id": ""
        }
    }
}

class Settings:
    """
    Trading botu için yapılandırma ayarlarını yöneten sınıf.
    
    Ayarlar şu kaynaklardan okunabilir (öncelik sırasıyla):
    1. .env dosyası
    2. config.json dosyası
    3. Varsayılan değerler (DEFAULT_CONFIG)
    """
    
    def __init__(self):
        """Settings sınıfını başlatır ve ayarları yükler."""
        self._config = DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self):
        """
        Ayarları yükler. Önce json dosyasını, sonra env değişkenlerini kontrol eder.
        """
        # 1. config.json dosyasından yükle (varsa)
        config_path = ROOT_DIR / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    json_config = json.load(f)
                    self._update_nested_dict(self._config, json_config)
                    logging.info(f"Ayarlar {config_path} dosyasından yüklendi")
            except Exception as e:
                logging.error(f"config.json yüklenirken hata: {e}")
        
        # 2. .env dosyasından değerleri güncelle
        self._load_from_env()
    
    def _load_from_env(self):
        """
        .env dosyasındaki veya sistem ortam değişkenlerindeki değerleri yapılandırmaya uygular.
        """
        # API anahtarları
        if os.getenv("BINANCE_API_KEY"):
            self._config["API"]["binance"]["api_key"] = os.getenv("BINANCE_API_KEY")
        
        if os.getenv("BINANCE_API_SECRET"):
            self._config["API"]["binance"]["api_secret"] = os.getenv("BINANCE_API_SECRET")
        
        if os.getenv("BINANCE_TESTNET"):
            self._config["API"]["binance"]["testnet"] = os.getenv("BINANCE_TESTNET").lower() == "true"
        
        # Telegram Bot
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            self._config["API"]["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if os.getenv("TELEGRAM_CHAT_ID"):
            self._config["API"]["telegram"]["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
        
        # Bot modu
        if os.getenv("BOT_MODE"):
            self._config["BOT_MODE"] = os.getenv("BOT_MODE")
        
        # Risk yönetimi
        if os.getenv("MAX_POSITION_SIZE_USD"):
            self._config["RISK_MANAGEMENT"]["max_position_size_usd"] = float(os.getenv("MAX_POSITION_SIZE_USD"))
        
        if os.getenv("MAX_POSITION_SIZE_PERCENTAGE"):
            self._config["RISK_MANAGEMENT"]["max_position_size_percentage"] = float(os.getenv("MAX_POSITION_SIZE_PERCENTAGE"))
        
        if os.getenv("DEFAULT_STOP_LOSS_PERCENTAGE"):
            self._config["RISK_MANAGEMENT"]["default_stop_loss_percentage"] = float(os.getenv("DEFAULT_STOP_LOSS_PERCENTAGE"))
        
        if os.getenv("DEFAULT_TAKE_PROFIT_PERCENTAGE"):
            self._config["RISK_MANAGEMENT"]["default_take_profit_percentage"] = float(os.getenv("DEFAULT_TAKE_PROFIT_PERCENTAGE"))
        
        if os.getenv("DEFAULT_LEVERAGE"):
            self._config["RISK_MANAGEMENT"]["default_leverage"] = int(os.getenv("DEFAULT_LEVERAGE"))
    
    def _update_nested_dict(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """
        İç içe sözlükleri günceller.
        
        Args:
            d: Hedef sözlük
            u: Yeni değerler içeren sözlük
            
        Returns:
            Dict[str, Any]: Güncellenmiş sözlük
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Yapılandırmadan bir değer getirir.
        
        Args:
            key: Yapılandırma anahtarı (nokta notasyonuyla iç içe anahtarlar belirtilebilir)
            default: Anahtar bulunamazsa dönecek varsayılan değer
            
        Returns:
            Any: Yapılandırma değeri veya varsayılan değer
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default
        
        return config
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        Mevcut yapılandırmayı bir JSON dosyasına kaydeder.
        
        Args:
            config_path: Kaydedilecek dosya yolu (None ise varsayılan config.json kullanılır)
            
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        if config_path is None:
            config_path = ROOT_DIR / "config.json"
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            logging.info(f"Ayarlar {config_path} dosyasına kaydedildi")
            return True
        except Exception as e:
            logging.error(f"Ayarlar kaydedilirken hata: {e}")
            return False
    
    def update(self, key: str, value: Any) -> bool:
        """
        Yapılandırmayı günceller.
        
        Args:
            key: Güncellenecek anahtar (nokta notasyonuyla iç içe anahtarlar belirtilebilir)
            value: Yeni değer
            
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        keys = key.split(".")
        config = self._config
        
        # Son anahtara kadar ilerle
        for i, k in enumerate(keys[:-1]):
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Son anahtarı güncelle
        config[keys[-1]] = value
        return True
    
    def __getattr__(self, name: str) -> Any:
        """
        Özellik erişimi için özel metod (örn: settings.BOT_MODE).
        
        Args:
            name: Özellik adı
            
        Returns:
            Any: Özellik değeri
            
        Raises:
            AttributeError: Özellik bulunamazsa
        """
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"'{self.__class__.__name__}' nesnesi '{name}' özelliğine sahip değil")


# Singleton Settings nesnesi
settings = Settings() 