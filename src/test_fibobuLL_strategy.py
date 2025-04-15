"""
FiboBULL stratejisini test eden ana modül.

Bu modül, FiboBULL stratejisini oluşturur, örnek veri üzerinde test eder 
ve sonuçları görselleştirir.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from loguru import logger
import yfinance as yf
import os

from src.strategies.fibobuLL_strategy import FiboBULLStrategy
from src.indicators.test_fibobuLL_pa import generate_sample_data


def get_historical_data(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Yahoo Finance'dan tarihsel veri çeker.
    
    Args:
        symbol: Sembol adı (örn. 'EURUSD=X')
        period: Veri periyodu (örn. '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Bar aralığı (örn. '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
    Returns:
        pd.DataFrame: OHLCV verileri
    """
    try:
        # Yahoo Finance'dan veri çek
        data = yf.download(symbol, period=period, interval=interval)
        
        # Sütun isimlerini küçük harfle değiştir
        data.columns = [col.lower() for col in data.columns]
        
        # İndeks tarih formatını kontrol et
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        logger.info(f"{symbol} için {len(data)} satır veri alındı. Periyot: {period}, Aralık: {interval}")
        return data
        
    except Exception as e:
        logger.error(f"Veri çekerken hata oluştu: {e}")
        return pd.DataFrame()


def plot_strategy_results(data: pd.DataFrame, results: dict, title: str = "FiboBULL Strateji Sonuçları"):
    """
    Strateji sonuçlarını görselleştirir.
    
    Args:
        data: Fiyat verileri
        results: Strateji sonuçları
        title: Grafik başlığı
    """
    if 'signals' not in results or not results['signals']:
        logger.warning("Görselleştirilecek sinyal yok")
        return
    
    plt.figure(figsize=(16, 10))
    
    # Fiyat grafiği
    plt.subplot(2, 1, 1)
    plt.plot(data.index, data['close'], label='Kapanış Fiyatı', color='blue', linewidth=1.5)
    
    # Giriş ve çıkış işlemlerini işaretle
    for signal in results['signals']:
        if signal['action'] == 'ENTER' and signal['signal'] == 'BUY':
            plt.plot(signal['date'], signal['price'], '^', markersize=10, color='green', 
                     label='Long Giriş' if 'Long Giriş' not in plt.gca().get_legend_handles_labels()[1] else "")
            
        elif signal['action'] == 'ENTER' and signal['signal'] == 'SELL':
            plt.plot(signal['date'], signal['price'], 'v', markersize=10, color='red', 
                     label='Short Giriş' if 'Short Giriş' not in plt.gca().get_legend_handles_labels()[1] else "")
            
        elif signal['action'] == 'EXIT' and signal['side'] == 'LONG':
            plt.plot(signal['date'], signal['exit_price'], 'x', markersize=10, color='green', 
                     label='Long Çıkış' if 'Long Çıkış' not in plt.gca().get_legend_handles_labels()[1] else "")
            
            # Giriş ve çıkış arasında çizgi çiz
            entry_date = signal['date'] - timedelta(days=1)  # Yaklaşık giriş tarihi
            for entry_signal in results['signals']:
                if entry_signal['action'] == 'ENTER' and entry_signal['signal'] == 'BUY' and entry_signal['date'] < signal['date']:
                    if not any(exit_signal['action'] == 'EXIT' and exit_signal['side'] == 'LONG' and 
                              exit_signal['date'] > entry_signal['date'] and exit_signal['date'] < signal['date'] 
                              for exit_signal in results['signals']):
                        entry_date = entry_signal['date']
                        plt.plot([entry_date, signal['date']], 
                                [entry_signal['price'], signal['exit_price']], 
                                'g--', alpha=0.3)
                        break
            
        elif signal['action'] == 'EXIT' and signal['side'] == 'SHORT':
            plt.plot(signal['date'], signal['exit_price'], 'x', markersize=10, color='red', 
                     label='Short Çıkış' if 'Short Çıkış' not in plt.gca().get_legend_handles_labels()[1] else "")
            
            # Giriş ve çıkış arasında çizgi çiz
            entry_date = signal['date'] - timedelta(days=1)  # Yaklaşık giriş tarihi
            for entry_signal in results['signals']:
                if entry_signal['action'] == 'ENTER' and entry_signal['signal'] == 'SELL' and entry_signal['date'] < signal['date']:
                    if not any(exit_signal['action'] == 'EXIT' and exit_signal['side'] == 'SHORT' and 
                              exit_signal['date'] > entry_signal['date'] and exit_signal['date'] < signal['date'] 
                              for exit_signal in results['signals']):
                        entry_date = entry_signal['date']
                        plt.plot([entry_date, signal['date']], 
                                [entry_signal['price'], signal['exit_price']], 
                                'r--', alpha=0.3)
                        break
    
    plt.title(f"{title} - Fiyat ve İşlemler")
    plt.xlabel('Tarih')
    plt.ylabel('Fiyat')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Equity grafiği
    plt.subplot(2, 1, 2)
    
    equity = 100  # Başlangıç sermayesi
    equity_curve = [equity]
    dates = [data.index[0]]
    
    for signal in sorted(results['signals'], key=lambda x: x['date']):
        if signal['action'] == 'EXIT':
            equity += signal.get('profit_loss', 0)
            equity_curve.append(equity)
            dates.append(signal['date'])
    
    if len(equity_curve) > 1:
        plt.plot(dates, equity_curve, label='Sermaye Eğrisi', color='purple', linewidth=2)
        plt.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
        
        # Drawdown hesapla ve göster
        peak = 100
        drawdown = []
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            drawdown.append(dd)
        
        plt.fill_between(dates, 0, drawdown, alpha=0.3, color='red', label='Drawdown')
    
    plt.title(f"{title} - Sermaye Eğrisi")
    plt.xlabel('Tarih')
    plt.ylabel('Sermaye (%)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    
    # Sonuçlar için klasör oluştur
    os.makedirs('results', exist_ok=True)
    plt.savefig('results/fibobuLL_strategy_backtest.png')
    logger.info("Grafik 'results/fibobuLL_strategy_backtest.png' dosyasına kaydedildi")


def print_backtest_summary(results: dict):
    """
    Backtest sonuçlarını konsola yazdırır.
    
    Args:
        results: Backtest sonuçları
    """
    if not results['success']:
        logger.error(f"Backtest başarısız: {results.get('reason', 'Bilinmeyen hata')}")
        return
    
    summary = results['summary']
    
    print("\n" + "="*50)
    print(" "*15 + "BACKTEST SONUÇLARI")
    print("="*50)
    print(f"Toplam İşlem Sayısı: {summary['total_trades']}")
    print(f"Kazançlı İşlemler: {summary['winning_trades']}")
    print(f"Zararlı İşlemler: {summary['losing_trades']}")
    print(f"Kazanç Oranı: {summary['win_rate']:.2f}%")
    print(f"Kâr Faktörü: {summary['profit_factor']:.2f}")
    print(f"Toplam Getiri: {summary['total_return']:.2f}%")
    print(f"Maksimum Drawdown: {summary['max_drawdown']:.2f}%")
    print("="*50)
    
    # İşlem detayları
    print("\nİşlem Detayları:")
    print("-"*90)
    print(f"{'Tarih':<20} {'İşlem':<10} {'Yön':<8} {'Fiyat':<10} {'Kâr/Zarar':<12} {'Neden':<30}")
    print("-"*90)
    
    for signal in results['signals']:
        if signal['action'] == 'ENTER':
            print(f"{signal['date'].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{'GİRİŞ':<10} "
                  f"{signal['side']:<8} "
                  f"{signal['price']:<10.4f} "
                  f"{'':<12} "
                  f"{signal['reason'][:30]:<30}")
        elif signal['action'] == 'EXIT':
            print(f"{signal['date'].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{'ÇIKIŞ':<10} "
                  f"{signal['side']:<8} "
                  f"{signal['exit_price']:<10.4f} "
                  f"{signal.get('profit_loss', 0):<12.2f}% "
                  f"{signal['reason'][:30]:<30}")
    
    print("-"*90)


def test_with_sample_data():
    """
    Oluşturulan örnek veri ile testi çalıştırır.
    """
    logger.info("Örnek veri ile test başlatılıyor...")
    
    # Örnek veri oluştur
    df = generate_sample_data(periods=500)
    
    # Stratejiyi oluştur
    strategy = FiboBULLStrategy(
        left_bars=8,
        right_bars=8,
        stop_loss_percent=3.0,
        take_profit_percent=6.0
    )
    
    # Backtest yap
    results = strategy.backtest(df)
    
    # Sonuçları yazdır
    print_backtest_summary(results)
    
    # Sonuçları görselleştir
    plot_strategy_results(df, results, "FiboBULL Strateji - Örnek Veri")


def test_with_real_data(symbol: str = "EURUSD=X", period: str = "1y", interval: str = "1d"):
    """
    Gerçek piyasa verisi ile testi çalıştırır.
    
    Args:
        symbol: Test edilecek sembol
        period: Veri periyodu
        interval: Bar aralığı
    """
    logger.info(f"{symbol} için gerçek veri ile test başlatılıyor...")
    
    # Veri çek
    df = get_historical_data(symbol, period, interval)
    
    if df.empty:
        logger.error("Veri çekilemedi, test sonlandırılıyor")
        return
    
    # Stratejiyi oluştur
    strategy = FiboBULLStrategy(
        left_bars=8,
        right_bars=8,
        stop_loss_percent=2.0,
        take_profit_percent=4.0
    )
    
    # Backtest yap
    results = strategy.backtest(df)
    
    # Sonuçları yazdır
    print_backtest_summary(results)
    
    # Sonuçları görselleştir
    plot_strategy_results(df, results, f"FiboBULL Strateji - {symbol}")


if __name__ == "__main__":
    # Log formatını ayarla
    logger.configure(handlers=[{"sink": lambda msg: print(msg)}])
    
    # Örnek veri ile test
    test_with_sample_data()
    
    # Gerçek veri ile test (yorum satırından çıkarılarak kullanılabilir)
    # pip install yfinance gerektirir
    # test_with_real_data(symbol="BTCUSD=X", period="1y", interval="1d") 