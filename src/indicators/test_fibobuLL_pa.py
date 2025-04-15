"""
FiboBULL PA göstergesinin test ve demo modülü.

Bu modül, gösterge hesaplamalarını ve sinyallerini test etmek için örnek veriler kullanır.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger

from src.indicators.fibobuLL_pa import FiboBULLPA


def generate_sample_data(periods: int = 200) -> pd.DataFrame:
    """
    Test için örnek veri oluşturur.
    
    Args:
        periods: Veri noktası sayısı
        
    Returns:
        pd.DataFrame: OHLCV verisi
    """
    # Rastgele bir trend oluştur
    np.random.seed(42)  # Tekrarlanabilir sonuçlar için
    
    # Başlangıç fiyatı
    base_price = 100.0
    
    # Rastgele yürüyüş (random walk) ile fiyat oluştur
    changes = np.random.normal(0, 1, periods) * 0.5
    
    # Trend bileşeni ekle
    trend = np.sin(np.linspace(0, 4*np.pi, periods)) * 5  # Sinüs dalgası trend
    
    # Değişimleri topla
    price_changes = changes + trend * 0.1
    
    # Kümülatif toplamla fiyatları oluştur
    closes = base_price + np.cumsum(price_changes)
    
    # Günlük volatilite (yüzde olarak)
    volatility = 1.5
    
    # High, low ve open değerlerini oluştur
    highs = closes + closes * np.random.uniform(0, volatility / 100, periods)
    lows = closes - closes * np.random.uniform(0, volatility / 100, periods)
    opens = lows + (highs - lows) * np.random.random(periods)
    
    # Hacim (volume) değerlerini oluştur
    volumes = np.random.normal(1000000, 200000, periods)
    volumes = np.abs(volumes)  # Negative hacimleri engelle
    
    # Tarih endeksi oluştur
    dates = pd.date_range('2023-01-01', periods=periods)
    
    # DataFrame oluştur
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)
    
    return df


def run_fibobuLL_pa_test():
    """
    FiboBULL PA göstergesini test eder ve sonuçları gösterir.
    """
    # Örnek veri oluştur
    df = generate_sample_data(periods=300)
    logger.info(f"Örnek veri oluşturuldu: {len(df)} satır")
    
    # FiboBULL PA göstergesini oluştur ve hesapla
    fibo_indicator = FiboBULLPA(left_bars=8, right_bars=8)
    result = fibo_indicator.calculate(df)
    
    if result.empty:
        logger.error("FiboBULL PA hesaplaması başarısız oldu.")
        return
    
    logger.info(f"FiboBULL PA hesaplandı: {len(result)} satır")
    
    # Alım/satım sinyallerini logla
    long_signals = result[result['long_signal']].index
    short_signals = result[result['short_signal']].index
    
    logger.info(f"Toplam {len(long_signals)} alım sinyali bulundu")
    logger.info(f"Toplam {len(short_signals)} satım sinyali bulundu")
    
    # Sonuçları görselleştir
    plt.figure(figsize=(14, 8))
    
    # Fiyat grafiği
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Kapanış Fiyatı', color='blue', alpha=0.7)
    
    # Destek ve direnç çizgileri
    if 'support' in result.columns and 'resistance' in result.columns:
        plt.plot(result.index, result['support'], label='Destek', color='green', linestyle='--')
        plt.plot(result.index, result['resistance'], label='Direnç', color='red', linestyle='--')
    
    # Alım sinyallerini işaretle
    for signal_date in long_signals:
        plt.plot(signal_date, df.loc[signal_date, 'close'], '^', markersize=10, color='green', 
                 label='Alım Sinyali' if signal_date == long_signals[0] else "")
    
    # Satım sinyallerini işaretle
    for signal_date in short_signals:
        plt.plot(signal_date, df.loc[signal_date, 'close'], 'v', markersize=10, color='red', 
                 label='Satım Sinyali' if signal_date == short_signals[0] else "")
    
    plt.title('FiboBULL PA Fiyat ve Sinyal Grafiği')
    plt.ylabel('Fiyat')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Trend grafiği
    plt.subplot(2, 1, 2)
    plt.plot(result.index, result['trend'], label='Trend Yönü', color='purple')
    plt.fill_between(result.index, result['trend'], 0, where=(result['trend'] > 0), 
                     facecolor='green', alpha=0.3, interpolate=True)
    plt.fill_between(result.index, result['trend'], 0, where=(result['trend'] < 0), 
                     facecolor='red', alpha=0.3, interpolate=True)
    plt.title('FiboBULL PA Trend Grafiği')
    plt.ylabel('Trend Yönü (1: Yukarı, -1: Aşağı)')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('fibobuLL_pa_test.png')
    logger.info("Grafik 'fibobuLL_pa_test.png' dosyasına kaydedildi")
    
    # Gösterge sonuçları hakkında bilgiler
    signal = fibo_indicator.get_signal()
    support_resistance = fibo_indicator.get_support_resistance()
    
    logger.info(f"Mevcut Sinyal: {signal}")
    logger.info(f"Destek-Direnç: {support_resistance}")
    
    # Mevcut trend bilgisi
    trend = fibo_indicator.get_current_trend()
    trend_text = "Yukarı" if trend == 1 else "Aşağı" if trend == -1 else "Yatay"
    logger.info(f"Mevcut Trend: {trend_text} ({trend})")


if __name__ == "__main__":
    # Log formatını ayarla
    logger.configure(handlers=[{"sink": lambda msg: print(msg)}])
    
    # Testi çalıştır
    run_fibobuLL_pa_test() 