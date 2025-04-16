from typing import Dict, Any
from src.errors import InsufficientDataError

class BollingerBandsStrategy:
    def generate_signal(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Verilen sembol ve zaman dilimi için trading sinyali üretir.
        
        Args:
            symbol: Trading sembolü (örn. "DOGEUSDT")
            timeframe: Zaman dilimi (örn. "15m", "1h", "4h", "1d")
            
        Returns:
            Dict[str, Any]: Sinyal bilgilerini içeren sözlük
            
        Raises:
            InsufficientDataError: Yeterli veri yoksa
        """
        try:
            # Tarihsel verileri al - use fresh data
            df = self.market_data.get_historical_data(symbol, timeframe, use_cache=False)
            
            if df.empty or len(df) < self.min_bars:
                raise InsufficientDataError(
                    f"{symbol} için yeterli veri yok. En az {self.min_bars} bar gerekli."
                )
            # ... existing code ...
        except Exception as e:
            # ... existing code ...
            raise 