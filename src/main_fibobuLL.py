"""
FiboBULL PA strateji ana modülü.

Bu modül, trading bot içinde FiboBULL PA stratejisini çalıştırmak için 
ana giriş noktası sağlar.
"""
import argparse
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from loguru import logger
import json

from src.strategies.fibobuLL_strategy import FiboBULLStrategy
from src.indicators.test_fibobuLL_pa import generate_sample_data
from src.test_fibobuLL_strategy import (
    get_historical_data,
    plot_strategy_results,
    print_backtest_summary
)


def setup_logger(log_file=None):
    """
    Logger yapılandırması.
    
    Args:
        log_file: Log dosyası (varsayılan: None)
    """
    if log_file:
        logger.configure(
            handlers=[
                {"sink": sys.stdout, "level": "INFO"},
                {"sink": log_file, "level": "DEBUG", "rotation": "10 MB"}
            ]
        )
    else:
        logger.configure(
            handlers=[
                {"sink": sys.stdout, "level": "INFO"}
            ]
        )


def load_config(config_file):
    """
    Yapılandırma dosyasını yükler.
    
    Args:
        config_file: Yapılandırma dosyası yolu
        
    Returns:
        dict: Yapılandırma ayarları
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Yapılandırma dosyası yüklendi: {config_file}")
        return config
    except Exception as e:
        logger.error(f"Yapılandırma dosyası yüklenirken hata: {e}")
        return {}


def save_results(results, output_file):
    """
    Strateji sonuçlarını dosyaya kaydeder.
    
    Args:
        results: Strateji sonuçları
        output_file: Çıktı dosyası yolu
    """
    try:
        # Sonuçları JSON'a çevrilebilir hale getir
        signals = []
        for signal in results.get('signals', []):
            signal_dict = {k: v for k, v in signal.items()}
            # Datetime nesnelerini string'e çevir
            if 'date' in signal_dict and isinstance(signal_dict['date'], (datetime, pd.Timestamp)):
                signal_dict['date'] = signal_dict['date'].isoformat()
            signals.append(signal_dict)
            
        output = {
            'success': results.get('success', False),
            'summary': results.get('summary', {}),
            'signals': signals
        }
        
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
            
        logger.info(f"Sonuçlar kaydedildi: {output_file}")
    except Exception as e:
        logger.error(f"Sonuçlar kaydedilirken hata: {e}")


def run_backtest(config):
    """
    Backtest çalıştırır.
    
    Args:
        config: Yapılandırma ayarları
        
    Returns:
        dict: Backtest sonuçları
    """
    # Veri kaynağı kontrolü
    data_source = config.get('data_source', 'sample')
    
    if data_source == 'sample':
        # Örnek veri oluştur
        periods = config.get('sample_periods', 500)
        df = generate_sample_data(periods=periods)
        logger.info(f"Örnek veri oluşturuldu: {len(df)} satır")
    elif data_source == 'csv':
        # CSV dosyasından veri yükle
        csv_file = config.get('csv_file')
        if not csv_file or not os.path.exists(csv_file):
            logger.error(f"CSV dosyası bulunamadı: {csv_file}")
            return {'success': False, 'reason': 'CSV dosyası bulunamadı'}
            
        try:
            df = pd.read_csv(csv_file, parse_dates=True, index_col=0)
            # Sütun isimlerini kontrol et ve düzelt
            columns = {c.lower(): c for c in df.columns}
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.error(f"CSV dosyasında eksik sütunlar: {missing_columns}")
                return {'success': False, 'reason': f"Eksik sütunlar: {missing_columns}"}
                
            # Sütun isimlerini küçük harfe çevir
            df.columns = [c.lower() for c in df.columns]
            logger.info(f"CSV dosyasından veri yüklendi: {len(df)} satır")
        except Exception as e:
            logger.error(f"CSV dosyası yüklenirken hata: {e}")
            return {'success': False, 'reason': f"CSV dosyası yüklenirken hata: {e}"}
    elif data_source == 'yahoo':
        # Yahoo Finance'dan veri çek
        symbol = config.get('symbol', 'EURUSD=X')
        period = config.get('period', '1y')
        interval = config.get('interval', '1d')
        
        df = get_historical_data(symbol, period, interval)
        
        if df.empty:
            logger.error(f"Yahoo Finance'dan veri çekilemedi: {symbol}")
            return {'success': False, 'reason': f"Veri çekilemedi: {symbol}"}
            
        logger.info(f"Yahoo Finance'dan veri çekildi: {len(df)} satır")
    else:
        logger.error(f"Geçersiz veri kaynağı: {data_source}")
        return {'success': False, 'reason': f"Geçersiz veri kaynağı: {data_source}"}
    
    # Veri ön işleme
    if df.empty:
        logger.error("Veri yok, işlem durduruluyor")
        return {'success': False, 'reason': 'Veri yok'}
    
    # Strateji parametreleri
    left_bars = config.get('left_bars', 8)
    right_bars = config.get('right_bars', 8)
    stop_loss_percent = config.get('stop_loss_percent', 3.0)
    take_profit_percent = config.get('take_profit_percent', 6.0)
    use_confirmations = config.get('use_confirmations', True)
    
    # Stratejiyi oluştur
    strategy = FiboBULLStrategy(
        left_bars=left_bars,
        right_bars=right_bars,
        stop_loss_percent=stop_loss_percent,
        take_profit_percent=take_profit_percent,
        use_confirmations=use_confirmations
    )
    
    # Backtest yap
    results = strategy.backtest(df)
    
    # Görselleştirme yapılacak mı?
    if config.get('visualize', True):
        title = config.get('title', "FiboBULL Strateji")
        plot_strategy_results(df, results, title)
    
    # Özet yazdırılacak mı?
    if config.get('print_summary', True):
        print_backtest_summary(results)
    
    return results


def main():
    """
    Ana giriş noktası.
    """
    # Komut satırı argümanları
    parser = argparse.ArgumentParser(description='FiboBULL PA Strateji Çalıştırıcı')
    parser.add_argument('--config', type=str, default='config/fibobuLL_config.json',
                        help='Yapılandırma dosyası yolu')
    parser.add_argument('--output', type=str, default='results/fibobuLL_results.json',
                        help='Sonuç dosyası yolu')
    parser.add_argument('--log', type=str, default='logs/fibobuLL.log',
                        help='Log dosyası yolu')
    
    args = parser.parse_args()
    
    # Log klasörü oluştur
    os.makedirs('logs', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    # Logger ayarla
    setup_logger(args.log)
    
    logger.info("FiboBULL PA Strateji Çalıştırıcı başlatılıyor...")
    
    # Örnek yapılandırma dosyası oluştur (yoksa)
    if not os.path.exists(args.config):
        default_config = {
            "data_source": "sample",  # sample, csv, yahoo
            "sample_periods": 500,
            "csv_file": "data/sample.csv",
            "symbol": "EURUSD=X",
            "period": "1y",
            "interval": "1d",
            "left_bars": 8,
            "right_bars": 8, 
            "stop_loss_percent": 3.0,
            "take_profit_percent": 6.0,
            "use_confirmations": True,
            "visualize": True,
            "print_summary": True,
            "title": "FiboBULL Strateji"
        }
        
        with open(args.config, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        logger.info(f"Örnek yapılandırma dosyası oluşturuldu: {args.config}")
    
    # Yapılandırma dosyasını yükle
    config = load_config(args.config)
    
    # Backtest çalıştır
    results = run_backtest(config)
    
    # Sonuçları kaydet
    save_results(results, args.output)
    
    logger.info("FiboBULL PA Strateji Çalıştırıcı tamamlandı.")


if __name__ == "__main__":
    main() 