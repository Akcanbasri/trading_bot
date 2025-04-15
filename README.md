# Binance Trading Bot

<div align="center">
  <img src="docs/images/logo.png" alt="Trading Bot Logo" width="200"/>
  <p><em>A modular crypto trading bot with advanced risk management features, following SOLID and DRY principles</em></p>
  
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![Binance API](https://img.shields.io/badge/Binance-API-yellow.svg)](https://binance-docs.github.io/apidocs/)
  [![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
</div>

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Strategies](#-strategies)
- [Risk Management](#-risk-management)
- [Indicators](#-indicators)
- [Signal Management](#-signal-management)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Modular Architecture**: Extensible architecture following SOLID and DRY principles
- **Multiple Strategy Support**: Easy integration of different trading strategies
- **Advanced Risk Management**: Position sizing, stop-loss, and take-profit controls
- **Technical Indicators**: RSI, RSI Middle Band, and other technical indicators
- **Signal Management**: Combining signals from multiple indicators
- **Backtest Support**: Testing strategies on historical data
- **Notification System**: Sending notifications for trade entries/exits
- **Detailed Logging**: Recording all operations and errors

## 📁 Project Structure

```
trading_bot/
├── src/                      # Source code
│   ├── api/                  # Binance API integration
│   ├── config/               # Configuration settings
│   ├── data/                 # Data fetching and processing
│   ├── indicators/           # Technical indicators
│   ├── order_management/     # Order management
│   ├── risk_management/      # Risk management
│   ├── signals/              # Signal generation and control
│   ├── strategies/           # Trading strategies
│   └── utils/                # Utility functions
├── tests/                    # Test files
├── docs/                     # Documentation
└── logs/                     # Log files
```

## 🚀 Installation

### Requirements

- Python 3.9 or higher
- Binance account and API keys

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Akcanbasri/trading_bot.git
   cd trading_bot
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` file and add your Binance API keys:
   ```
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   ```

## 💻 Usage

### Running the Bot

```bash
python -m src.main
```

### Running Backtest

```bash
python -m src.backtest --strategy moving_average --symbol BTCUSDT --start-date 2023-01-01 --end-date 2023-12-31
```

### Strategy Optimization

```bash
python -m src.optimize --strategy moving_average --symbol BTCUSDT --parameter short_period --range 5,20,5
```

## 📊 Strategies

The bot opens long and short positions using two different strategies:

### 1. Moving Average Crossover Strategy

- **Long (Buy) Conditions:**
  - Short-term moving average crosses above long-term moving average
  - Short-term moving average is above long-term moving average and signal strength is greater than 1.0

- **Short (Sell) Conditions:**
  - Short-term moving average crosses below long-term moving average
  - Short-term moving average is below long-term moving average and signal strength is less than -1.0

### 2. FiboBULL Strategy

- **Long (Buy) Conditions:**
  - When FiboBULL PA indicator gives a "BUY" signal
  - When an upward trend is detected

- **Short (Sell) Conditions:**
  - When FiboBULL PA indicator gives a "SELL" signal
  - When a downward trend is detected

### Position Closing Conditions

For both strategies, positions are closed under the following conditions:

1. **Stop-Loss:** When price reaches the specified stop-loss level
2. **Take-Profit:** When price reaches the specified take-profit level
3. **Signal Change:** 
   - When a "SELL" signal is received while in a long position
   - When a "BUY" signal is received while in a short position

## 🛡️ Risk Management

The bot includes the following risk management features:

- **Minimum Position Size:** Minimum 5 USDT position size check for each trade
- **Maximum Position Size:** Limited to 3% of account balance
- **Daily Maximum Loss Limit:** 3% of account balance
- **Total Maximum Loss Limit:** 15% of account balance
- **Dynamic Stop-Loss:** Increasing stop-loss level as profit grows after position opening
- **Profit Taking Levels:** Partial position closing at different profit targets

## 📈 Indicators

The bot uses the following technical indicators:

- **RSI (Relative Strength Index):** For determining overbought/oversold levels
- **RSI Middle Band:** For detecting momentum changes
- **Moving Averages:** For determining trend direction
- **FiboBULL PA:** For generating buy/sell signals based on Fibonacci levels

## 🔔 Signal Management

The `TradeSignalManager` class combines signals from different indicators to make trading decisions:

- Combining signals from multiple indicators
- Ensuring only one open position at a time
- Defining minimum agreement requirement for indicator signals
- Notification mechanism for trade entries and exits
- Detailed trade history tracking

## 🤝 Contributing

To contribute:

1. Fork this repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

---

<div align="center">
  <p>This project is for educational purposes. Cryptocurrency trading involves risk. Please do your own research and implement your risk management strategies.</p>
</div> 