"""
Binance API client module.

Bu modül, Binance API ile güvenli bağlantı kurma ve 
çeşitli işlem fonksiyonlarını içeren BinanceClient sınıfını sağlar.
"""
import os
import time
import hmac
import hashlib
import json
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from loguru import logger

# .env dosyasını yükle
load_dotenv()


class BinanceClient:
    """
    Binance API için güvenli bağlantı sağlayan ve işlem yapan sınıf.
    
    API key ve secret değerlerini .env veya config dosyasından çeker.
    Emir açma, emir kapama, pozisyon kontrolü ve bakiye görüntüleme 
    işlemlerini destekler.
    """
    
    def __init__(
        self, 
        testnet: bool = False,
        config_path: Optional[str] = None
    ):
        """
        BinanceClient sınıfını başlatır.
        
        Args:
            testnet: Testnet kullanılıp kullanılmayacağı (varsayılan: False)
            config_path: Config dosyası yolu (varsayılan: None, .env dosyası kullanılır)
        """
        self.testnet = testnet
        
        # API endpoint'lerini ayarla
        if testnet:
            self.base_url = "https://testnet.binance.vision"
            logger.info("Binance Testnet kullanılıyor")
        else:
            self.base_url = "https://api.binance.com"
            logger.info("Binance Mainnet kullanılıyor")
        
        # API bilgilerini al
        if config_path:
            self._load_config_from_file(config_path)
        else:
            self._load_config_from_env()
        
        # API anahtarlarını kontrol et
        if not self.api_key or not self.api_secret:
            raise ValueError("API key ve secret gerekli")
        
        # Oturum başlat
        self.session = self._init_session()
        
        # Sunucu zamanı farkını hesapla
        self.time_offset = 0
        self._sync_time()
        
        logger.info("Binance API bağlantısı başlatıldı")
    
    def _load_config_from_env(self):
        """
        .env dosyasından API bilgilerini yükler.
        """
        # Testnet veya normal API anahtarları
        if self.testnet:
            self.api_key = os.getenv('BINANCE_TESTNET_API_KEY', '')
            self.api_secret = os.getenv('BINANCE_TESTNET_API_SECRET', '')
        else:
            self.api_key = os.getenv('BINANCE_API_KEY', '')
            self.api_secret = os.getenv('BINANCE_API_SECRET', '')
            
        if not self.api_key or not self.api_secret:
            logger.warning("API bilgileri .env dosyasında bulunamadı")
    
    def _load_config_from_file(self, config_path: str):
        """
        Config dosyasından API bilgilerini yükler.
        
        Args:
            config_path: Config dosyası yolu
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Testnet veya normal API anahtarları
            if self.testnet:
                self.api_key = config.get('binance_testnet_api_key', '')
                self.api_secret = config.get('binance_testnet_api_secret', '')
            else:
                self.api_key = config.get('binance_api_key', '')
                self.api_secret = config.get('binance_api_secret', '')
                
            if not self.api_key or not self.api_secret:
                logger.warning(f"API bilgileri {config_path} dosyasında bulunamadı")
        except Exception as e:
            logger.error(f"Config dosyası yüklenirken hata oluştu: {e}")
            self.api_key = ''
            self.api_secret = ''
    
    def _init_session(self) -> requests.Session:
        """
        API istekleri için session oluşturur.
        
        Returns:
            Session: Requests session nesnesi
        """
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'X-MBX-APIKEY': self.api_key
        })
        return session
    
    def _sync_time(self):
        """
        Yerel saat ile Binance sunucu saati arasındaki farkı hesaplar.
        """
        try:
            server_time = self._public_request("GET", "/api/v3/time")
            local_time = int(time.time() * 1000)
            self.time_offset = server_time['serverTime'] - local_time
            logger.debug(f"Sunucu zamanı farkı: {self.time_offset} ms")
        except Exception as e:
            logger.error(f"Sunucu zamanı alınırken hata oluştu: {e}")
    
    def _get_timestamp(self) -> int:
        """
        Sunucu zamanı farkını dikkate alarak timestamp döndürür.
        
        Returns:
            int: Sunucu zamanı ile senkronize edilmiş timestamp
        """
        return int(time.time() * 1000 + self.time_offset)
    
    def _generate_signature(self, query_string: str) -> str:
        """
        HMAC SHA256 imzası oluşturur.
        
        Args:
            query_string: İmzalanacak sorgu parametreleri
            
        Returns:
            str: HMAC SHA256 imzası
        """
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _public_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        Public API endpoint'ine istek yapar.
        
        Args:
            method: HTTP metodu (GET, POST, vb.)
            endpoint: API endpoint
            params: Sorgu parametreleri
            
        Returns:
            Dict: API yanıtı
        """
        url = self.base_url + endpoint
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Geçersiz HTTP metodu: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API isteği sırasında hata oluştu: {e}")
            raise
    
    def _signed_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        Signed (imzalı) API endpoint'ine istek yapar.
        
        Args:
            method: HTTP metodu (GET, POST, vb.)
            endpoint: API endpoint
            params: Sorgu parametreleri
            
        Returns:
            Dict: API yanıtı
        """
        if params is None:
            params = {}
        
        # Timestamp ekle
        params['timestamp'] = self._get_timestamp()
        
        # Parametreleri sırala ve sorguya dönüştür
        query_string = urlencode(params)
        
        # İmza oluştur ve ekle
        signature = self._generate_signature(query_string)
        query_string += f"&signature={signature}"
        
        # Endpoint URL'i oluştur
        url = f"{self.base_url}{endpoint}?{query_string}"
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Geçersiz HTTP metodu: {method}")
            
            # Yanıt kodunu kontrol et
            if response.status_code != 200:
                logger.error(f"API hata kodu: {response.status_code}, yanıt: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API isteği sırasında hata oluştu: {e}")
            raise
    
    def get_account_info(self) -> Dict:
        """
        Hesap bilgilerini alır.
        
        Returns:
            Dict: Hesap bilgileri
        """
        try:
            return self._signed_request("GET", "/api/v3/account")
        except Exception as e:
            logger.error(f"Hesap bilgileri alınırken hata oluştu: {e}")
            raise
    
    def get_balances(self) -> List[Dict]:
        """
        Tüm varlık bakiyelerini alır.
        
        Returns:
            List[Dict]: Varlık bakiyeleri listesi
        """
        try:
            account_info = self.get_account_info()
            balances = [
                {
                    'asset': balance['asset'],
                    'free': float(balance['free']),
                    'locked': float(balance['locked']),
                    'total': float(balance['free']) + float(balance['locked'])
                }
                for balance in account_info['balances']
                if float(balance['free']) > 0 or float(balance['locked']) > 0
            ]
            return balances
        except Exception as e:
            logger.error(f"Bakiyeler alınırken hata oluştu: {e}")
            raise
    
    def get_asset_balance(self, asset: str) -> Dict:
        """
        Belirli bir varlık için bakiye bilgisini alır.
        
        Args:
            asset: Varlık sembolü (örn. BTC)
            
        Returns:
            Dict: Varlık bakiye bilgisi
        """
        try:
            balances = self.get_balances()
            for balance in balances:
                if balance['asset'] == asset:
                    return balance
            
            # Varlık bulunamadıysa sıfır bakiye döndür
            return {
                'asset': asset,
                'free': 0.0,
                'locked': 0.0,
                'total': 0.0
            }
        except Exception as e:
            logger.error(f"{asset} bakiyesi alınırken hata oluştu: {e}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Açık emirleri alır.
        
        Args:
            symbol: Sembol (örn. BTCUSDT), belirtilmezse tüm semboller için açık emirler alınır
            
        Returns:
            List[Dict]: Açık emirler listesi
        """
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
            
            return self._signed_request("GET", "/api/v3/openOrders", params)
        except Exception as e:
            logger.error(f"Açık emirler alınırken hata oluştu: {e}")
            raise
    
    def get_all_orders(self, symbol: str, limit: int = 500) -> List[Dict]:
        """
        Sembol için tüm emir geçmişini alır.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            limit: Maksimum emir sayısı
            
        Returns:
            List[Dict]: Emirler listesi
        """
        try:
            params = {
                'symbol': symbol,
                'limit': limit
            }
            
            return self._signed_request("GET", "/api/v3/allOrders", params)
        except Exception as e:
            logger.error(f"{symbol} için emir geçmişi alınırken hata oluştu: {e}")
            raise
    
    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        stop_price: Optional[float] = None,
        iceberg_qty: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Yeni bir emir oluşturur.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            side: Emir yönü (BUY, SELL)
            order_type: Emir tipi (LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, LIMIT_MAKER)
            quantity: Miktar
            price: Fiyat (LIMIT emirleri için)
            time_in_force: Emir süresi (GTC, IOC, FOK)
            stop_price: Stop fiyatı (STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT emirleri için)
            iceberg_qty: Buzdağı miktarı
            quote_order_qty: Quote varlık miktarı (MARKET emirleri için)
            new_client_order_id: Client emir ID
            
        Returns:
            Dict: Emir bilgisi
        """
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
            }
            
            # Emir tipine bağlı zorunlu parametreler
            if order_type == "LIMIT":
                if not price:
                    raise ValueError("LIMIT emirleri için fiyat belirtilmelidir")
                if not quantity:
                    raise ValueError("LIMIT emirleri için miktar belirtilmelidir")
                params['timeInForce'] = time_in_force
                params['price'] = price
                params['quantity'] = quantity
            
            elif order_type == "MARKET":
                if quote_order_qty:
                    # Quote miktar belirtildiyse (örn. 100 USDT)
                    params['quoteOrderQty'] = quote_order_qty
                elif quantity:
                    # Base miktar belirtildiyse (örn. 0.1 BTC)
                    params['quantity'] = quantity
                else:
                    raise ValueError("MARKET emirleri için miktar veya quote miktar belirtilmelidir")
            
            elif order_type in ["STOP_LOSS", "TAKE_PROFIT"]:
                if not quantity:
                    raise ValueError(f"{order_type} emirleri için miktar belirtilmelidir")
                if not stop_price:
                    raise ValueError(f"{order_type} emirleri için stop fiyatı belirtilmelidir")
                params['quantity'] = quantity
                params['stopPrice'] = stop_price
            
            elif order_type in ["STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"]:
                if not quantity or not price or not stop_price:
                    raise ValueError(f"{order_type} emirleri için miktar, fiyat ve stop fiyatı belirtilmelidir")
                params['quantity'] = quantity
                params['price'] = price
                params['stopPrice'] = stop_price
                params['timeInForce'] = time_in_force
            
            elif order_type == "LIMIT_MAKER":
                if not quantity or not price:
                    raise ValueError("LIMIT_MAKER emirleri için miktar ve fiyat belirtilmelidir")
                params['quantity'] = quantity
                params['price'] = price
            
            # Opsiyonel parametreler
            if iceberg_qty:
                params['icebergQty'] = iceberg_qty
                
            if new_client_order_id:
                params['newClientOrderId'] = new_client_order_id
                
            # Ek parametreler
            for key, value in kwargs.items():
                params[key] = value
            
            return self._signed_request("POST", "/api/v3/order", params)
        
        except Exception as e:
            logger.error(f"Emir oluşturulurken hata oluştu: {e}")
            raise
    
    def create_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: Optional[float] = None,
        quote_quantity: Optional[float] = None
    ) -> Dict:
        """
        Market emri oluşturur.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            side: Emir yönü (BUY, SELL)
            quantity: Base varlık miktarı (örn. 0.1 BTC)
            quote_quantity: Quote varlık miktarı (örn. 100 USDT)
            
        Returns:
            Dict: Emir bilgisi
        """
        try:
            if quantity:
                return self.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=quantity
                )
            elif quote_quantity:
                return self.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quote_order_qty=quote_quantity
                )
            else:
                raise ValueError("Miktar veya quote miktar belirtilmelidir")
        except Exception as e:
            logger.error(f"Market emri oluşturulurken hata oluştu: {e}")
            raise
    
    def create_limit_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float,
        time_in_force: str = "GTC"
    ) -> Dict:
        """
        Limit emri oluşturur.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            side: Emir yönü (BUY, SELL)
            quantity: Miktar
            price: Fiyat
            time_in_force: Emir süresi (GTC, IOC, FOK)
            
        Returns:
            Dict: Emir bilgisi
        """
        try:
            return self.create_order(
                symbol=symbol,
                side=side,
                order_type="LIMIT",
                quantity=quantity,
                price=price,
                time_in_force=time_in_force
            )
        except Exception as e:
            logger.error(f"Limit emri oluşturulurken hata oluştu: {e}")
            raise
    
    def create_order_with_sl_tp(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        **kwargs
    ) -> Dict:
        """
        Stop loss ve take profit içeren emir oluşturur.
        
        Not: Bu method önce ana emri oluşturur, sonra stop loss ve take profit emirlerini ekler.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            side: Emir yönü (BUY, SELL)
            order_type: Emir tipi (LIMIT, MARKET)
            quantity: Miktar
            price: Fiyat (LIMIT emirleri için)
            stop_loss: Stop loss fiyatı
            take_profit: Take profit fiyatı
            
        Returns:
            Dict: Ana emir, stop loss emri ve take profit emri bilgilerini içeren sözlük
        """
        try:
            # Ana emri oluştur
            if order_type == "LIMIT":
                if not price:
                    raise ValueError("LIMIT emirleri için fiyat belirtilmelidir")
                
                order = self.create_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    **kwargs
                )
            elif order_type == "MARKET":
                order = self.create_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity
                )
            else:
                raise ValueError(f"Desteklenmeyen emir tipi: {order_type}")
            
            # Sonuç sözlüğünü oluştur
            result = {
                'main_order': order,
                'stop_loss_order': None,
                'take_profit_order': None
            }
            
            # Emir başarılı mı kontrol et
            if order.get('orderId'):
                # Ana emrin yönünün tersi (BUY ise SELL, SELL ise BUY)
                opposite_side = "SELL" if side == "BUY" else "BUY"
                
                # Stop Loss emri ekle
                if stop_loss:
                    sl_order = self.create_order(
                        symbol=symbol,
                        side=opposite_side,
                        order_type="STOP_LOSS",
                        quantity=quantity,
                        stop_price=stop_loss
                    )
                    result['stop_loss_order'] = sl_order
                
                # Take Profit emri ekle
                if take_profit:
                    tp_order = self.create_order(
                        symbol=symbol,
                        side=opposite_side,
                        order_type="TAKE_PROFIT",
                        quantity=quantity,
                        stop_price=take_profit
                    )
                    result['take_profit_order'] = tp_order
            
            return result
        except Exception as e:
            logger.error(f"SL/TP ile emir oluşturulurken hata oluştu: {e}")
            raise
    
    def cancel_order(
        self, 
        symbol: str, 
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None
    ) -> Dict:
        """
        Bir emri iptal eder.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            order_id: Emir ID
            orig_client_order_id: Orijinal client emir ID
            
        Returns:
            Dict: İptal edilen emir bilgisi
        """
        try:
            params = {'symbol': symbol}
            
            if order_id:
                params['orderId'] = order_id
            elif orig_client_order_id:
                params['origClientOrderId'] = orig_client_order_id
            else:
                raise ValueError("order_id veya orig_client_order_id belirtilmelidir")
            
            return self._signed_request("DELETE", "/api/v3/order", params)
        except Exception as e:
            logger.error(f"Emir iptal edilirken hata oluştu: {e}")
            raise
    
    def cancel_all_orders(self, symbol: str) -> List[Dict]:
        """
        Bir sembol için tüm açık emirleri iptal eder.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            
        Returns:
            List[Dict]: İptal edilen emirler listesi
        """
        try:
            params = {'symbol': symbol}
            return self._signed_request("DELETE", "/api/v3/openOrders", params)
        except Exception as e:
            logger.error(f"{symbol} için tüm emirler iptal edilirken hata oluştu: {e}")
            raise
    
    def get_order(
        self, 
        symbol: str, 
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None
    ) -> Dict:
        """
        Bir emrin durumunu sorgular.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            order_id: Emir ID
            orig_client_order_id: Orijinal client emir ID
            
        Returns:
            Dict: Emir bilgisi
        """
        try:
            params = {'symbol': symbol}
            
            if order_id:
                params['orderId'] = order_id
            elif orig_client_order_id:
                params['origClientOrderId'] = orig_client_order_id
            else:
                raise ValueError("order_id veya orig_client_order_id belirtilmelidir")
            
            return self._signed_request("GET", "/api/v3/order", params)
        except Exception as e:
            logger.error(f"Emir durumu sorgulanırken hata oluştu: {e}")
            raise
    
    def get_open_positions(self) -> List[Dict]:
        """
        Açık pozisyonları alır (sadece margin/futures hesapları için).
        
        Not: Spot hesaplar için get_balances() kullanın.
        
        Returns:
            List[Dict]: Açık pozisyonlar listesi
        """
        try:
            account_info = self.get_account_info()
            
            if 'positions' in account_info:
                # Futures API için
                return [
                    pos for pos in account_info['positions'] 
                    if float(pos['positionAmt']) != 0
                ]
            else:
                # Spot hesaplar için
                logger.warning("Spot hesaplar için pozisyon bilgisi alınamaz. get_balances() kullanın.")
                return []
        except Exception as e:
            logger.error(f"Açık pozisyonlar alınırken hata oluştu: {e}")
            raise
    
    def get_exchange_info(self) -> Dict:
        """
        Borsa bilgilerini alır (semboller, filtreleme kuralları, vb.).
        
        Returns:
            Dict: Borsa bilgileri
        """
        try:
            return self._public_request("GET", "/api/v3/exchangeInfo")
        except Exception as e:
            logger.error(f"Borsa bilgileri alınırken hata oluştu: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Bir sembol için detaylı bilgileri alır.
        
        Args:
            symbol: Sembol (örn. BTCUSDT)
            
        Returns:
            Dict: Sembol bilgisi
        """
        try:
            exchange_info = self.get_exchange_info()
            
            for sym in exchange_info['symbols']:
                if sym['symbol'] == symbol:
                    return sym
            
            logger.warning(f"{symbol} sembolü bulunamadı")
            return None
        except Exception as e:
            logger.error(f"{symbol} bilgisi alınırken hata oluştu: {e}")
            raise 