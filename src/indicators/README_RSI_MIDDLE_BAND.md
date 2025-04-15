# RSI Middle Band Göstergesi

Bu gösterge, RSI değerlerinin belirli seviyelerini geçiş durumunu ve EMA değişimini takip ederek alım/satım sinyalleri üretir. PineScript'ten Python'a dönüştürülmüştür.

## Özellikleri

- RSI göstergesinin belirli seviyeler (varsayılan 50/45) arasında geçişini izler
- EMA değişim yönünü kontrol eder
- Pozitif ve negatif momentum koşullarına göre alım/satım sinyalleri üretir
- Sinyal oluştuğunda bir sonraki ters sinyal gelene kadar aktif kalır

## Parametreler

- `rsi_period`: RSI hesaplama periyodu (varsayılan: 14)
- `positive_momentum`: Pozitif momentum için RSI geçiş seviyesi (varsayılan: 50)
- `negative_momentum`: Negatif momentum için RSI geçiş seviyesi (varsayılan: 45)
- `ema_short_period`: Kısa EMA periyodu (varsayılan: 5)
- `ema_long_period`: Uzun EMA periyodu (varsayılan: 10)
- `column`: Hesaplama için kullanılacak veri sütunu (varsayılan: 'close')

## Giriş Koşulları (Alım Sinyali)

Aşağıdaki koşulların tümü sağlanırsa pozitif momentum (alım sinyali) oluşur:

1. Önceki RSI değeri < `positive_momentum` (varsayılan 50)
2. Mevcut RSI değeri > `positive_momentum` 
3. Mevcut RSI değeri > `negative_momentum` (varsayılan 45)
4. EMA değişimi pozitif yönde (EMA artıyor)

## Çıkış Koşulları (Satım Sinyali)

Aşağıdaki koşulların tümü sağlanırsa negatif momentum (satım sinyali) oluşur:

1. RSI değeri < `negative_momentum` (varsayılan 45)
2. EMA değişimi negatif yönde (EMA azalıyor)

## Kullanım Örneği

```python
from src.indicators.rsi_middle_band import RSIMiddleBand

# Göstergeyi oluştur
indicator = RSIMiddleBand(
    rsi_period=14,
    positive_momentum=50,
    negative_momentum=45,
    ema_short_period=5,
    ema_long_period=10
)

# Verileri güncelle ve hesapla
result = indicator.update(price_data)

# Sinyalleri kontrol et
if indicator.is_buy_signal():
    print("ALIM SİNYALİ")
    
if indicator.is_sell_signal():
    print("SATIM SİNYALİ")

# Sinyal detayları al
signal_info = indicator.get_signal()
print(f"Sinyal: {signal_info['signal']}")
print(f"Güç: {signal_info['strength']}")
print(f"RSI Değeri: {signal_info['value']}")
```

## Orijinal PineScript Kodu

```pinescript
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © FiBoBuLL

//@version=5
indicator('RSI Middle Band', overlay=true)

// ** ---> Inputs ------------- {
var bool AL       = false
var bool SAT       = false
string RSI_group        = "RSI Settings"
string mom_group        = "Momentum Vales"
string visual           = "Visuals" 
int Len2                = input(14,"RSI 1️⃣",inline = "rsi",group = RSI_group)
int pmom                = input(50," Positive above",inline = "rsi1",group =RSI_group )
int nmom                = input(45,"Negative below",inline = "rsi1",group =RSI_group )
bool showlabels         = input(true,"Show Momentum ❓",inline = "001",group =visual )
color p                 = input(color.rgb(76, 175, 79, 62),"Positive",inline = "001",group =visual )
color n                 = input(color.rgb(255, 82, 82, 66),"Negative",inline = "001",group =visual )
bool filleshow          = input(true,"Show highlighter ❓",inline = "002",group =visual )
color bull              = input(color.rgb(76, 175, 79, 62),"Bull",inline = "002",group =visual )
color bear              = input(color.rgb(255, 82, 82, 66),"Bear",inline = "002",group =visual )
rsi                     = ta.rsi(close, Len2)
//------------------- }

// ** ---> Momentums ------------- {

p_mom               = rsi[1] < pmom and rsi > pmom and rsi > nmom and ta.change(ta.ema(close,5)) > 0
n_mom               = rsi < nmom and ta.change(ta.ema(close,5)) < 0
if p_mom
    AL:= true
    SAT:= false

if n_mom
    AL:= false
    SAT:= true     

// ** ---> Entry Conditions ------------- {

a = plot(filleshow ? ta.ema(high,5) : na,display = display.none,editable = false)
b = plot(filleshow ? ta.ema(low,10) : na,style = plot.style_stepline,color = color.red,display = display.none,editable = false)

// fill(a,b,color = color.from_gradient(rsi14,35,pmom,color.rgb(255, 82, 82, 66),color.rgb(76, 175, 79, 64)) )
fill(a,b,color = AL ? bull :bear ,editable = false)
``` 