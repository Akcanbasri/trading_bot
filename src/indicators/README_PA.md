# FiboBULL PA Göstergesi ve Strateji

Bu modül, PineScript'te yazılmış olan FiboBULL PA göstergesinin Python versiyonunu içerir. Gösterge, pivot high/low noktalarını tespit eder, trend yönünü belirler ve destek-direnç seviyelerini hesaplar.

## Göstergenin Özellikleri

- Pivot high ve low noktalarını tespit eder
- Higher High (HH), Lower Low (LL), Higher Low (HL), Lower High (LH) paternlerini bulur
- Dinamik destek ve direnç seviyeleri hesaplar
- Trend yönünü belirler (yukarı, aşağı, yatay)
- Long ve short alım/satım sinyalleri üretir

## Kurulum ve Kullanım

### Bağımlılıklar

Göstergeyi kullanmak için aşağıdaki Python kütüphaneleri gereklidir:

```
pip install pandas numpy matplotlib loguru
```

Gerçek verilerle test etmek için:

```
pip install yfinance
```

### Göstergeyi Kullanma

```python
from src.indicators.fibobuLL_pa import FiboBULLPA
import pandas as pd

# Veri hazırla (OHLCV formatında)
df = your_data_loading_function()  # high, low, close sütunları içermeli

# Göstergeyi oluştur
fibo_indicator = FiboBULLPA(left_bars=8, right_bars=8)

# Göstergeyi hesapla
result = fibo_indicator.calculate(df)

# Sinyalleri kontrol et
if fibo_indicator.is_valid_signal():
    signal = fibo_indicator.get_signal()
    print(f"Sinyal: {signal['signal']}, Taraf: {signal['side']}, Güç: {signal['strength']}")

# Destek ve direnç seviyelerini al
levels = fibo_indicator.get_support_resistance()
print(f"Destek: {levels['support']}, Direnç: {levels['resistance']}")

# Mevcut trend yönünü al
trend = fibo_indicator.get_current_trend()
trend_text = "Yukarı" if trend == 1 else "Aşağı" if trend == -1 else "Yatay"
print(f"Trend: {trend_text}")
```

### Stratejiyi Kullanma

```python
from src.strategies.fibobuLL_strategy import FiboBULLStrategy
import pandas as pd

# Veri hazırla (OHLCV formatında)
df = your_data_loading_function()  # high, low, close sütunları içermeli

# Stratejiyi oluştur
strategy = FiboBULLStrategy(
    left_bars=8,
    right_bars=8,
    stop_loss_percent=2.0,
    take_profit_percent=4.0
)

# Stratejiyi güncelle ve sinyal al
signal = strategy.update(df)
print(f"Sinyal: {signal['signal']}, İşlem: {signal['action']}, Neden: {signal['reason']}")

# Backtest yap
backtest_results = strategy.backtest(df)
```

## Test Etme

Göstergeyi ve stratejiyi test etmek için örnek bir test betiği oluşturulmuştur:

```
python -m src.test_fibobuLL_strategy
```

Bu komut, örnek veriler üzerinde stratejiyi çalıştırır ve sonuçları görselleştirir.

## Parametreler

### FiboBULLPA Göstergesi

- `left_bars`: Pivot noktası tespiti için sol bar sayısı (varsayılan: 8)
- `right_bars`: Pivot noktası tespiti için sağ bar sayısı (varsayılan: 8)
- `show_sup_res`: Destek-direnç çizgilerini gösterme durumu (varsayılan: True)

### FiboBULLStrategy Stratejisi

- `left_bars`: Pivot noktası tespiti için sol bar sayısı (varsayılan: 8)
- `right_bars`: Pivot noktası tespiti için sağ bar sayısı (varsayılan: 8)
- `use_confirmations`: Ek onay göstergeleri kullanılsın mı (varsayılan: True)
- `stop_loss_percent`: Stop-loss yüzdesi (varsayılan: 3.0)
- `take_profit_percent`: Take-profit yüzdesi (varsayılan: 6.0)

## PineScript Kodu

Bu gösterge, aşağıdaki PineScript kodunun Python'a çevrilmiş halidir:

```
//@version=4
study("FiboBuLL PA", overlay=true, max_lines_count=500)
///-------------------------------------------------------------------------------
findprevious(lb,rb) =>  // finds previous three points (b, c, d, e)
    ph = pivothigh(lb, rb)
    pl = pivotlow(lb, rb)

    hl = iff(ph, 1, iff(pl, -1, na)) // Trend direction
    zz = iff(ph, ph, iff(pl, pl, na)) // similar to zigzag but may have multiple highs/lows
    ...
    [hl,zz,loc1, loc2, loc3, loc4]
///---------------------------------------------------------------------------------------------
// ... (diğer PineScript kodları)
```

## Örnek Sonuçlar

Strateji, backtest sonucunda aşağıdaki metrikleri üretir:

- Toplam işlem sayısı
- Kazançlı işlemler
- Zararlı işlemler
- Kazanç oranı (%)
- Kâr faktörü
- Toplam getiri (%)
- Maksimum drawdown (%)

## Lisans

Bu gösterge ve strateji açık kaynak olarak sunulmuştur ve kişisel/ticari kullanıma uygundur. 