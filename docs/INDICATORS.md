# Teknik Göstergeler

Bu projede kullanılan teknik göstergeler, fiyat hareketlerini analiz etmek ve alım/satım sinyalleri üretmek için kullanılır. Her gösterge, belirli bir teknik analiz stratejisini uygular ve sinyaller üretir.

## Gösterge Arayüzü

Tüm göstergeler, aşağıdaki temel arayüzü uygular:

```python
class Indicator:
    def __init__(self):
        self.last_signal = "NEUTRAL"
        
    def update(self, data):
        """
        Yeni veri ile göstergeleri günceller.
        
        Args:
            data (pd.DataFrame): OHLCV verileri içeren DataFrame
        """
        pass
        
    def get_signal(self):
        """
        Mevcut sinyali döndürür.
        
        Returns:
            str: "LONG", "SHORT", "CLOSE_LONG", "CLOSE_SHORT" veya "NEUTRAL"
        """
        return self.last_signal
```

## RSI (Relative Strength Index)

RSI, fiyat momentumunu ölçen popüler bir göstergedir. Aşırı alım ve aşırı satım seviyelerini belirleyerek alım/satım sinyalleri üretir.

### Özellikleri

- Periyot: Varsayılan 14
- Aşırı alım seviyesi: Varsayılan 70
- Aşırı satım seviyesi: Varsayılan 30

### Sinyal Mantığı

- RSI 30'un altına düştüğünde: LONG sinyali
- RSI 70'in üzerine çıktığında: SHORT sinyali
- RSI 50'nin altına düştüğünde (long pozisyondayken): CLOSE_LONG sinyali
- RSI 50'nin üzerine çıktığında (short pozisyondayken): CLOSE_SHORT sinyali

### Kullanım

```python
from src.indicators.rsi import RSI

# RSI göstergesi oluştur
rsi = RSI(period=14, overbought=70, oversold=30)

# Yeni veri ile güncelle
rsi.update(price_data)

# Sinyal al
signal = rsi.get_signal()
```

## RSI Middle Band

RSI Middle Band, RSI göstergesinin orta bandını (50 seviyesi) kullanarak momentum değişimlerini tespit eder. Pozitif ve negatif momentum seviyeleri tanımlanabilir.

### Özellikleri

- RSI periyodu: Varsayılan 14
- Pozitif momentum seviyesi: Varsayılan 50
- Negatif momentum seviyesi: Varsayılan 45

### Sinyal Mantığı

- RSI pozitif momentum seviyesinin üzerine çıktığında: LONG sinyali
- RSI negatif momentum seviyesinin altına düştüğünde: SHORT sinyali
- RSI negatif momentum seviyesinin altına düştüğünde (long pozisyondayken): CLOSE_LONG sinyali
- RSI pozitif momentum seviyesinin üzerine çıktığında (short pozisyondayken): CLOSE_SHORT sinyali

### Kullanım

```python
from src.indicators.rsi_middle_band import RSIMiddleBand

# RSI Middle Band göstergesi oluştur
rsi_middle_band = RSIMiddleBand(
    rsi_period=14,
    positive_momentum=50,
    negative_momentum=45
)

# Yeni veri ile güncelle
rsi_middle_band.update(price_data)

# Sinyal al
signal = rsi_middle_band.get_signal()
```

## Gösterge Kombinasyonları

Farklı göstergelerin sinyalleri birleştirilerek daha güvenilir alım/satım kararları alınabilir. Örneğin:

```python
from src.indicators.rsi import RSI
from src.indicators.rsi_middle_band import RSIMiddleBand
from src.trading.trade_signal_manager import TradeSignalManager

# Göstergeleri oluştur
rsi = RSI(period=14, overbought=70, oversold=30)
rsi_middle_band = RSIMiddleBand(
    rsi_period=14,
    positive_momentum=50,
    negative_momentum=45
)

# Göstergeleri bir dictionary içinde topla
indicators = {
    "RSI": rsi,
    "RSI_Middle_Band": rsi_middle_band
}

# TradeSignalManager oluştur
signal_manager = TradeSignalManager(
    client=client,
    symbol="BTCUSDT",
    indicators=indicators,
    min_signal_agreement=2  # En az 2 göstergeden gelen sinyal gerekli
)
```

## Yeni Gösterge Ekleme

Yeni bir gösterge eklemek için, temel `Indicator` sınıfını uygulayan yeni bir sınıf oluşturulmalıdır:

```python
from src.indicators.base_indicator import Indicator

class NewIndicator(Indicator):
    def __init__(self, param1, param2):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
        
    def update(self, data):
        # Gösterge hesaplamaları
        # ...
        
        # Sinyal belirleme
        if condition1:
            self.last_signal = "LONG"
        elif condition2:
            self.last_signal = "SHORT"
        elif condition3:
            self.last_signal = "CLOSE_LONG"
        elif condition4:
            self.last_signal = "CLOSE_SHORT"
        else:
            self.last_signal = "NEUTRAL"
```

## Gösterge Optimizasyonu

Göstergelerin parametreleri, geçmiş veriler üzerinde backtest yapılarak optimize edilebilir. Örnek bir optimizasyon süreci:

1. Parametre aralıklarını belirle
2. Her parametre kombinasyonu için backtest yap
3. En iyi performans gösteren parametreleri seç

```python
def optimize_indicator(data, param_ranges):
    best_params = None
    best_performance = float('-inf')
    
    for params in param_combinations(param_ranges):
        indicator = NewIndicator(**params)
        
        # Backtest
        performance = backtest(indicator, data)
        
        if performance > best_performance:
            best_performance = performance
            best_params = params
            
    return best_params
```

## İleriki Geliştirmeler

- Daha fazla teknik gösterge ekleme (MACD, Bollinger Bands, vb.)
- Gösterge parametrelerinin otomatik optimizasyonu
- Gösterge sinyallerinin ağırlıklandırılması
- Farklı zaman dilimlerinde gösterge analizi
- Makine öğrenimi tabanlı gösterge kombinasyonları 