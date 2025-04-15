# Binance API Client

Binance API'si ile güvenli bağlantı kuran ve çeşitli işlem fonksiyonlarını içeren Python modülü.

## Özellikleri

- Binance API ile güvenli bağlantı kurma
- API kimlik bilgilerini .env veya config dosyasından yükleme
- Mainnet ve Testnet desteği
- Hesap bilgilerini ve bakiyeleri görüntüleme
- Çeşitli emir tipleri oluşturma (market, limit, stop-loss, take-profit)
- Stop-loss ve take-profit içeren emirler oluşturma
- Açık emirleri listeleme ve iptal etme
- Kapsamlı hata yönetimi ve loglama

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install requests python-dotenv loguru
```

2. `.env.binance.example` dosyasını `.env` olarak kopyalayın ve API bilgilerinizi ekleyin:
```bash
cp .env.binance.example .env
# Dosyayı düzenleyip API bilgilerinizi ekleyin
```

3. (Opsiyonel) Testnet kullanmak için [Binance Testnet](https://testnet.binance.vision/) üzerinden test API anahtarları alın.

## Kullanım

### Basit Kullanım

```python
from src.api.binance_client import BinanceClient

# Testnet için client oluştur (test amaçlı)
client = BinanceClient(testnet=True)

# Veya gerçek hesap için
# client = BinanceClient(testnet=False)

# Hesap bilgilerini al
account = client.get_account_info()
print(f"Hesap tipi: {account.get('accountType')}")

# Bakiyeleri görüntüle
balances = client.get_balances()
for balance in balances:
    print(f"{balance['asset']}: {balance['free']} (serbest), {balance['locked']} (blokeli)")

# Bir sembol için açık emirleri görüntüle
open_orders = client.get_open_orders("BTCUSDT")
print(f"Açık emirler: {len(open_orders)}")
```

### Alım-Satım İşlemleri

```python
# Market emri oluştur
market_order = client.create_market_order(
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.001  # 0.001 BTC satın al
)

# Limit emri oluştur
limit_order = client.create_limit_order(
    symbol="BTCUSDT",
    side="SELL",
    quantity=0.001,
    price=50000  # $50,000 fiyatından sat
)

# Stop Loss ve Take Profit içeren emir oluştur
sl_tp_order = client.create_order_with_sl_tp(
    symbol="BTCUSDT",
    side="BUY",
    order_type="MARKET",
    quantity=0.001,
    stop_loss=45000,  # $45,000 altına düşerse sat
    take_profit=55000  # $55,000 üstüne çıkarsa sat
)

# Bir emri iptal et
cancel_result = client.cancel_order(
    symbol="BTCUSDT",
    order_id=market_order['orderId']
)

# Tüm açık emirleri iptal et
cancel_all = client.cancel_all_orders("BTCUSDT")
```

## Önemli Metodlar

### Bağlantı ve Kimlik Doğrulama

- `__init__(testnet=False, config_path=None)`: Client sınıfını başlatır
- `_load_config_from_env()`: .env dosyasından API bilgilerini yükler
- `_load_config_from_file(config_path)`: JSON dosyasından API bilgilerini yükler

### Hesap ve Bakiye İşlemleri

- `get_account_info()`: Hesap bilgilerini alır
- `get_balances()`: Tüm varlık bakiyelerini alır
- `get_asset_balance(asset)`: Belirli bir varlık için bakiye bilgisi alır
- `get_open_positions()`: Açık pozisyonları alır (margin/futures için)

### Emir İşlemleri

- `get_open_orders(symbol)`: Açık emirleri alır
- `get_all_orders(symbol, limit)`: Tüm emir geçmişini alır
- `create_order(...)`: Genel emir oluşturma metodu
- `create_market_order(symbol, side, quantity, quote_quantity)`: Market emri oluşturur
- `create_limit_order(symbol, side, quantity, price)`: Limit emri oluşturur
- `create_order_with_sl_tp(...)`: Stop loss ve take profit içeren emir oluşturur
- `cancel_order(symbol, order_id)`: Bir emri iptal eder
- `cancel_all_orders(symbol)`: Tüm açık emirleri iptal eder
- `get_order(symbol, order_id)`: Bir emrin durumunu sorgular

### Piyasa Verileri

- `get_exchange_info()`: Borsa bilgilerini alır
- `get_symbol_info(symbol)`: Bir sembol için detaylı bilgileri alır

## Hata Yönetimi

Client sınıfı, olası tüm hataları yakalar ve loglar. Her metot, bir hata oluştuğunda açıklayıcı hata mesajlarıyla birlikte istisnaları yeniden yükseltir. 

API istekleri, 5xx sunucu hataları için otomatik olarak yeniden deneme mantığı içermez, gerekirse bu mantık eklenmesi gerekebilir.

## Güvenlik Notları

- API anahtarlarınızı her zaman güvende tutun ve paylaşmayın
- Gerçek hesaplar için testnet'te test ettiğiniz kodları kullanın
- Büyük miktarlarda işlem yapmadan önce küçük miktarlarla test edin
- İşlem yaparken her zaman miktar ve fiyat limitlerini kontrol edin

## Lisans

Bu kod, açık kaynak olarak MIT lisansı altında dağıtılmaktadır. 