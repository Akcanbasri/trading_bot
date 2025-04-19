"""
TradeSignalManager kullanım örneği.

Bu örnek, TradeSignalManager sınıfının iki farklı gösterge (RSI Middle Band ve RSI)
ile nasıl kullanılacağını ve işlem bildirimlerinin nasıl yönetileceğini gösterir.
"""

import os
import sys
import time
from typing import Dict, Any
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import yfinance as yf

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import BinanceClient
from src.indicators.rsi_middle_band import RSIMiddleBand
from src.indicators.rsi import RSI
from src.trading.trade_signal_manager import (
    TradeSignalManager,
    SignalType,
    PositionType,
)


def fetch_data(symbol="BTCUSDT", interval="1d", period="3mo"):
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


def trade_notification_handler(trade_info: Dict[str, Any]):
    """
    İşlem bildirimlerini işler.

    Args:
        trade_info: İşlem bilgileri
    """
    # İşlem türüne göre mesaj oluştur
    if trade_info["type"] == "OPEN":
        message = (
            f"🔔 YENİ İŞLEM AÇILDI!\n"
            f"Sembol: {trade_info['symbol']}\n"
            f"Yön: {trade_info['position']}\n"
            f"Miktar: {trade_info['size']:.6f}\n"
            f"Fiyat: ${trade_info['price']:.2f}\n"
            f"Zaman: {trade_info['time']}"
        )
    else:  # CLOSE
        pnl = trade_info.get("pnl", 0)
        pnl_percentage = trade_info.get("pnl_percentage", 0)

        # Kar/zarar durumuna göre emoji seç
        emoji = "🟢" if pnl > 0 else "🔴"

        message = (
            f"🔔 İŞLEM KAPATILDI! {emoji}\n"
            f"Sembol: {trade_info['symbol']}\n"
            f"Yön: {trade_info['position']}\n"
            f"Miktar: {trade_info['size']:.6f}\n"
            f"Giriş: ${trade_info['entry_price']:.2f}\n"
            f"Çıkış: ${trade_info['exit_price']:.2f}\n"
            f"PNL: {pnl:.2f} USDT ({pnl_percentage:.2f}%)\n"
            f"Zaman: {trade_info['time']}"
        )

    # Gerçek bildirim servisi entegrasyonu burada olabilir
    # Örnek: Telegram, Email, SMS, Discord webhooks vb.
    logger.info(f"BİLDİRİM GÖNDERİLİYOR:\n{message}")

    # Telegram üzerinden bildirim göndermek için örnek kod:
    """
    import requests
    
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram bildirimi gönderildi")
            else:
                logger.error(f"Telegram bildirimi gönderilemedi: {response.text}")
        except Exception as e:
            logger.error(f"Telegram bildirimi gönderilemedi: {e}")
    """


def backtest_with_signal_manager(data: pd.DataFrame, symbol: str = "BTCUSDT"):
    """
    Geçmiş veriler üzerinde gösterge sinyallerini test eder.

    Args:
        data: Fiyat verisi
        symbol: İşlem sembolü
    """
    if data.empty:
        logger.error("Veri yok, backtest yapılamaz")
        return

    # Göstergeleri oluştur
    rsi_indicator = RSI(period=14, overbought=70, oversold=30)
    rsi_middle_band = RSIMiddleBand(
        rsi_period=14,
        positive_momentum=50,
        negative_momentum=45,
        ema_short_period=5,
        ema_long_period=10,
    )

    # Sahte bir Binance istemcisi oluştur (backtest için)
    class MockBinanceClient:
        def __init__(self):
            self.current_price = 0

        def _public_request(self, method, endpoint, params=None):
            if endpoint == "/api/v3/ticker/price":
                return {"price": str(self.current_price)}
            return {}

        def get_asset_balance(self, asset):
            return {"asset": asset, "free": 1000.0, "locked": 0.0, "total": 1000.0}

        def create_market_order(self, symbol, side, quantity):
            return {
                "orderId": "mock_order_id",
                "status": "FILLED",
                "executedQty": quantity,
            }

    mock_client = MockBinanceClient()

    # Göstergeleri bir dictionary içinde topla
    indicators = {"RSI": rsi_indicator, "RSI_Middle_Band": rsi_middle_band}

    # TradeSignalManager oluştur
    signal_manager = TradeSignalManager(
        client=mock_client,
        symbol=symbol,
        indicators=indicators,
        notification_callback=trade_notification_handler,
        min_signal_agreement=1,  # Sadece bir göstergeden gelen sinyal yeterli
    )

    # Sonuçları saklamak için listeler
    dates = []
    prices = []
    signals = []
    positions = []
    equity = [1000.0]  # Başlangıç sermayesi

    # Her mum için işlem simülasyonu yap
    for i in range(1, len(data)):
        # Şu anki mum verilerini al
        current_candle = data.iloc[: i + 1]
        current_price = current_candle["close"].iloc[-1]
        current_date = current_candle.index[-1]

        # Mock client'a şu anki fiyatı ayarla
        mock_client.current_price = current_price

        # Göstergeleri güncelle ve sinyalleri al
        combined_signal = signal_manager.update(current_candle)

        # Sonuçları sakla
        dates.append(current_date)
        prices.append(current_price)
        signals.append(combined_signal.value)
        positions.append(signal_manager.current_position.value)

        # Basit bir equity hesabı
        last_equity = equity[-1]
        if signal_manager.current_position == PositionType.LONG:
            # Long pozisyon varsa fiyat değişimlerini hesaba kat
            if len(prices) > 1:
                price_change_pct = (current_price - prices[-2]) / prices[-2]
                new_equity = last_equity * (1 + price_change_pct)
                equity.append(new_equity)
            else:
                equity.append(last_equity)
        elif signal_manager.current_position == PositionType.SHORT:
            # Short pozisyon varsa fiyat değişimlerini ters yönde hesaba kat
            if len(prices) > 1:
                price_change_pct = (prices[-2] - current_price) / prices[-2]
                new_equity = last_equity * (1 + price_change_pct)
                equity.append(new_equity)
            else:
                equity.append(last_equity)
        else:
            # Pozisyon yoksa equity değişmez
            equity.append(last_equity)

    # Sonuçları görselleştir
    plot_backtest_results(dates, prices, signals, positions, equity, symbol)

    # İşlem geçmişini göster
    trade_history = signal_manager.get_trade_history()
    logger.info(f"Toplam {len(trade_history)} işlem gerçekleşti")

    # Basit performans metrikleri
    if equity:
        total_return_pct = (equity[-1] - equity[0]) / equity[0] * 100
        logger.info(f"Toplam Getiri: %{total_return_pct:.2f}")

        # Kar/zarar işlemlerini hesapla
        profitable_trades = sum(
            1
            for trade in trade_history
            if trade.get("type") == "CLOSE" and trade.get("pnl", 0) > 0
        )
        total_closed_trades = sum(
            1 for trade in trade_history if trade.get("type") == "CLOSE"
        )

        if total_closed_trades > 0:
            win_rate = profitable_trades / total_closed_trades * 100
            logger.info(
                f"Kazanç Oranı: %{win_rate:.2f} ({profitable_trades}/{total_closed_trades})"
            )


def plot_backtest_results(dates, prices, signals, positions, equity, symbol):
    """
    Backtest sonuçlarını görselleştirir.

    Args:
        dates: Tarih listesi
        prices: Fiyat listesi
        signals: Sinyal listesi
        positions: Pozisyon listesi
        equity: Sermaye listesi
        symbol: İşlem sembolü
    """
    plt.figure(figsize=(14, 12))

    # 3 alt figür oluştur
    ax1 = plt.subplot(3, 1, 1)
    ax2 = plt.subplot(3, 1, 2)
    ax3 = plt.subplot(3, 1, 3)

    # Fiyat grafiği
    ax1.plot(dates, prices, label="Fiyat", color="black")
    ax1.set_title(f"{symbol} Fiyat ve İşlemler", fontsize=14)
    ax1.set_ylabel("Fiyat", fontsize=12)

    # İşaretleri ekle
    long_entry_dates = [
        date
        for date, pos, prev_pos in zip(dates, positions, ["NONE"] + positions[:-1])
        if pos == "LONG" and prev_pos != "LONG"
    ]
    long_entry_prices = [
        price
        for price, pos, prev_pos in zip(prices, positions, ["NONE"] + positions[:-1])
        if pos == "LONG" and prev_pos != "LONG"
    ]

    short_entry_dates = [
        date
        for date, pos, prev_pos in zip(dates, positions, ["NONE"] + positions[:-1])
        if pos == "SHORT" and prev_pos != "SHORT"
    ]
    short_entry_prices = [
        price
        for price, pos, prev_pos in zip(prices, positions, ["NONE"] + positions[:-1])
        if pos == "SHORT" and prev_pos != "SHORT"
    ]

    long_exit_dates = [
        date
        for date, pos, prev_pos in zip(dates, positions, ["NONE"] + positions[:-1])
        if pos == "NONE" and prev_pos == "LONG"
    ]
    long_exit_prices = [
        price
        for price, pos, prev_pos in zip(prices, positions, ["NONE"] + positions[:-1])
        if pos == "NONE" and prev_pos == "LONG"
    ]

    short_exit_dates = [
        date
        for date, pos, prev_pos in zip(dates, positions, ["NONE"] + positions[:-1])
        if pos == "NONE" and prev_pos == "SHORT"
    ]
    short_exit_prices = [
        price
        for price, pos, prev_pos in zip(prices, positions, ["NONE"] + positions[:-1])
        if pos == "NONE" and prev_pos == "SHORT"
    ]

    # Long ve Short işlem noktalarını işaretle
    ax1.scatter(
        long_entry_dates,
        long_entry_prices,
        marker="^",
        color="green",
        s=100,
        label="Long Giriş",
    )
    ax1.scatter(
        short_entry_dates,
        short_entry_prices,
        marker="v",
        color="red",
        s=100,
        label="Short Giriş",
    )
    ax1.scatter(
        long_exit_dates,
        long_exit_prices,
        marker="o",
        color="blue",
        s=80,
        label="Long Çıkış",
    )
    ax1.scatter(
        short_exit_dates,
        short_exit_prices,
        marker="o",
        color="orange",
        s=80,
        label="Short Çıkış",
    )

    # Pozisyon bölgelerini renklendir
    for i in range(1, len(dates)):
        if positions[i] == "LONG":
            ax1.axvspan(dates[i - 1], dates[i], alpha=0.2, color="green")
        elif positions[i] == "SHORT":
            ax1.axvspan(dates[i - 1], dates[i], alpha=0.2, color="red")

    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Sinyaller grafiği
    signal_values = [
        (
            1
            if s == "LONG"
            else (
                -1
                if s == "SHORT"
                else (
                    0
                    if s == "NEUTRAL"
                    else 0.5 if s == "CLOSE_LONG" else -0.5 if s == "CLOSE_SHORT" else 0
                )
            )
        )
        for s in signals
    ]

    ax2.plot(dates, signal_values, label="Sinyal", color="purple", linewidth=1.5)
    ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)
    ax2.axhline(y=1, color="green", linestyle="--", alpha=0.5)
    ax2.axhline(y=-1, color="red", linestyle="--", alpha=0.5)
    ax2.set_title("Kombine Sinyaller", fontsize=14)
    ax2.set_ylabel("Sinyal", fontsize=12)
    ax2.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax2.set_yticklabels(["SHORT", "CLOSE_SHORT", "NEUTRAL", "CLOSE_LONG", "LONG"])
    ax2.grid(True, alpha=0.3)

    # Sermaye grafiği
    ax3.plot(dates, equity[1:], label="Sermaye", color="blue")
    ax3.set_title("Sermaye Eğrisi", fontsize=14)
    ax3.set_ylabel("Sermaye", fontsize=12)
    ax3.set_xlabel("Tarih", fontsize=12)
    ax3.grid(True, alpha=0.3)

    # Başlangıç sermayesini göstermek için yatay çizgi
    ax3.axhline(
        y=equity[0],
        color="gray",
        linestyle="--",
        alpha=0.5,
        label="Başlangıç Sermayesi",
    )
    ax3.legend()

    # Grafiği sıkıştır ve kaydet
    plt.tight_layout()
    plt.savefig("backtest_results.png", dpi=300)
    plt.show()


def main():
    """
    TradeSignalManager demo amaçlı çalıştırır.
    """
    logger.info("TradeSignalManager örneği başlatılıyor...")

    # .env dosyasını yükle
    load_dotenv()

    # Veri çek
    symbol = "BTC-USD"  # Yahoo Finance için sembol
    binance_symbol = "BTCUSDT"  # Binance için sembol

    # Geçmiş verileri çek (Son 6 ay, günlük mumlar)
    data = fetch_data(symbol=symbol, interval="1d", period="6mo")

    if data.empty:
        logger.error("Veri çekilemedi, program sonlandırılıyor")
        return

    # Backtest yap
    backtest_with_signal_manager(data, binance_symbol)


if __name__ == "__main__":
    # Log ayarları
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/trade_signal_manager_{time}.log", rotation="500 MB", level="DEBUG")

    # Ana fonksiyonu çalıştır
    main()
