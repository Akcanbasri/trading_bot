"""
Custom exceptions for the trading bot.

This module contains custom exceptions used throughout the trading bot application
to provide more specific error handling and meaningful error messages.
"""

class TradingBotException(Exception):
    """Base exception class for all trading bot exceptions."""
    pass

class InsufficientDataError(TradingBotException):
    """Exception raised when there is insufficient data for calculations or analysis."""
    pass

class CalculationError(TradingBotException):
    """Exception raised when there is an error during calculations."""
    pass

class MarketDataError(TradingBotException):
    """Exception raised when there is an error fetching or processing market data."""
    pass

class ConfigurationError(TradingBotException):
    """Exception raised when there is an error in the configuration."""
    pass

class APIError(TradingBotException):
    """Exception raised when there is an error in API communication."""
    pass

class OrderError(TradingBotException):
    """Exception raised when there is an error placing, modifying, or canceling an order."""
    pass

class PositionError(TradingBotException):
    """Exception raised when there is an error managing positions."""
    pass

class AuthenticationError(TradingBotException):
    """Exception raised when there is an authentication error."""
    pass

class RiskManagementError(TradingBotException):
    """Exception raised when a risk management rule is violated."""
    pass

class StrategyError(TradingBotException):
    """Exception raised when there is an error in a strategy."""
    pass 