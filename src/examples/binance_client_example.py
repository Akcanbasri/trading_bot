"""
Binance API client kullanım örneği.

Bu örnek, BinanceClient sınıfının nasıl kullanılacağını
ve API üzerinden temel işlemleri nasıl gerçekleştireceğini gösterir.
"""
import os
import sys
import time
from decimal import Decimal
from loguru import logger
from dotenv import load_dotenv

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.binance_client import BinanceClient


def format_price(price: float, precision: int = 8) -> str:
    """
    Fiyatı uygun formatla gösterir.
    
    Args:
        price: Formatlanacak fiyat
        precision: Ondalık hassasiyet
        
    Returns:
        str: Formatlanmış fiyat
    """
    return f"{price:.{precision}f}"


def display_balances(client: BinanceClient):
    """
    Hesaptaki varlık bakiyelerini gösterir.
    
    Args:
        client: BinanceClient nesnesi
    """
    balances = client.get_balances()
    
    logger.info(f"Toplam {len(balances)} farklı varlık bulundu")
    logger.info("-" * 50)
    
    for balance in balances:
        asset = balance['asset']
        free = balance['free']
        locked = balance['locked']
        total = balance['total']
        
        logger.info(f"Varlık: {asset}")
        logger.info(f"  Kullanılabilir: {format_price(free)}")
        logger.info(f"  Blokeli      : {format_price(locked)}")
        logger.info(f"  Toplam       : {format_price(total)}")
        logger.info("-" * 50)


def get_btc_price(client: BinanceClient) -> float:
    """
    Güncel BTC fiyatını alır.
    
    Args:
        client: BinanceClient nesnesi
        
    Returns:
        float: Güncel BTC fiyatı
    """
    # Güncel fiyat bilgisini al
    ticker = client._public_request("GET", "/api/v3/ticker/price", {"symbol": "BTCUSDT"})
    price = float(ticker['price'])
    logger.info(f"Güncel BTC Fiyatı: ${format_price(price, 2)}")
    return price


def place_limit_orders(client: BinanceClient, symbol: str):
    """
    Belirli bir sembol için alış ve satış limit emirleri oluşturur.
    
    Args:
        client: BinanceClient nesnesi
        symbol: İşlem yapılacak sembol (örn. BTCUSDT)
    """
    # Sembol bilgilerini al
    symbol_info = client.get_symbol_info(symbol)
    
    if not symbol_info:
        logger.error(f"{symbol} için bilgi bulunamadı")
        return
    
    # Filtrelerden fiyat hassasiyetini al
    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
    lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
    
    if not price_filter or not lot_size_filter:
        logger.error("Fiyat veya miktar filtresi bulunamadı")
        return
    
    # Fiyat ve miktar hassasiyetini belirle
    tick_size = float(price_filter['tickSize'])
    step_size = float(lot_size_filter['stepSize'])
    
    # Ondalık basamak sayısını hesapla
    price_precision = len(str(tick_size).split('.')[-1].rstrip('0'))
    quantity_precision = len(str(step_size).split('.')[-1].rstrip('0'))
    
    logger.info(f"Fiyat hassasiyeti: {price_precision}, Miktar hassasiyeti: {quantity_precision}")
    
    # Güncel fiyatı al
    current_price = get_btc_price(client)
    
    # Test alış emri - mevcut fiyatın %5 altında
    buy_price = current_price * 0.95
    buy_price = round(buy_price, price_precision)
    
    # Test satış emri - mevcut fiyatın %5 üstünde
    sell_price = current_price * 1.05
    sell_price = round(sell_price, price_precision)
    
    # Minimum satın alma miktarı
    min_qty = float(lot_size_filter['minQty'])
    min_notional = 10  # Minimum 10 USDT değerinde işlem
    
    # İşlem miktarını hesapla ($10 değerinde BTC, en az minimum miktar kadar)
    quantity = max(min_qty, min_notional / current_price)
    quantity = round(quantity, quantity_precision)
    
    logger.info(f"İşlem yapılacak miktar: {quantity} BTC (yaklaşık ${quantity * current_price:.2f})")
    
    try:
        # Alış emri oluştur
        logger.info(f"Alış limit emri oluşturuluyor: {quantity} BTC @ ${buy_price}")
        buy_order = client.create_limit_order(
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            price=buy_price
        )
        logger.info(f"Alış emri oluşturuldu. Emir ID: {buy_order['orderId']}")
        
        # Satış emri oluştur
        logger.info(f"Satış limit emri oluşturuluyor: {quantity} BTC @ ${sell_price}")
        sell_order = client.create_limit_order(
            symbol=symbol,
            side="SELL",
            quantity=quantity,
            price=sell_price
        )
        logger.info(f"Satış emri oluşturuldu. Emir ID: {sell_order['orderId']}")
        
        # Açık emirleri göster
        open_orders = client.get_open_orders(symbol)
        logger.info(f"{symbol} için {len(open_orders)} açık emir var:")
        
        for order in open_orders:
            order_id = order['orderId']
            side = order['side']
            price = float(order['price'])
            qty = float(order['origQty'])
            status = order['status']
            
            logger.info(f"  Emir ID: {order_id}, Yön: {side}, Fiyat: ${price}, Miktar: {qty}, Durum: {status}")
        
        # İptal edilecek emirleri seç
        if len(open_orders) > 0:
            logger.info("Emirler 3 saniye sonra iptal edilecek...")
            time.sleep(3)
            
            # Tüm açık emirleri iptal et
            cancelled = client.cancel_all_orders(symbol)
            logger.info(f"{len(cancelled)} emir iptal edildi")
    
    except Exception as e:
        logger.error(f"Emir işlemi sırasında hata: {e}")


def place_order_with_sl_tp(client: BinanceClient, symbol: str):
    """
    Stop loss ve take profit içeren bir emir oluşturur.
    
    Args:
        client: BinanceClient nesnesi
        symbol: İşlem yapılacak sembol (örn. BTCUSDT)
    """
    # Güncel fiyatı al
    current_price = get_btc_price(client)
    
    # Sembol bilgilerini al
    symbol_info = client.get_symbol_info(symbol)
    
    if not symbol_info:
        logger.error(f"{symbol} için bilgi bulunamadı")
        return
    
    # Filtrelerden fiyat hassasiyetini al
    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
    lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
    
    # Fiyat ve miktar hassasiyetini belirle
    tick_size = float(price_filter['tickSize'])
    step_size = float(lot_size_filter['stepSize'])
    
    # Ondalık basamak sayısını hesapla
    price_precision = len(str(tick_size).split('.')[-1].rstrip('0'))
    quantity_precision = len(str(step_size).split('.')[-1].rstrip('0'))
    
    # Minimum satın alma miktarı
    min_qty = float(lot_size_filter['minQty'])
    min_notional = 10  # Minimum 10 USDT değerinde işlem
    
    # İşlem miktarını hesapla ($10 değerinde BTC, en az minimum miktar kadar)
    quantity = max(min_qty, min_notional / current_price)
    quantity = round(quantity, quantity_precision)
    
    # Market emri fiyatları (anlık fiyat çevresinde)
    market_price = current_price
    stop_loss = round(market_price * 0.97, price_precision)  # Fiyatın %3 altı
    take_profit = round(market_price * 1.03, price_precision)  # Fiyatın %3 üstü
    
    logger.info(f"İşlem yapılacak miktar: {quantity} BTC (yaklaşık ${quantity * current_price:.2f})")
    logger.info(f"Piyasa fiyatı: ${market_price}")
    logger.info(f"Stop Loss: ${stop_loss} (-%3)")
    logger.info(f"Take Profit: ${take_profit} (+%3)")
    
    try:
        # SL/TP ile market emri oluştur
        logger.info("SL/TP ile market emri oluşturuluyor...")
        
        order_result = client.create_order_with_sl_tp(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Ana emir bilgisi
        main_order = order_result['main_order']
        sl_order = order_result['stop_loss_order']
        tp_order = order_result['take_profit_order']
        
        logger.info(f"Ana emir oluşturuldu. Emir ID: {main_order['orderId']}, Durum: {main_order['status']}")
        
        if sl_order:
            logger.info(f"Stop Loss emri oluşturuldu. Emir ID: {sl_order['orderId']}")
        
        if tp_order:
            logger.info(f"Take Profit emri oluşturuldu. Emir ID: {tp_order['orderId']}")
        
        # Açık emirleri göster
        open_orders = client.get_open_orders(symbol)
        logger.info(f"{symbol} için {len(open_orders)} açık emir var:")
        
        for order in open_orders:
            order_id = order['orderId']
            side = order['side']
            order_type = order['type']
            stop_price = order.get('stopPrice', 'N/A')
            status = order['status']
            
            logger.info(f"  Emir ID: {order_id}, Yön: {side}, Tip: {order_type}, Stop Fiyatı: {stop_price}, Durum: {status}")
        
        # İptal edilecek emirleri seç
        if len(open_orders) > 0:
            logger.info("Emirler 3 saniye sonra iptal edilecek...")
            time.sleep(3)
            
            # Tüm açık emirleri iptal et
            cancelled = client.cancel_all_orders(symbol)
            logger.info(f"{len(cancelled)} emir iptal edildi")
    
    except Exception as e:
        logger.error(f"SL/TP ile emir işlemi sırasında hata: {e}")


def main():
    """
    BinanceClient demo amaçlı çalıştırır.
    """
    logger.info("Binance API Client örneği başlatılıyor...")
    
    # .env dosyasını yükle
    load_dotenv()
    
    # Testnet mi kullanılacak?
    use_testnet = True
    symbol = "BTCUSDT"
    
    try:
        # BinanceClient oluştur
        client = BinanceClient(testnet=use_testnet)
        
        # 1. Hesap bilgilerini al
        account_info = client.get_account_info()
        logger.info(f"Hesap durumu: {account_info.get('accountType', 'Bilinmiyor')}")
        
        # 2. Bakiyeleri göster
        display_balances(client)
        
        # 3. Güncel BTC fiyatını al
        current_btc_price = get_btc_price(client)
        
        # 4. Limit emirleri oluştur (testnet için)
        if use_testnet:
            logger.info("\n=== Limit Emir Örneği ===")
            place_limit_orders(client, symbol)
            
            # 5. Stop Loss ve Take Profit içeren emir oluştur
            logger.info("\n=== SL/TP ile Emir Örneği ===")
            place_order_with_sl_tp(client, symbol)
        else:
            logger.warning("Gerçek hesapta test emirleri devre dışı bırakıldı")
        
    except Exception as e:
        logger.error(f"Program çalışırken hata oluştu: {e}")


if __name__ == "__main__":
    # Log ayarları
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/binance_client_{time}.log", rotation="500 MB", level="DEBUG")
    
    # Ana fonksiyonu çalıştır
    main() 