# Binance Trading Bot

<div align="center">
  <img src="docs/images/logo.png" alt="Trading Bot Logo" width="200"/>
  <p><em>Modüler, SOLID ve DRY prensiplerine uygun, gelişmiş risk yönetimi özelliklerine sahip kripto trading bot</em></p>
  
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Binance API](https://img.shields.io/badge/Binance-API-yellow.svg)](https://binance-docs.github.io/apidocs/)
  [![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
</div>

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Proje Yapısı](#-proje-yapısı)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Stratejiler](#-stratejiler)
- [Risk Yönetimi](#-risk-yönetimi)
- [Göstergeler](#-göstergeler)
- [Sinyal Yönetimi](#-sinyal-yönetimi)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

## ✨ Özellikler

- **Modüler Yapı**: SOLID ve DRY prensiplerine uygun, genişletilebilir mimari
- **Çoklu Strateji Desteği**: Farklı trading stratejilerini kolayca entegre edebilme
- **Gelişmiş Risk Yönetimi**: Pozisyon büyüklüğü, stop-loss ve take-profit kontrolleri
- **Teknik Göstergeler**: RSI, RSI Middle Band ve diğer teknik göstergeler
- **Sinyal Yönetimi**: Birden fazla göstergeden gelen sinyalleri birleştirme
- **Backtest Desteği**: Geçmiş veriler üzerinde stratejileri test etme
- **Bildirim Sistemi**: İşlem açılış/kapanışlarında bildirim gönderme
- **Detaylı Loglama**: Tüm işlemlerin ve hataların kaydedilmesi

## 📁 Proje Yapısı

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

## 🚀 Kurulum

### Gereksinimler

- Python 3.9 veya üzeri
- Binance hesabı ve API anahtarları

### Adımlar

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/Akcanbasri/trading_bot.git
   cd trading_bot
   ```

2. Sanal ortam oluşturun ve aktifleştirin:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. `.env` dosyasını oluşturun:
   ```bash
   cp .env.example .env
   ```

5. `.env` dosyasını düzenleyin ve Binance API anahtarlarınızı ekleyin:
   ```
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   ```

## 💻 Kullanım

### Botu Çalıştırma

```bash
python -m src.main
```

### Backtest Yapma

```bash
python -m src.backtest --strategy moving_average --symbol BTCUSDT --start-date 2023-01-01 --end-date 2023-12-31
```

### Strateji Optimizasyonu

```bash
python -m src.optimize --strategy moving_average --symbol BTCUSDT --parameter short_period --range 5,20,5
```

## 📊 Stratejiler

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

## 🛡️ Risk Yönetimi

Bot, aşağıdaki risk yönetimi özelliklerini içerir:

- **Minimum Pozisyon Büyüklüğü:** Her işlem için minimum 5 USDT'lik pozisyon büyüklüğü kontrolü
- **Maksimum Pozisyon Büyüklüğü:** Hesap bakiyesinin %3'ü ile sınırlı
- **Günlük Maksimum Kayıp Limiti:** Hesap bakiyesinin %3'ü
- **Toplam Maksimum Kayıp Limiti:** Hesap bakiyesinin %15'i
- **Dinamik Stop-Loss:** Pozisyon açıldıktan sonra kâr arttıkça stop-loss seviyesini yükseltme
- **Kâr Alım Seviyeleri:** Farklı kâr hedeflerine ulaşıldığında kısmi pozisyon kapatma

## 📈 Göstergeler

Bot, aşağıdaki teknik göstergeleri kullanır:

- **RSI (Relative Strength Index):** Aşırı alım/satım seviyelerini belirlemek için
- **RSI Middle Band:** Momentum değişimlerini tespit etmek için
- **Hareketli Ortalamalar:** Trend yönünü belirlemek için
- **FiboBULL PA:** Fibonacci seviyelerine göre alım/satım sinyalleri üretmek için

## 🔔 Sinyal Yönetimi

`TradeSignalManager` sınıfı, farklı göstergelerden gelen sinyalleri birleştirerek alım/satım kararları verir:

- Birden fazla göstergenin sinyallerini birleştirme
- Aynı anda sadece bir açık pozisyon olmasını sağlama
- Gösterge sinyallerinde minimum uyum şartı tanımlama
- İşlem açılış ve kapanışlarında bildirim mekanizması
- Detaylı işlem geçmişi tutma

## 🤝 Katkıda Bulunma

Katkıda bulunmak için:

1. Bu repoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Daha fazla bilgi için [LICENSE](LICENSE) dosyasına bakın.

---

<div align="center">
  <p>Bu proje eğitim amaçlıdır. Kripto para ticareti risk içerir. Lütfen kendi araştırmanızı yapın ve risk yönetimi stratejilerinizi uygulayın.</p>
</div> 