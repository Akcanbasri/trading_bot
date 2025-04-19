"""
Scaled Entry/Exit Strategy implementation.
This strategy combines MACD, RSI Middle Band, and FiboBuLL PA indicators with scaled entry/exit logic.
"""

import numpy as np
import pandas as pd
import math
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.data.market_data import MarketDataCollector
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_middle_band_strategy import RSIMiddleBandStrategy
from src.strategies.fibobull_pa_strategy import FibobullPAStrategy
from src.telegram_notifier import TelegramNotifier


class ScaledEntryExitStrategy(BaseStrategy):
    """
    Scaled Entry/Exit Strategy implementation.
    Combines MACD, RSI Middle Band, and FiboBuLL PA indicators with scaled entry/exit logic.
    """

    def __init__(
        self,
        market_data: MarketDataCollector,
        telegram_notifier: Optional[TelegramNotifier] = None,
        # MACD parameters
        macd_fast_period: int = 12,
        macd_slow_period: int = 26,
        macd_signal_period: int = 9,
        macd_histogram_threshold: float = 0.0,
        # RSI Middle Band parameters
        rsi_period: int = 14,
        rsi_positive_momentum: float = 50.0,
        rsi_negative_momentum: float = 45.0,
        rsi_ema_period: int = 5,
        # FiboBuLL PA parameters
        fibo_left_bars: int = 8,
        fibo_right_bars: int = 8,
        # Position sizing parameters
        tier1_size_percentage: float = 0.4,  # 40% of total position size
        tier2_size_percentage: float = 0.3,  # 30% of total position size
        tier3_size_percentage: float = 0.3,  # 30% of total position size
        # Take profit parameters
        tp1_rr_ratio: float = 1.5,  # Risk/Reward ratio for first take profit
        tp2_rr_ratio: float = 2.5,  # Risk/Reward ratio for second take profit
        # Risk management
        max_risk_per_trade: float = 0.01,  # 1% max risk per trade
        # Leverage parameters
        min_notional_size: float = 5.0,  # Minimum notional size in USDT
        max_leverage: int = 20,  # Maximum allowed leverage
        max_margin_allocation_percent: float = 0.25,  # Maximum percentage of balance to allocate as margin
    ):
        """
        Initialize the Scaled Entry/Exit strategy.

        Args:
            market_data: MarketDataCollector instance
            telegram_notifier: Optional TelegramNotifier instance for sending notifications
            macd_fast_period: Fast EMA period for MACD
            macd_slow_period: Slow EMA period for MACD
            macd_signal_period: Signal line period for MACD
            macd_histogram_threshold: Threshold for MACD histogram crossover
            rsi_period: RSI calculation period
            rsi_positive_momentum: Upper threshold for RSI positive momentum
            rsi_negative_momentum: Lower threshold for RSI negative momentum
            rsi_ema_period: Period for EMA calculation in RSI
            fibo_left_bars: Number of bars to look back for FiboBuLL PA
            fibo_right_bars: Number of bars to look forward for FiboBuLL PA
            tier1_size_percentage: Percentage of total position size for Tier 1 entry
            tier2_size_percentage: Percentage of total position size for Tier 2 entry
            tier3_size_percentage: Percentage of total position size for Tier 3 entry
            tp1_rr_ratio: Risk/Reward ratio for first take profit
            tp2_rr_ratio: Risk/Reward ratio for second take profit
            max_risk_per_trade: Maximum risk per trade as a percentage of account
            min_notional_size: Minimum notional size in USDT
            max_leverage: Maximum allowed leverage
            max_margin_allocation_percent: Maximum percentage of balance to allocate as margin
        """
        super().__init__("Scaled Entry/Exit Strategy", market_data)

        # Store Telegram notifier
        self.telegram_notifier = telegram_notifier

        # Initialize individual strategies
        self.macd_strategy = MACDStrategy(
            market_data=market_data,
            fast_period=macd_fast_period,
            slow_period=macd_slow_period,
            signal_period=macd_signal_period,
            histogram_threshold=macd_histogram_threshold,
        )

        self.rsi_strategy = RSIMiddleBandStrategy(
            market_data=market_data,
            period=rsi_period,
            positive_momentum=rsi_positive_momentum,
            negative_momentum=rsi_negative_momentum,
            ema_period=rsi_ema_period,
        )

        self.fibo_strategy = FibobullPAStrategy(
            market_data=market_data,
            left_bars=fibo_left_bars,
            right_bars=fibo_right_bars,
        )

        # Position sizing parameters
        self.tier1_size_percentage = tier1_size_percentage
        self.tier2_size_percentage = tier2_size_percentage
        self.tier3_size_percentage = tier3_size_percentage

        # Take profit parameters
        self.tp1_rr_ratio = tp1_rr_ratio
        self.tp2_rr_ratio = tp2_rr_ratio

        # Risk management parameters
        self.max_risk_per_trade = max_risk_per_trade

        # Leverage parameters
        self.min_notional_size = min_notional_size
        self.max_leverage = max_leverage
        self.max_margin_allocation_percent = max_margin_allocation_percent

        # Position state tracking
        self.position_state = {
            "direction": "NONE",  # "NONE", "LONG", or "SHORT"
            "tier1_entered": False,
            "tier2_entered": False,
            "tier3_entered": False,
            "tier1_exited": False,
            "tier2_exited": False,
            "tier3_exited": False,
            "entry_price": 0.0,
            "average_entry_price": 0.0,
            "stop_loss": 0.0,
            "position_size": 0.0,
            "tier1_size": 0.0,
            "tier2_size": 0.0,
            "tier3_size": 0.0,
            "leverage": 1,  # Default leverage
            "last_signal": None,
        }

        logger.info("Scaled Entry/Exit Strategy initialized")

    def get_macd_values(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Get MACD indicator values.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dictionary containing MACD values
        """
        signal = self.macd_strategy.generate_signal(symbol, timeframe)
        return {
            "macd": signal.get("macd", 0.0),
            "signal": signal.get("signal_line", 0.0),
            "hist": signal.get("histogram", 0.0),
            "rising_to_falling": signal.get("rising_to_falling", False),
            "falling_to_rising": signal.get("falling_to_rising", False),
        }

    def get_rsi_middle_band_values(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Get RSI Middle Band indicator values.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dictionary containing RSI Middle Band values
        """
        signal = self.rsi_strategy.generate_signal(symbol, timeframe)
        return {
            "rsi": signal.get("rsi", 0.0),
            "AL": signal.get("positive_momentum", False),  # Positive momentum
            "SAT": signal.get("negative_momentum", False),  # Negative momentum
            "is_long": signal.get("is_long", False),
            "is_short": signal.get("is_short", False),
        }

    def get_fibobull_pa_values(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Get FiboBuLL PA indicator values.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dictionary containing FiboBuLL PA values
        """
        signal = self.fibo_strategy.generate_signal(symbol, timeframe)
        return {
            "trend": signal.get("trend", 0),
            "long_signal": signal.get("signal", "") == "LONG",
            "short_signal": signal.get("signal", "") == "SHORT",
            "res": signal.get("resistance", 0.0),
            "sup": signal.get("support", 0.0),
            "patterns": signal.get("patterns", {}),
        }

    def calculate_dynamic_leverage(
        self, entry_price: float, stop_loss: float, account_balance: float
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate the dynamic leverage required for a trade based on risk parameters.

        Args:
            entry_price: Entry price for the position
            stop_loss: Stop loss price
            account_balance: Current account balance

        Returns:
            Tuple containing:
            - Integer representing the calculated leverage
            - Dictionary with leverage calculation details
        """
        # Calculate risk amount in currency
        risk_per_trade = account_balance * self.max_risk_per_trade

        # Calculate position size based on risk
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit == 0:
            logger.warning("Risk per unit is zero, using default position size")
            total_position_size = account_balance * 0.1  # Default to 10% of account
        else:
            total_position_size = risk_per_trade / risk_per_unit

        # Calculate notional size
        notional_size = total_position_size * entry_price

        # Check if notional size meets minimum requirement
        if notional_size < self.min_notional_size:
            logger.warning(
                f"Notional size ({notional_size} USDT) is below minimum requirement ({self.min_notional_size} USDT)"
            )

            # Send Telegram notification if notifier is available
            if self.telegram_notifier:
                self.telegram_notifier.notify_leverage_constraint(
                    symbol=self.market_data.get_current_symbol(),
                    reason="Notional size too small",
                    details={
                        "notional_size": notional_size,
                        "min_notional_size": self.min_notional_size,
                        "total_position_size": total_position_size,
                        "risk_amount": risk_per_trade,
                    },
                )

            return 0, {
                "error": "MIN_NOTIONAL_SIZE_NOT_MET",
                "notional_size": notional_size,
                "min_notional_size": self.min_notional_size,
                "total_position_size": total_position_size,
                "risk_amount": risk_per_trade,
            }

        # Calculate maximum margin allowed
        max_margin_allowed = account_balance * self.max_margin_allocation_percent

        # Calculate required leverage
        if max_margin_allowed <= 0:
            logger.warning("Maximum margin allowed is zero or negative")

            # Send Telegram notification if notifier is available
            if self.telegram_notifier:
                self.telegram_notifier.notify_leverage_constraint(
                    symbol=self.market_data.get_current_symbol(),
                    reason="Maximum margin allowed is zero or negative",
                    details={
                        "max_margin_allowed": max_margin_allowed,
                        "account_balance": account_balance,
                    },
                )

            return 0, {
                "error": "MAX_MARGIN_ALLOWED_ZERO",
                "max_margin_allowed": max_margin_allowed,
                "account_balance": account_balance,
            }

        required_leverage = math.ceil(notional_size / max_margin_allowed)

        # Ensure leverage is at least 1
        required_leverage = max(1, required_leverage)

        # Check if required leverage exceeds maximum allowed
        if required_leverage > self.max_leverage:
            logger.warning(
                f"Required leverage ({required_leverage}x) exceeds maximum allowed ({self.max_leverage}x)"
            )

            # Send Telegram notification if notifier is available
            if self.telegram_notifier:
                self.telegram_notifier.notify_leverage_constraint(
                    symbol=self.market_data.get_current_symbol(),
                    reason="Max leverage exceeded",
                    details={
                        "required_leverage": required_leverage,
                        "max_leverage": self.max_leverage,
                        "notional_size": notional_size,
                        "max_margin_allowed": max_margin_allowed,
                    },
                )

            return 0, {
                "error": "MAX_LEVERAGE_EXCEEDED",
                "required_leverage": required_leverage,
                "max_leverage": self.max_leverage,
                "notional_size": notional_size,
                "max_margin_allowed": max_margin_allowed,
            }

        # All checks passed, return the calculated leverage
        logger.info(
            f"Dynamic leverage calculated: {required_leverage}x for notional size {notional_size} USDT"
        )

        # Send Telegram notification if notifier is available
        if self.telegram_notifier:
            self.telegram_notifier.notify_leverage_calculation(
                symbol=self.market_data.get_current_symbol(),
                leverage=required_leverage,
                notional_size=notional_size,
                margin_required=notional_size / required_leverage,
                reason="New trade preparation",
            )

        return required_leverage, {
            "leverage": required_leverage,
            "notional_size": notional_size,
            "max_margin_allowed": max_margin_allowed,
            "total_position_size": total_position_size,
            "risk_amount": risk_per_trade,
        }

    def calculate_position_size(
        self, entry_price: float, stop_loss: float, account_balance: float
    ) -> Dict[str, float]:
        """
        Calculate position sizes for each tier based on risk management.

        Args:
            entry_price: Entry price for the position
            stop_loss: Stop loss price
            account_balance: Current account balance

        Returns:
            Dictionary containing position sizes for each tier
        """
        # Calculate dynamic leverage
        leverage, leverage_details = self.calculate_dynamic_leverage(
            entry_price, stop_loss, account_balance
        )

        # If leverage calculation failed, return empty position sizes
        if leverage == 0:
            logger.warning(
                f"Position sizing failed: {leverage_details.get('error', 'Unknown error')}"
            )
            return {
                "total_position_size": 0.0,
                "tier1_size": 0.0,
                "tier2_size": 0.0,
                "tier3_size": 0.0,
                "risk_amount": 0.0,
                "leverage": 0,
                "error": leverage_details.get("error", "Unknown error"),
                "details": leverage_details,
            }

        # Calculate risk amount in currency
        risk_per_trade = account_balance * self.max_risk_per_trade

        # Calculate position size based on risk
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit == 0:
            logger.warning("Risk per unit is zero, using default position size")
            total_position_size = account_balance * 0.1  # Default to 10% of account
        else:
            total_position_size = risk_per_trade / risk_per_unit

        # Calculate tier sizes
        tier1_size = total_position_size * self.tier1_size_percentage
        tier2_size = total_position_size * self.tier2_size_percentage
        tier3_size = total_position_size * self.tier3_size_percentage

        return {
            "total_position_size": total_position_size,
            "tier1_size": tier1_size,
            "tier2_size": tier2_size,
            "tier3_size": tier3_size,
            "risk_amount": risk_per_trade,
            "leverage": leverage,
            "notional_size": leverage_details.get("notional_size", 0.0),
        }

    def check_long_entry_conditions(
        self, symbol: str, timeframe: str
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Check conditions for long entry at different tiers.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Tuple containing:
            - Boolean indicating if entry conditions are met
            - Tier number (1, 2, or 3) for which conditions are met
            - Dictionary with entry details
        """
        # Get indicator values
        macd_values = self.get_macd_values(symbol, timeframe)
        rsi_values = self.get_rsi_middle_band_values(symbol, timeframe)
        fibo_values = self.get_fibobull_pa_values(symbol, timeframe)

        # Get current price
        current_price = self.market_data.get_current_price(symbol)

        # Check Tier 1 entry conditions
        if not self.position_state["tier1_entered"]:
            tier1_conditions = (
                fibo_values["long_signal"]
                and rsi_values["AL"]
                and macd_values["hist"] > 0
            )

            if tier1_conditions:
                # Send Telegram notification for indicator signal if notifier is available
                if self.telegram_notifier:
                    self.telegram_notifier.notify_indicator_signal(
                        symbol=symbol,
                        signal_type="LONG",
                        indicator_values={
                            "FiboBuLL PA": "Long",
                            "RSI": "AL",
                            "MACD Histogram": f"{macd_values['hist']:.4f}",
                            "Current Price": f"{current_price:.8f}",
                        },
                    )

                # Calculate stop loss (slightly below support)
                stop_loss = fibo_values["sup"] * 0.995  # 0.5% below support

                # Calculate position size
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, stop_loss, account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(f"Long entry skipped: {position_sizes['error']}")
                    return False, 0, {}

                # Store the leverage in the position state
                self.position_state["leverage"] = position_sizes["leverage"]

                return (
                    True,
                    1,
                    {
                        "entry_price": current_price,
                        "stop_loss": stop_loss,
                        "position_size": position_sizes["tier1_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        # Check Tier 2 entry conditions
        elif (
            self.position_state["tier1_entered"]
            and not self.position_state["tier2_entered"]
        ):
            # Check if price pulled back to resistance (now support) or made another breakout
            price_pullback = (
                current_price >= self.position_state["entry_price"] * 0.995
                and current_price <= self.position_state["entry_price"] * 1.02
                and rsi_values["AL"]
                and macd_values["hist"] > 0
            )

            price_breakout = (
                current_price > self.position_state["entry_price"] * 1.02
                and rsi_values["AL"]
                and macd_values["hist"] > 0
            )

            if price_pullback or price_breakout:
                # Calculate position size for tier 2
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, self.position_state["stop_loss"], account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(
                        f"Long tier 2 entry skipped: {position_sizes['error']}"
                    )
                    return False, 0, {}

                return (
                    True,
                    2,
                    {
                        "entry_price": current_price,
                        "stop_loss": self.position_state["stop_loss"],
                        "position_size": position_sizes["tier2_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        # Check Tier 3 entry conditions
        elif (
            self.position_state["tier2_entered"]
            and not self.position_state["tier3_entered"]
        ):
            # Check for new Higher High or significant breakout
            new_higher_high = (
                fibo_values["patterns"].get("higher_high", False)
                and rsi_values["AL"]
                and macd_values["hist"] > 0
            )

            significant_breakout = (
                current_price > self.position_state["entry_price"] * 1.05
                and rsi_values["AL"]
                and macd_values["hist"] > 0
            )

            if new_higher_high or significant_breakout:
                # Calculate position size for tier 3
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, self.position_state["stop_loss"], account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(
                        f"Long tier 3 entry skipped: {position_sizes['error']}"
                    )
                    return False, 0, {}

                return (
                    True,
                    3,
                    {
                        "entry_price": current_price,
                        "stop_loss": self.position_state["stop_loss"],
                        "position_size": position_sizes["tier3_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        return False, 0, {}

    def check_short_entry_conditions(
        self, symbol: str, timeframe: str
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Check conditions for short entry at different tiers.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Tuple containing:
            - Boolean indicating if entry conditions are met
            - Tier number (1, 2, or 3) for which conditions are met
            - Dictionary with entry details
        """
        # Get indicator values
        macd_values = self.get_macd_values(symbol, timeframe)
        rsi_values = self.get_rsi_middle_band_values(symbol, timeframe)
        fibo_values = self.get_fibobull_pa_values(symbol, timeframe)

        # Get current price
        current_price = self.market_data.get_current_price(symbol)

        # Check Tier 1 entry conditions
        if not self.position_state["tier1_entered"]:
            tier1_conditions = (
                fibo_values["short_signal"]
                and rsi_values["SAT"]
                and macd_values["hist"] < 0
            )

            if tier1_conditions:
                # Send Telegram notification for indicator signal if notifier is available
                if self.telegram_notifier:
                    self.telegram_notifier.notify_indicator_signal(
                        symbol=symbol,
                        signal_type="SHORT",
                        indicator_values={
                            "FiboBuLL PA": "Short",
                            "RSI": "SAT",
                            "MACD Histogram": f"{macd_values['hist']:.4f}",
                            "Current Price": f"{current_price:.8f}",
                        },
                    )

                # Calculate stop loss (slightly above resistance)
                stop_loss = fibo_values["res"] * 1.005  # 0.5% above resistance

                # Calculate position size
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, stop_loss, account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(f"Short entry skipped: {position_sizes['error']}")
                    return False, 0, {}

                # Store the leverage in the position state
                self.position_state["leverage"] = position_sizes["leverage"]

                return (
                    True,
                    1,
                    {
                        "entry_price": current_price,
                        "stop_loss": stop_loss,
                        "position_size": position_sizes["tier1_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        # Check Tier 2 entry conditions
        elif (
            self.position_state["tier1_entered"]
            and not self.position_state["tier2_entered"]
        ):
            # Check if price pulled back to support (now resistance) or made another breakdown
            price_pullback = (
                current_price <= self.position_state["entry_price"] * 1.005
                and current_price >= self.position_state["entry_price"] * 0.98
                and rsi_values["SAT"]
                and macd_values["hist"] < 0
            )

            price_breakdown = (
                current_price < self.position_state["entry_price"] * 0.98
                and rsi_values["SAT"]
                and macd_values["hist"] < 0
            )

            if price_pullback or price_breakdown:
                # Calculate position size for tier 2
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, self.position_state["stop_loss"], account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(
                        f"Short tier 2 entry skipped: {position_sizes['error']}"
                    )
                    return False, 0, {}

                return (
                    True,
                    2,
                    {
                        "entry_price": current_price,
                        "stop_loss": self.position_state["stop_loss"],
                        "position_size": position_sizes["tier2_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        # Check Tier 3 entry conditions
        elif (
            self.position_state["tier2_entered"]
            and not self.position_state["tier3_entered"]
        ):
            # Check for new Lower Low or significant breakdown
            new_lower_low = (
                fibo_values["patterns"].get("lower_low", False)
                and rsi_values["SAT"]
                and macd_values["hist"] < 0
            )

            significant_breakdown = (
                current_price < self.position_state["entry_price"] * 0.95
                and rsi_values["SAT"]
                and macd_values["hist"] < 0
            )

            if new_lower_low or significant_breakdown:
                # Calculate position size for tier 3
                account_balance = (
                    10000  # This should be fetched from the account manager
                )
                position_sizes = self.calculate_position_size(
                    current_price, self.position_state["stop_loss"], account_balance
                )

                # Check if position sizing failed due to leverage constraints
                if "error" in position_sizes:
                    logger.warning(
                        f"Short tier 3 entry skipped: {position_sizes['error']}"
                    )
                    return False, 0, {}

                return (
                    True,
                    3,
                    {
                        "entry_price": current_price,
                        "stop_loss": self.position_state["stop_loss"],
                        "position_size": position_sizes["tier3_size"],
                        "total_position_size": position_sizes["total_position_size"],
                        "risk_amount": position_sizes["risk_amount"],
                        "leverage": position_sizes["leverage"],
                        "notional_size": position_sizes["notional_size"],
                    },
                )

        return False, 0, {}

    def check_long_exit_conditions(
        self, symbol: str, timeframe: str
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Check conditions for long exit at different tiers.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Tuple containing:
            - Boolean indicating if exit conditions are met
            - Tier number (1, 2, or 3) for which conditions are met
            - Dictionary with exit details
        """
        # Get indicator values
        macd_values = self.get_macd_values(symbol, timeframe)
        rsi_values = self.get_rsi_middle_band_values(symbol, timeframe)
        fibo_values = self.get_fibobull_pa_values(symbol, timeframe)

        # Get current price
        current_price = self.market_data.get_current_price(symbol)

        # Calculate profit/loss
        if self.position_state["direction"] == "LONG":
            pnl = (
                current_price - self.position_state["average_entry_price"]
            ) / self.position_state["average_entry_price"]
            risk = (
                self.position_state["average_entry_price"]
                - self.position_state["stop_loss"]
            ) / self.position_state["average_entry_price"]
            rr_ratio = pnl / risk if risk > 0 else 0
        else:
            return False, 0, {}

        # Check Tier 1 exit conditions
        if (
            self.position_state["tier1_entered"]
            and not self.position_state["tier1_exited"]
        ):
            # Check for R/R target, approaching resistance, or MACD histogram peak
            rr_target_reached = rr_ratio >= self.tp1_rr_ratio
            approaching_resistance = current_price >= fibo_values["res"] * 0.995
            macd_hist_peak = (
                macd_values["hist"] > 0
                and macd_values["falling_to_rising"] == False
                and macd_values["rising_to_falling"] == False
            )

            if rr_target_reached or approaching_resistance or macd_hist_peak:
                return (
                    True,
                    1,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier1_size"],
                        "new_stop_loss": self.position_state[
                            "average_entry_price"
                        ],  # Move to break-even
                    },
                )

        # Check Tier 2 exit conditions
        elif (
            self.position_state["tier1_exited"]
            and not self.position_state["tier2_exited"]
        ):
            # Check for higher R/R target, RSI losing momentum, or MACD approaching zero
            higher_rr_target_reached = rr_ratio >= self.tp2_rr_ratio
            rsi_losing_momentum = not rsi_values["AL"]
            macd_approaching_zero = (
                macd_values["hist"] > 0
                and macd_values["hist"] < macd_values["hist"] * 0.5
            )

            if higher_rr_target_reached or rsi_losing_momentum or macd_approaching_zero:
                return (
                    True,
                    2,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier2_size"]
                        + self.position_state["tier3_size"],
                        "new_stop_loss": current_price
                        * 0.99,  # Set trailing stop 1% below current price
                        "activate_trailing_stop": True,
                    },
                )

        # Check Tier 3 exit conditions (full exit)
        elif (
            self.position_state["tier2_exited"]
            and not self.position_state["tier3_exited"]
        ):
            # Check for full exit signals
            macd_negative = macd_values["hist"] < 0
            rsi_negative_momentum = rsi_values["SAT"]
            fibo_short_signal = fibo_values["short_signal"]

            if macd_negative or rsi_negative_momentum or fibo_short_signal:
                return (
                    True,
                    3,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier3_size"],
                        "full_exit": True,
                    },
                )

        return False, 0, {}

    def check_short_exit_conditions(
        self, symbol: str, timeframe: str
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Check conditions for short exit at different tiers.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Tuple containing:
            - Boolean indicating if exit conditions are met
            - Tier number (1, 2, or 3) for which conditions are met
            - Dictionary with exit details
        """
        # Get indicator values
        macd_values = self.get_macd_values(symbol, timeframe)
        rsi_values = self.get_rsi_middle_band_values(symbol, timeframe)
        fibo_values = self.get_fibobull_pa_values(symbol, timeframe)

        # Get current price
        current_price = self.market_data.get_current_price(symbol)

        # Calculate profit/loss
        if self.position_state["direction"] == "SHORT":
            pnl = (
                self.position_state["average_entry_price"] - current_price
            ) / self.position_state["average_entry_price"]
            risk = (
                self.position_state["stop_loss"]
                - self.position_state["average_entry_price"]
            ) / self.position_state["average_entry_price"]
            rr_ratio = pnl / risk if risk > 0 else 0
        else:
            return False, 0, {}

        # Check Tier 1 exit conditions
        if (
            self.position_state["tier1_entered"]
            and not self.position_state["tier1_exited"]
        ):
            # Check for R/R target, approaching support, or MACD histogram trough
            rr_target_reached = rr_ratio >= self.tp1_rr_ratio
            approaching_support = current_price <= fibo_values["sup"] * 1.005
            macd_hist_trough = (
                macd_values["hist"] < 0
                and macd_values["falling_to_rising"] == False
                and macd_values["rising_to_falling"] == False
            )

            if rr_target_reached or approaching_support or macd_hist_trough:
                return (
                    True,
                    1,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier1_size"],
                        "new_stop_loss": self.position_state[
                            "average_entry_price"
                        ],  # Move to break-even
                    },
                )

        # Check Tier 2 exit conditions
        elif (
            self.position_state["tier1_exited"]
            and not self.position_state["tier2_exited"]
        ):
            # Check for higher R/R target, RSI losing momentum, or MACD approaching zero
            higher_rr_target_reached = rr_ratio >= self.tp2_rr_ratio
            rsi_losing_momentum = not rsi_values["SAT"]
            macd_approaching_zero = (
                macd_values["hist"] < 0
                and macd_values["hist"] > macd_values["hist"] * 0.5
            )

            if higher_rr_target_reached or rsi_losing_momentum or macd_approaching_zero:
                return (
                    True,
                    2,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier2_size"]
                        + self.position_state["tier3_size"],
                        "new_stop_loss": current_price
                        * 1.01,  # Set trailing stop 1% above current price
                        "activate_trailing_stop": True,
                    },
                )

        # Check Tier 3 exit conditions (full exit)
        elif (
            self.position_state["tier2_exited"]
            and not self.position_state["tier3_exited"]
        ):
            # Check for full exit signals
            macd_positive = macd_values["hist"] > 0
            rsi_positive_momentum = rsi_values["AL"]
            fibo_long_signal = fibo_values["long_signal"]

            if macd_positive or rsi_positive_momentum or fibo_long_signal:
                return (
                    True,
                    3,
                    {
                        "exit_price": current_price,
                        "exit_size": self.position_state["tier3_size"],
                        "full_exit": True,
                    },
                )

        return False, 0, {}

    def update_position_state(
        self, entry: bool, tier: int, details: Dict[str, Any]
    ) -> None:
        """
        Update the position state based on entry or exit.

        Args:
            entry: True if this is an entry, False if this is an exit
            tier: Tier number (1, 2, or 3)
            details: Dictionary with entry or exit details
        """
        if entry:
            if tier == 1:
                self.position_state["tier1_entered"] = True
                self.position_state["entry_price"] = details["entry_price"]
                self.position_state["average_entry_price"] = details["entry_price"]
                self.position_state["stop_loss"] = details["stop_loss"]
                self.position_state["position_size"] = details["position_size"]
                self.position_state["tier1_size"] = details["position_size"]
                self.position_state["risk_amount"] = details["risk_amount"]

                # Send Telegram notification for Tier 1 entry if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    self.telegram_notifier.notify_scaled_entry(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        tier=1,
                        entry_price=details["entry_price"],
                        position_size=details["position_size"],
                        total_position_size=details["total_position_size"],
                        leverage=details["leverage"],
                        stop_loss=details["stop_loss"],
                    )

            elif tier == 2:
                self.position_state["tier2_entered"] = True
                # Update average entry price
                total_size = (
                    self.position_state["tier1_size"] + details["position_size"]
                )
                self.position_state["average_entry_price"] = (
                    self.position_state["entry_price"]
                    * self.position_state["tier1_size"]
                    + details["entry_price"] * details["position_size"]
                ) / total_size
                self.position_state["position_size"] += details["position_size"]
                self.position_state["tier2_size"] = details["position_size"]

                # Send Telegram notification for Tier 2 entry if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    self.telegram_notifier.notify_scaled_entry(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        tier=2,
                        entry_price=details["entry_price"],
                        position_size=details["position_size"],
                        total_position_size=self.position_state["position_size"],
                        leverage=details["leverage"],
                        stop_loss=details["stop_loss"],
                    )

            elif tier == 3:
                self.position_state["tier3_entered"] = True
                # Update average entry price
                total_size = (
                    self.position_state["tier1_size"]
                    + self.position_state["tier2_size"]
                    + details["position_size"]
                )
                self.position_state["average_entry_price"] = (
                    self.position_state["entry_price"]
                    * self.position_state["tier1_size"]
                    + self.position_state["entry_price"]
                    * self.position_state["tier2_size"]
                    + details["entry_price"] * details["position_size"]
                ) / total_size
                self.position_state["position_size"] += details["position_size"]
                self.position_state["tier3_size"] = details["position_size"]

                # Send Telegram notification for Tier 3 entry if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    self.telegram_notifier.notify_scaled_entry(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        tier=3,
                        entry_price=details["entry_price"],
                        position_size=details["position_size"],
                        total_position_size=self.position_state["position_size"],
                        leverage=details["leverage"],
                        stop_loss=details["stop_loss"],
                    )

        else:  # Exit
            if tier == 1:
                self.position_state["tier1_exited"] = True
                self.position_state["stop_loss"] = details["new_stop_loss"]

                # Send Telegram notification for Tier 1 exit if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    # Calculate PnL
                    entry_price = self.position_state["average_entry_price"]
                    exit_price = details["exit_price"]
                    position_size = details["exit_size"]

                    if trade_type == "LONG":
                        pnl = (exit_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - exit_price) * position_size

                    pnl_percentage = (pnl / (entry_price * position_size)) * 100

                    self.telegram_notifier.notify_scaled_exit(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        tier=1,
                        exit_price=exit_price,
                        closed_size=position_size,
                        pnl=pnl,
                        pnl_percentage=pnl_percentage,
                    )

            elif tier == 2:
                self.position_state["tier2_exited"] = True
                self.position_state["stop_loss"] = details["new_stop_loss"]
                if details.get("activate_trailing_stop", False):
                    self.position_state["trailing_stop_activated"] = True

                # Send Telegram notification for Tier 2 exit if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    # Calculate PnL
                    entry_price = self.position_state["average_entry_price"]
                    exit_price = details["exit_price"]
                    position_size = details["exit_size"]

                    if trade_type == "LONG":
                        pnl = (exit_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - exit_price) * position_size

                    pnl_percentage = (pnl / (entry_price * position_size)) * 100

                    self.telegram_notifier.notify_scaled_exit(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        tier=2,
                        exit_price=exit_price,
                        closed_size=position_size,
                        pnl=pnl,
                        pnl_percentage=pnl_percentage,
                    )

                    # Also notify about stop loss adjustment
                    self.telegram_notifier.notify_stop_loss_adjusted(
                        symbol=self.market_data.get_current_symbol(),
                        new_stop_loss=details["new_stop_loss"],
                        reason="Trailing stop activated",
                    )

            elif tier == 3:
                self.position_state["tier3_exited"] = True
                # Reset position state

                # Send Telegram notification for final exit if notifier is available
                if self.telegram_notifier:
                    trade_type = (
                        "LONG"
                        if self.position_state["direction"] == "LONG"
                        else "SHORT"
                    )
                    # Calculate PnL
                    entry_price = self.position_state["average_entry_price"]
                    exit_price = details["exit_price"]
                    position_size = details["exit_size"]

                    if trade_type == "LONG":
                        pnl = (exit_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - exit_price) * position_size

                    pnl_percentage = (pnl / (entry_price * position_size)) * 100

                    # Determine exit reason
                    exit_reason = "Strategy signal"
                    if "macd_negative" in details and details["macd_negative"]:
                        exit_reason = "MACD turned negative"
                    elif (
                        "rsi_negative_momentum" in details
                        and details["rsi_negative_momentum"]
                    ):
                        exit_reason = "RSI lost momentum"
                    elif (
                        "fibo_short_signal" in details and details["fibo_short_signal"]
                    ):
                        exit_reason = "FiboBuLL PA short signal"

                    self.telegram_notifier.notify_final_exit(
                        symbol=self.market_data.get_current_symbol(),
                        trade_type=trade_type,
                        exit_price=exit_price,
                        closed_size=position_size,
                        pnl=pnl,
                        pnl_percentage=pnl_percentage,
                        reason=exit_reason,
                    )

                # Reset position state
                self.position_state = {
                    "direction": "NONE",
                    "tier1_entered": False,
                    "tier2_entered": False,
                    "tier3_entered": False,
                    "tier1_exited": False,
                    "tier2_exited": False,
                    "tier3_exited": False,
                    "entry_price": 0.0,
                    "average_entry_price": 0.0,
                    "stop_loss": 0.0,
                    "position_size": 0.0,
                    "tier1_size": 0.0,
                    "tier2_size": 0.0,
                    "tier3_size": 0.0,
                    "leverage": 1,  # Default leverage
                    "last_signal": self.position_state["last_signal"],
                }

    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generate trading signal based on the scaled entry/exit strategy.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis

        Returns:
            Dictionary containing signal details
        """
        try:
            # Check for long entry conditions first
            long_entry, tier, entry_details = self.check_long_entry_conditions(
                symbol, timeframe
            )

            if long_entry:
                # Update position state
                self.update_position_state(True, tier, entry_details)

                # Generate signal with leverage information
                signal = {
                    "action": "BUY",
                    "tier": tier,
                    "strength": (
                        "STRONG" if tier == 1 else "MEDIUM" if tier == 2 else "WEAK"
                    ),
                    "entry_price": entry_details["entry_price"],
                    "stop_loss": entry_details["stop_loss"],
                    "position_size": entry_details["position_size"],
                    "total_position_size": entry_details["total_position_size"],
                    "risk_amount": entry_details["risk_amount"],
                    "leverage": entry_details["leverage"],
                    "notional_size": entry_details["notional_size"],
                    "leverage_details": {
                        "required_leverage": entry_details["leverage"],
                        "notional_size": entry_details["notional_size"],
                        "margin_required": entry_details["notional_size"]
                        / entry_details["leverage"],
                        "risk_per_unit": entry_details["risk_amount"]
                        / entry_details["position_size"],
                    },
                }

                self.last_signal = signal
                return signal

            # Check for short entry conditions
            short_entry, tier, entry_details = self.check_short_entry_conditions(
                symbol, timeframe
            )

            if short_entry:
                # Update position state
                self.update_position_state(True, tier, entry_details)

                # Generate signal with leverage information
                signal = {
                    "action": "SELL",
                    "tier": tier,
                    "strength": (
                        "STRONG" if tier == 1 else "MEDIUM" if tier == 2 else "WEAK"
                    ),
                    "entry_price": entry_details["entry_price"],
                    "stop_loss": entry_details["stop_loss"],
                    "position_size": entry_details["position_size"],
                    "total_position_size": entry_details["total_position_size"],
                    "risk_amount": entry_details["risk_amount"],
                    "leverage": entry_details["leverage"],
                    "notional_size": entry_details["notional_size"],
                    "leverage_details": {
                        "required_leverage": entry_details["leverage"],
                        "notional_size": entry_details["notional_size"],
                        "margin_required": entry_details["notional_size"]
                        / entry_details["leverage"],
                        "risk_per_unit": entry_details["risk_amount"]
                        / entry_details["position_size"],
                    },
                }

                self.last_signal = signal
                return signal

            # Check for exit conditions if in a position
            if self.position_state["direction"] != "NONE":
                exit_signal = self.check_exit_conditions(symbol, timeframe)
                if exit_signal:
                    self.last_signal = exit_signal
                    return exit_signal

            # No signal generated
            return {
                "action": "HOLD",
                "strength": "NONE",
                "leverage": self.position_state.get("leverage", 1),
                "notional_size": self.position_state.get("notional_size", 0),
            }

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            return {"action": "ERROR", "strength": "NONE", "error": str(e)}

    def get_last_signal(self) -> Dict[str, Any]:
        """
        Get the last generated signal.

        Returns:
            Dict containing the last signal information
        """
        return self.last_signal
