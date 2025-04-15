# Binance Trading Bot

Binance API kullanan, modüler, SOLID ve DRY prensiplerine uygun bir trading bot.

## Proje Yapısı

```
trading_bot/
├── src/                      # Kaynak kod
│   ├── api/                  # Binance API entegrasyonu
│   ├── config/               # Yapılandırma ayarları
│   ├── data/                 # Veri çekme ve işleme
│   ├── indicators/           # Teknik göstergeler
│   ├── order_management/     # Emir yönetimi
│   ├── risk_management/      # Risk yönetimi
│   ├── signals/              # Sinyal oluşturma ve kontrol
│   ├── strategies/           # Trading stratejileri
│   └── utils/                # Yardımcı fonksiyonlar
├── tests/                    # Test dosyaları
├── docs/                     # Dökümantasyon
└── logs/                     # Log dosyaları
```

## Kurulum

```bash
# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt
```

## Kullanım

```bash
python -m src.main
```

## Long ve Short Koşulları

Bot, iki farklı strateji kullanarak long ve short pozisyonlar açar:

### 1. Hareketli Ortalama Kesişimi (Moving Average Crossover) Stratejisi

- **Long (Alış) Koşulları:**
  - Kısa dönem hareketli ortalama, uzun dönem hareketli ortalamayı yukarı keserse
  - Kısa dönem hareketli ortalama, uzun dönem hareketli ortalamanın üzerinde ve sinyal gücü 1.0'dan büyükse

- **Short (Satış) Koşulları:**
  - Kısa dönem hareketli ortalama, uzun dönem hareketli ortalamayı aşağı keserse
  - Kısa dönem hareketli ortalama, uzun dönem hareketli ortalamanın altında ve sinyal gücü -1.0'dan küçükse

### 2. FiboBULL Stratejisi

- **Long (Alış) Koşulları:**
  - FiboBULL PA göstergesi "BUY" sinyali verdiğinde
  - Yukarı trend başlangıcı tespit edildiğinde

- **Short (Satış) Koşulları:**
  - FiboBULL PA göstergesi "SELL" sinyali verdiğinde
  - Aşağı trend başlangıcı tespit edildiğinde

### Pozisyon Kapatma Koşulları

Her iki strateji için de pozisyonlar şu durumlarda kapatılır:

1. **Stop-Loss:** Fiyat, belirlenen stop-loss seviyesine ulaştığında
2. **Take-Profit:** Fiyat, belirlenen take-profit seviyesine ulaştığında
3. **Sinyal Değişimi:** 
   - Long pozisyondayken "SELL" sinyali geldiğinde
   - Short pozisyondayken "BUY" sinyali geldiğinde

### Risk Yönetimi

- Her işlem için minimum 5 USDT'lik pozisyon büyüklüğü kontrolü
- Maksimum pozisyon büyüklüğü hesap bakiyesinin %3'ü ile sınırlı
- Günlük maksimum kayıp limiti hesap bakiyesinin %3'ü
- Toplam maksimum kayıp limiti hesap bakiyesinin %15'i 