"""
Fundamentals Service — fetches EPS, P/E, Book Value from Yahoo Finance
"""

import logging
import time
from typing import Dict, Any
import yfinance as yf

logger = logging.getLogger(__name__)


class FundamentalsService:
    """Fetches fundamental financial metrics from Yahoo Finance via yfinance."""

    def __init__(self) -> None:
        # Cache Yahoo info payloads to reduce repeated network calls.
        self._info_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 60 * 60 * 6  # 6 hours

    def _get_cached_info(self, yahoo_symbol: str) -> Dict[str, Any]:
        now = time.time()
        cached = self._info_cache.get(yahoo_symbol)
        if cached and cached.get("expires_at", 0) > now:
            return cached.get("info", {})

        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info or {}
        self._info_cache[yahoo_symbol] = {
            "info": info,
            "expires_at": now + self._cache_ttl_seconds,
        }
        return info

    def get_fundamentals(self, symbol: str, exchange_code: str = "N") -> Dict[str, Any]:
        """
        Fetch fundamental metrics (P/E, EPS, Book Value, Market Cap) for a stock.
        
        Args:
            symbol: NSE/BSE stock symbol (e.g., 'RELIANCE')
            exchange_code: 'N' for NSE, 'B' for BSE (default: 'N')
            
        Returns:
            Dict with keys:
              - symbol: Input symbol
              - pe_ratio: Trailing P/E (float or None)
              - forward_pe: Forward P/E (float or None)
              - eps: Trailing EPS (float or None)
              - book_value: Book value per share (float or None)
              - market_cap: Market cap in INR (float or None)
              - source: 'Yahoo Finance'
              - error: Error message if fetch failed (None if successful)
        """
        try:
            # Build Yahoo ticker symbol (e.g., RELIANCE.NS or RELIANCE.BO)
            yahoo_symbol = self._build_yahoo_symbol(symbol, exchange_code)
            logger.info(f"[FUNDAMENTALS] Fetching for {symbol} → {yahoo_symbol}")
            
            # Fetch ticker info
            info = self._get_cached_info(yahoo_symbol)
            
            if not info:
                logger.warning(f"[FUNDAMENTALS] Empty info dict for {yahoo_symbol}")
                return self._error_response(symbol, "No data found on Yahoo Finance")
            
            # Extract fundamentals
            result = {
                "symbol": symbol,
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "eps": info.get("trailingEps"),
                "book_value": info.get("bookValue"),
                "market_cap": info.get("marketCap"),
                "source": "Yahoo Finance",
                "error": None,
            }
            
            logger.info(f"[FUNDAMENTALS] Success for {symbol}: PE={result['pe_ratio']}, "
                       f"EPS={result['eps']}, BV={result['book_value']}")
            return result
            
        except Exception as exc:
            logger.warning(f"[FUNDAMENTALS] Exception for {symbol}: {exc}")
            return self._error_response(symbol, str(exc))

    def get_sector_classification(self, symbol: str, exchange_code: str = "N") -> Dict[str, Any]:
        """
        Fetch sector/industry classification for a stock from Yahoo Finance.

        Returns keys:
          - symbol
          - sector
          - industry
          - source
          - error
        """
        try:
            yahoo_symbol = self._build_yahoo_symbol(symbol, exchange_code)
            info = self._get_cached_info(yahoo_symbol)

            sector = info.get("sector")
            industry = info.get("industry")
            if not sector and not industry:
                return {
                    "symbol": symbol,
                    "sector": None,
                    "industry": None,
                    "source": "Yahoo Finance",
                    "error": "Sector data unavailable",
                }

            return {
                "symbol": symbol,
                "sector": sector,
                "industry": industry,
                "source": "Yahoo Finance",
                "error": None,
            }
        except Exception as exc:
            logger.warning(f"[FUNDAMENTALS] Sector fetch failed for {symbol}: {exc}")
            return {
                "symbol": symbol,
                "sector": None,
                "industry": None,
                "source": "Yahoo Finance",
                "error": str(exc),
            }

    def _build_yahoo_symbol(self, symbol: str, exchange_code: str) -> str:
        """
        Convert NSE/BSE symbol to Yahoo Finance format.
        NSE uses .NS, BSE uses .BO suffix.
        """
        exchange_code = exchange_code.upper()
        suffix = ".NS" if exchange_code == "N" else ".BO"
        return f"{symbol}{suffix}"

    def _error_response(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """Build a standardized error response."""
        return {
            "symbol": symbol,
            "pe_ratio": None,
            "forward_pe": None,
            "eps": None,
            "book_value": None,
            "market_cap": None,
            "source": "Yahoo Finance",
            "error": error_msg,
        }


# Create singleton instance
fundamentals_service = FundamentalsService()
