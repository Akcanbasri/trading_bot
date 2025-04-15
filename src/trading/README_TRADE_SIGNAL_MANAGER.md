# Trade Signal Manager

TradeSignalManager, farklı göstergelerden gelen sinyalleri birleştirerek alım/satım kararları veren ve aynı anda sadece bir açık pozisyon olmasını sağlayan bir modüldür.

## Özellikleri

- Birden fazla teknik göstergenin sinyallerini birleştirir
- Aynı anda sadece bir açık pozisyon olmasını sağlar (pozisyon kontrolü)
- Gösterge sinyallerinde minimum uyum şartı tanımlanabilir
- İşlem açılış ve kapanışlarında bildirim mekanizması
- Detaylı işlem geçmişi tutma
- Pozisyon büyüklüğü ve risk yönetimi
- Etkinleştirme/devre dışı bırakma desteği

## Kullanım

### Temel Kullanım

```python
from src.trading.trade_signal_manager import TradeSignalManager
from src.indicators.rsi_middle_band import RSIMiddleBand
from src.indicators.rsi import RSI
from src.api.binance_client import BinanceClient

# Binance API client oluştur
client = BinanceClient(testnet=True)  # Test için testnet

# Göstergeleri oluştur
rsi_indicator = RSI(period=14, overbought=70, oversold=30)
rsi_middle_band = RSIMiddleBand(
    rsi_period=14, 
    positive_momentum=50, 
    negative_momentum=45
)

# Göstergeleri bir dictionary içinde topla
indicators = {
    "RSI": rsi_indicator,
    "RSI_Middle_Band": rsi_middle_band
}

# Bildirim callback fonksiyonu
def notification_handler(trade_info):
    print(f"İşlem bildirimi: {trade_info}")
    # Telegram, Email, vb. bildirimler eklenebilir

# TradeSignalManager oluştur
signal_manager = TradeSignalManager(
    client=client,
    symbol="BTCUSDT",
    indicators=indicators,
    notification_callback=notification_handler,
    min_signal_agreement=1  # Sadece bir göstergeden gelen sinyal yeterli
)

# Yeni veri geldiğinde güncelle
signal_manager.update(new_price_data)

# Mevcut pozisyon durumunu görüntüle
position_status = signal_manager.get_position_status()
print(position_status)

# İşlem geçmişini al
trade_history = signal_manager.get_trade_history()
```

### Sinyal Türleri

TradeSignalManager aşağıdaki sinyal türlerini destekler:

- `LONG`: Alış (Long) pozisyonu açma sinyali
- `SHORT`: Satış (Short) pozisyonu açma sinyali
- `CLOSE_LONG`: Long pozisyonu kapatma sinyali
- `CLOSE_SHORT`: Short pozisyonu kapatma sinyali
- `NEUTRAL`: Tarafsız (işlem yapma) sinyali

### Pozisyon Kontrolü

TradeSignalManager, aynı anda sadece bir açık pozisyon olmasını garanti eder:

1. Hiç pozisyon yokken (`NONE`) bir LONG sinyali gelirse, long pozisyon açılır
2. Hiç pozisyon yokken (`NONE`) bir SHORT sinyali gelirse, short pozisyon açılır
3. Long pozisyon varken (`LONG`) bir CLOSE_LONG sinyali gelirse, pozisyon kapatılır
4. Short pozisyon varken (`SHORT`) bir CLOSE_SHORT sinyali gelirse, pozisyon kapatılır
5. Long pozisyon varken bir SHORT sinyali gelirse, önce long pozisyon kapatılır
6. Short pozisyon varken bir LONG sinyali gelirse, önce short pozisyon kapatılır

### İşlem Bildirimleri

TradeSignalManager, her işlem açılışında ve kapanışında bir bildirim callback fonksiyonu çağırır. Bu fonksiyon, aşağıdaki bilgileri içeren bir sözlük alır:

**Açılış İşlemi Örneği:**
```json
{
  "type": "OPEN",
  "position": "LONG",
  "symbol": "BTCUSDT",
  "size": 0.001,
  "price": 50000.0,
  "time": "2023-01-01T12:00:00",
  "order_id": "123456789",
  "signals": {
    "RSI": "LONG",
    "RSI_Middle_Band": "NEUTRAL"
  }
}
```

**Kapanış İşlemi Örneği:**
```json
{
  "type": "CLOSE",
  "position": "LONG",
  "symbol": "BTCUSDT",
  "size": 0.001,
  "entry_price": 50000.0,
  "exit_price": 52000.0,
  "pnl": 2.0,
  "pnl_percentage": 4.0,
  "time": "2023-01-02T12:00:00",
  "duration": 86400,
  "order_id": "987654321",
  "signals": {
    "RSI": "CLOSE_LONG",
    "RSI_Middle_Band": "SHORT"
  }
}
```

## Backtest Kullanımı

TradeSignalManager, geçmiş veriler üzerinde backtest yapmak için de kullanılabilir. Backtest için sahte bir Binance client sınıfı kullanılabilir:

```python
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
        return {"orderId": "mock_order_id", "status": "FILLED", "executedQty": quantity}

# TradeSignalManager'ı backtest için kullan
mock_client = MockBinanceClient()
signal_manager = TradeSignalManager(client=mock_client, symbol="BTCUSDT", indicators=indicators)

# Her mum için işlem simülasyonu yap
for i in range(1, len(historical_data)):
    # Mock client'a şu anki fiyatı ayarla
    current_price = historical_data.iloc[i]['close']
    mock_client.current_price = current_price
    
    # Göstergeleri güncelle ve sinyalleri al
    signal_manager.update(historical_data.iloc[:i+1])
```

## Özelleştirme

TradeSignalManager sınıfı, farklı gereksinimler için özelleştirilebilir:

- **min_signal_agreement**: İşlem kararı için gereken minimum gösterge uyumu sayısı
- **notification_callback**: İşlem bildirimleri için özel callback fonksiyonu
- **enabled**: Sinyallerin işlem yaratıp yaratmayacağı (backtesting için kapatılabilir)

## Hata Yönetimi

TradeSignalManager, tüm kritik işlemleri try/except blokları içinde gerçekleştirir ve hataları loglar. API istekleri veya diğer işlemler sırasında oluşan hatalar, kullanıcıya bildirilir ve güvenli bir şekilde ele alınır.

## Risk Yönetimi

TradeSignalManager, varsayılan olarak hesap bakiyesinin %1'i kadar pozisyon açar. Bu değer, ihtiyaca göre değiştirilebilir. Ayrıca, uygulama kapsamında stop-loss ve take-profit emirleri ile risk yönetimi stratejileri eklenebilir.

## İleriki Geliştirmeler

- Stop-loss ve take-profit seviyelerinin otomatik ayarlanması
- Trailing stop desteği
- Birden fazla zaman diliminde sinyal doğrulama
- Daha gelişmiş pozisyon büyüklüğü hesaplaması
- Farklı varlık çiftleri için çoklu sinyal yönetimi 