import pandas as pd

NASDAQ_TICKERS_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_TICKERS_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def load_us_tickers() -> set[str]:
    """Load all major US market tickers from nasdaqtrader.com.
    
        Returns:
            Set of all valid tickers.
    """
    nasdaq = pd.read_csv(NASDAQ_TICKERS_URL, sep="|")
    other = pd.read_csv(OTHER_TICKERS_URL, sep="|")
    nasTickers = nasdaq.iloc[:,[0]]
    otherTickers = other.iloc[:,[0]]
    nasTickers.columns = otherTickers.columns

    allTickers = pd.concat([nasTickers, otherTickers], ignore_index=True)

    return set(allTickers["ACT Symbol"])


US_MARKET_TICKERS = load_us_tickers()


def is_valid_ticker(symbol: str) -> bool:
    """Check if a ticker is valid on major US Markets.

        Args:
            symbol: Ticker to be validated.

        Returns:
            If ticker was validated.
    """
    return symbol.upper() in US_MARKET_TICKERS


def time_to_next_position_update() -> tuple[float, str]:
    """Gets amount of time for ACORN to sleep until the next position update window
        currently using market open, noon, and eod.

        Returns:
            Tuple containing seconds till the next event and the name of the event
            'open', 'noon', or 'eod'.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    nowEst = datetime.now(ZoneInfo("America/New_York"))
    day = nowEst.weekday()
    targetOpen = nowEst.replace(hour=9, minute=30,  second=1, microsecond=0)
    targetNoon = nowEst.replace(hour=12, minute=45, second=0, microsecond=0)
    targetEod = nowEst.replace(hour=16, minute=0, second=0, microsecond=0)
    if day > 4:
        nextDay = targetOpen + timedelta(days=1)
        return (nextDay - nowEst).total_seconds(), "open"
    if nowEst < targetOpen:
        return (targetOpen - nowEst).total_seconds(), "open"
    elif nowEst < targetNoon:
        return (targetNoon - nowEst).total_seconds(), "noon"
    elif nowEst < targetEod:
        return (targetEod - nowEst).total_seconds(), "eod"
    else:
        nextOpen = targetOpen + timedelta(days=1)
        return (nextOpen - nowEst).total_seconds(), "open"