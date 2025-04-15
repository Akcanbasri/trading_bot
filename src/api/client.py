"""
Binance API için client wrapper.
"""
from typing import Dict, List, Optional, Any, Union
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta


class BinanceClient:
    """Binance API istemcisi wrapper sınıfı."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Binance API istemcisi başlatma.
        
        Args:
            api_key: Binance API anahtarı
            api_secret: Binance API gizli anahtarı
            testnet: Testnet modunu kullan (varsayılan: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Binance client'ı başlat
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )
        
        logger.info(f"Binance client başlatıldı. Testnet: {testnet}")
        
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Borsa bilgisini alır.
        
        Returns:
            Dict: Borsa bilgisi
        """
        try:
            return self.client.get_exchange_info()
        except BinanceAPIException as e:
            logger.error(f"Borsa bilgisi alınamadı: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Sembol bilgisini alır.
        
        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            
        Returns:
            Dict: Sembol bilgisi
        """
        try:
            return self.client.get_symbol_info(symbol)
        except BinanceAPIException as e:
            logger.error(f"{symbol} sembol bilgisi alınamadı: {e}")
            raise
    
    def get_historical_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Geçmiş kline/candlestick verilerini alır.
        
        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            interval: Zaman aralığı (örn. "1d", "4h", "1h", "15m", "5m", "1m")
            start_str: Başlangıç zamanı (örn. "1 Jan, 2020")
            end_str: Bitiş zamanı (örn. "1 Jan, 2021")
            limit: Sonuç sayısı limiti
            
        Returns:
            List: Kline verileri listesi
        """
        try:
            return self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str,
                limit=limit
            )
        except BinanceAPIException as e:
            logger.error(f"{symbol} için kline verileri alınamadı: {e}")
            raise
    
    def get_account(self) -> Dict[str, Any]:
        """
        Hesap bilgilerini alır.
        
        Returns:
            Dict: Hesap bilgileri
        """
        try:
            return self.client.get_account()
        except BinanceAPIException as e:
            logger.error(f"Hesap bilgisi alınamadı: {e}")
            raise
    
    def get_asset_balance(self, asset: str) -> Dict[str, str]:
        """
        Belirli bir varlık için bakiye bilgisini alır.
        
        Args:
            asset: Varlık sembolü (örn. "BTC", "USDT")
            
        Returns:
            Dict: Varlık bakiye bilgisi
        """
        try:
            return self.client.get_asset_balance(asset=asset)
        except BinanceAPIException as e:
            logger.error(f"{asset} için bakiye bilgisi alınamadı: {e}")
            raise
    
    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        time_in_force: Optional[str] = "GTC",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Alım/satım emri oluşturur.
        
        Args:
            symbol: İşlem sembolü (örn. "BTCUSDT")
            side: İşlem yönü ("BUY" or "SELL")
            type: Emir tipi ("LIMIT", "MARKET", etc.)
            quantity: İşlem miktarı
            price: İşlem fiyatı (LIMIT emirleri için)
            time_in_force: Emir geçerlilik süresi (GTC, IOC, FOK)
            **kwargs: Diğer parametreler
            
        Returns:
            Dict: Oluşturulan emir bilgisi
        """
        try:
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": type,
                **kwargs
            }
            
            if quantity is not None:
                order_params["quantity"] = quantity
                
            if price is not None and type != "MARKET":
                order_params["price"] = price
                
            if type == "LIMIT":
                order_params["timeInForce"] = time_in_force
            
            return self.client.create_order(**order_params)
        except BinanceAPIException as e:
            logger.error(f"Emir oluşturulamadı: {e}")
            raise
            
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Açık emirleri alır.
        
        Args:
            symbol: İşlem sembolü (opsiyonel)
            
        Returns:
            List: Açık emirler listesi
        """
        try:
            return self.client.get_open_orders(symbol=symbol)
        except BinanceAPIException as e:
            logger.error(f"Açık emirler alınamadı: {e}")
            raise
            
    def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bir emri iptal eder.
        
        Args:
            symbol: İşlem sembolü
            order_id: Emir ID'si (opsiyonel)
            orig_client_order_id: Orijinal client emir ID'si (opsiyonel)
            
        Returns:
            Dict: İptal edilen emir bilgisi
        """
        try:
            return self.client.cancel_order(
                symbol=symbol,
                orderId=order_id,
                origClientOrderId=orig_client_order_id
            )
        except BinanceAPIException as e:
            logger.error(f"Emir iptal edilemedi: {e}")
            raise
    
    def get_futures_account_balance(self) -> Dict[str, float]:
        """
        Futures hesap bakiyesini alır.
        
        Returns:
            Dict[str, float]: Bakiye bilgileri
        """
        try:
            account = self.client.futures_account_balance()
            total_balance = float(account[0]['balance'])
            available_balance = float(account[0]['withdrawAvailable'])
            
            return {
                'total': total_balance,
                'available': available_balance
            }
        except BinanceAPIException as e:
            logger.error(f"Futures bakiye bilgisi alınamadı: {e}")
            raise
            
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Kaldıraç oranını ayarlar.
        
        Args:
            symbol: İşlem sembolü
            leverage: Kaldıraç oranı
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"{symbol} için kaldıraç {leverage}x olarak ayarlandı")
            return True
        except BinanceAPIException as e:
            logger.error(f"Kaldıraç ayarlanamadı: {e}")
            return False
            
    def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """
        Marj tipini ayarlar (ISOLATED veya CROSSED).
        
        Args:
            symbol: İşlem sembolü
            margin_type: Marj tipi ('ISOLATED' veya 'CROSSED')
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
            logger.info(f"{symbol} için marj tipi {margin_type} olarak ayarlandı")
            return True
        except BinanceAPIException as e:
            logger.error(f"Marj tipi ayarlanamadı: {e}")
            return False
            
    def open_futures_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Futures pozisyonu açar.
        
        Args:
            symbol: İşlem sembolü
            side: İşlem yönü ('BUY' veya 'SELL')
            quantity: İşlem miktarı
            leverage: Kaldıraç oranı
            stop_loss: Stop-loss fiyatı
            take_profit: Take-profit fiyatı
            
        Returns:
            Dict[str, Any]: İşlem bilgileri
        """
        try:
            # Kaldıracı ayarla
            self.set_leverage(symbol, leverage)
            
            # Ana emri gönder
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            # Stop-loss emri
            if stop_loss:
                sl_side = 'SELL' if side == 'BUY' else 'BUY'
                self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type='STOP_MARKET',
                    stopPrice=stop_loss,
                    closePosition=True
                )
                
            # Take-profit emri
            if take_profit:
                tp_side = 'SELL' if side == 'BUY' else 'BUY'
                self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=take_profit,
                    closePosition=True
                )
                
            logger.info(f"Futures pozisyonu açıldı: {symbol} {side} {quantity}@{leverage}x")
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Futures pozisyonu açılamadı: {e}")
            raise
            
    def close_futures_position(self, symbol: str) -> bool:
        """
        Futures pozisyonunu kapatır.
        
        Args:
            symbol: İşlem sembolü
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            position = self.client.futures_position_information(symbol=symbol)[0]
            if float(position['positionAmt']) != 0:
                side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
                quantity = abs(float(position['positionAmt']))
                
                self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity,
                    reduceOnly=True
                )
                
                logger.info(f"Futures pozisyonu kapatıldı: {symbol}")
                return True
            return False
            
        except BinanceAPIException as e:
            logger.error(f"Futures pozisyonu kapatılamadı: {e}")
            return False
            
    def get_futures_position(self, symbol: str) -> Dict[str, Any]:
        """
        Futures pozisyon bilgilerini alır.
        
        Args:
            symbol: İşlem sembolü
            
        Returns:
            Dict[str, Any]: Pozisyon bilgileri
        """
        try:
            position = self.client.futures_position_information(symbol=symbol)[0]
            return {
                'symbol': position['symbol'],
                'position_amt': float(position['positionAmt']),
                'entry_price': float(position['entryPrice']),
                'unrealized_pnl': float(position['unRealizedProfit']),
                'leverage': int(position['leverage']),
                'margin_type': position['marginType']
            }
        except BinanceAPIException as e:
            logger.error(f"Futures pozisyon bilgisi alınamadı: {e}")
            raise
            
    def get_futures_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Futures kline verilerini alır.
        
        Args:
            symbol: İşlem sembolü
            interval: Zaman aralığı
            limit: Veri sayısı
            start_time: Başlangıç zamanı
            end_time: Bitiş zamanı
            
        Returns:
            pd.DataFrame: Kline verileri
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_time,
                endTime=end_time
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Futures kline verileri alınamadı: {e}")
            raise 