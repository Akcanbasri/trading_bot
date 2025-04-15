# Technical Indicators

This document describes the technical indicators used in the project and how they function.

## Indicator Interface

All indicators in the project implement the following interface:

```python
class Indicator:
    def calculate(self, data: pd.DataFrame) -> float:
        """
        Calculate the indicator value for the given data.
        
        Args:
            data (pd.DataFrame): Price data with OHLCV columns
            
        Returns:
            float: Calculated indicator value
        """
        pass
```

## RSI (Relative Strength Index)

The RSI is a momentum oscillator that measures the speed and magnitude of recent price changes to evaluate overbought or oversold conditions.

### Signal Logic

- **Overbought (Sell Signal):** RSI > 70
- **Oversold (Buy Signal):** RSI < 30
- **Neutral:** 30 ≤ RSI ≤ 70

### Implementation

```python
def calculate_rsi(data: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate RSI for the given data.
    
    Args:
        data (pd.DataFrame): Price data
        period (int): RSI period
        
    Returns:
        float: RSI value
    """
    # Implementation details...
```

## RSI Middle Band

The RSI Middle Band strategy combines RSI with EMA (Exponential Moving Average) to generate trading signals.

### Signal Logic

- **Long Signal:** 
  - RSI < Negative Momentum (default: 30)
  - Current price < EMA

- **Short Signal:**
  - RSI > Positive Momentum (default: 70)
  - Current price > EMA

### Implementation

```python
def calculate_ema(data: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate EMA for the given data.
    
    Args:
        data (pd.DataFrame): Price data
        period (int): EMA period
        
    Returns:
        float: EMA value
    """
    # Implementation details...
```

## Combining Indicators

Indicators can be combined to create more robust trading signals:

```python
def combine_signals(rsi_signal: float, ema_signal: float) -> float:
    """
    Combine signals from multiple indicators.
    
    Args:
        rsi_signal (float): RSI signal (-1 to 1)
        ema_signal (float): EMA signal (-1 to 1)
        
    Returns:
        float: Combined signal (-1 to 1)
    """
    # Implementation details...
```

## Adding New Indicators

To add a new indicator:

1. Create a new class implementing the Indicator interface
2. Implement the calculate() method
3. Add signal logic specific to the indicator
4. Register the indicator in the strategy configuration

## Optimization

Indicators can be optimized by:

1. Adjusting period lengths
2. Modifying signal thresholds
3. Adding additional confirmation indicators
4. Implementing custom signal combination logic

## Future Improvements

- Add more technical indicators (MACD, Bollinger Bands, etc.)
- Implement machine learning for signal optimization
- Add backtesting capabilities for indicator performance analysis
- Create a web interface for real-time indicator monitoring 