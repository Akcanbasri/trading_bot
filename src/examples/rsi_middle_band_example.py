"""
RSI Middle Band göstergesi kullanım örneği.

Bu örnek, RSI Middle Band göstergesinin nasıl kullanılacağını 
ve alım/satım sinyallerinin nasıl izleneceğini gösterir.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
import yfinance as yf

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.rsi_middle_band import RSIMiddleBand


def fetch_data(symbol='BTCUSDT', interval='1d', period='3mo'):
    """
    Yahoo Finance'den fiyat verisi çeker.
    
    Args:
        symbol: Sembol (varsayılan: BTCUSDT)
        interval: Veri aralığı (varsayılan: günlük)
        period: Veri dönemi (varsayılan: 3 ay)
    
    Returns:
        pd.DataFrame: OHLCV verisi
    """
    logger.info(f"{symbol} için {interval} veri çekiliyor, dönem: {period}")
    try:
        data = yf.download(symbol, interval=interval, period=period)
        data.columns = [col.lower() for col in data.columns]
        
        # Eksik değerleri temizle
        data = data.dropna()
        
        logger.info(f"{len(data)} veri noktası çekildi")
        return data
    except Exception as e:
        logger.error(f"Veri çekilirken hata oluştu: {e}")
        return pd.DataFrame()


def main():
    """
    RSI Middle Band göstergesini demo amaçlı çalıştırır.
    """
    # Veri çek
    df = fetch_data(symbol='BTC-USD', interval='1d', period='6mo')
    
    if df.empty:
        logger.error("Veri çekilemedi, program sonlandırılıyor")
        return
    
    # Parametre konfigürasyonu
    params = {
        'rsi_period': 14,           # RSI hesaplama periyodu
        'positive_momentum': 50,    # Pozitif momentum için RSI eşik değeri
        'negative_momentum': 45,    # Negatif momentum için RSI eşik değeri
        'ema_short_period': 5,      # Kısa EMA periyodu
        'ema_long_period': 10       # Uzun EMA periyodu
    }
    
    # RSI Middle Band göstergesini oluştur
    indicator = RSIMiddleBand(**params)
    
    # Göstergeyi hesapla
    result = indicator.update(df)
    
    if result.empty:
        logger.error("Gösterge hesaplanamadı, program sonlandırılıyor")
        return
    
    # Son sinyalleri kontrol et
    signal_info = indicator.get_signal()
    logger.info(f"Son sinyal: {signal_info['signal']}, Güç: {signal_info['strength']:.2f}, RSI: {signal_info['value']:.2f}")
    
    # Aktif alım sinyali varsa
    if indicator.is_buy_signal():
        logger.info("✅ ALIM SİNYALİ MEVCUT")
    
    # Aktif satım sinyali varsa
    if indicator.is_sell_signal():
        logger.info("❌ SATIM SİNYALİ MEVCUT")
    
    # Sonuçları görselleştir
    plot_results(df, result, indicator.params)


def plot_results(data, result, params):
    """
    Sonuçları görselleştir
    
    Args:
        data: Fiyat verisi
        result: Gösterge sonuçları
        params: Gösterge parametreleri
    """
    # Matplotlib ayarları
    plt.style.use('fivethirtyeight')
    plt.rcParams['figure.figsize'] = (14, 10)
    
    # İki alt grafik oluştur (2 satır, 1 sütun)
    fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]})
    
    # Fiyat grafiği
    ax1.plot(data.index, data['close'], label='Fiyat', color='black', linewidth=1.5)
    
    # EMA değerleri
    ax1.plot(data.index, result['ema_short'], label=f"EMA ({params['ema_short_period']})", color='blue', linewidth=1, alpha=0.7)
    ax1.plot(data.index, result['ema_high'], label=f"EMA High ({params['ema_short_period']})", color='green', linewidth=1, alpha=0.5)
    ax1.plot(data.index, result['ema_low'], label=f"EMA Low ({params['ema_long_period']})", color='red', linewidth=1, alpha=0.5)
    
    # Alım sinyalleri
    buy_signals = result[result['buy_signal'] & ~result['buy_signal'].shift(1).fillna(False)]
    if not buy_signals.empty:
        ax1.scatter(buy_signals.index, data.loc[buy_signals.index]['close'], 
                   color='green', marker='^', s=120, label='Alım Sinyali')
    
    # Satım sinyalleri
    sell_signals = result[result['sell_signal'] & ~result['sell_signal'].shift(1).fillna(False)]
    if not sell_signals.empty:
        ax1.scatter(sell_signals.index, data.loc[sell_signals.index]['close'], 
                   color='red', marker='v', s=120, label='Satım Sinyali')
    
    # İşlem dönemi vurgulama
    buy_periods = result['buy_signal'].astype(int).diff()
    buy_starts = result.index[buy_periods == 1]
    buy_ends = result.index[buy_periods == -1]
    
    for start, end in zip(buy_starts, buy_ends):
        if start < end:  # Eğer başlangıç sonu geçmiyorsa
            ax1.axvspan(start, end, color='green', alpha=0.15)
    
    # Fiyat grafiği özellikleri
    ax1.set_title('RSI Middle Band - Fiyat Grafiği', fontsize=14)
    ax1.set_ylabel('Fiyat', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # RSI grafiği
    ax2.plot(result.index, result['rsi'], label='RSI', color='purple', linewidth=1.5)
    ax2.axhline(y=params['positive_momentum'], color='green', linestyle='--', alpha=0.7, 
               label=f"Pozitif Momentum ({params['positive_momentum']})")
    ax2.axhline(y=params['negative_momentum'], color='red', linestyle='--', alpha=0.7,
               label=f"Negatif Momentum ({params['negative_momentum']})")
    
    # RSI için alım sinyalleri
    if not buy_signals.empty:
        ax2.scatter(buy_signals.index, result.loc[buy_signals.index]['rsi'], 
                   color='green', marker='^', s=120)
    
    # RSI için satım sinyalleri
    if not sell_signals.empty:
        ax2.scatter(sell_signals.index, result.loc[sell_signals.index]['rsi'], 
                   color='red', marker='v', s=120)
    
    # RSI grafiği özellikleri
    ax2.set_title('RSI', fontsize=14)
    ax2.set_ylabel('RSI Değeri', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Genel grafik ayarları
    plt.tight_layout()
    plt.savefig('rsi_middle_band_results.png', dpi=300)
    plt.show()


if __name__ == "__main__":
    # Log ayarları
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/rsi_middle_band_{time}.log", rotation="500 MB", level="DEBUG")
    
    # Ana fonksiyonu çalıştır
    main() 