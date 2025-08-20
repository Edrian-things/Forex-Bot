import MetaTrader5 as mt5
import pandas as pd
import ta
from datetime import datetime, time, timezone, timedelta
import time as t

# Constants
SYMBOLS = ["EURUSD", "GOLD"]  # Replace GOLD for XAUUSD as per your MT5 symbol
LOT_SIZE = 0.01
TP_PIPS = 20
SL_PIPS = 10

# Philippine Timezone UTC+8
PHT = timezone(timedelta(hours=8))

def is_in_trading_session():
    now = datetime.now(PHT).time()
    session_start = time(15, 0)  # 3:00 PM PHT
    session_end = time(23, 59, 59)  # Just before midnight
    return session_start <= now <= session_end

def get_data(symbol, timeframe=mt5.TIMEFRAME_M15, n=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def add_indicators(df):
    df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    return df

def check_signal(df):
    # Use last row indicators
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Buy signal: EMA fast crosses above EMA slow, RSI < 70, MACD crosses above signal
    buy_signal = (
        prev['ema_fast'] < prev['ema_slow'] and
        last['ema_fast'] > last['ema_slow'] and
        last['rsi'] < 70 and
        prev['macd'] < prev['macd_signal'] and
        last['macd'] > last['macd_signal']
    )

    # Sell signal: EMA fast crosses below EMA slow, RSI > 30, MACD crosses below signal
    sell_signal = (
        prev['ema_fast'] > prev['ema_slow'] and
        last['ema_fast'] < last['ema_slow'] and
        last['rsi'] > 30 and
        prev['macd'] > prev['macd_signal'] and
        last['macd'] < last['macd_signal']
    )

    if buy_signal:
        return "BUY"
    elif sell_signal:
        return "SELL"
    else:
        return None

def place_order(symbol, order_type):
    price = mt5.symbol_info_tick(symbol).ask if order_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    deviation = 10

    point = mt5.symbol_info(symbol).point
    sl = price - SL_PIPS * point if order_type == "BUY" else price + SL_PIPS * point
    tp = price + TP_PIPS * point if order_type == "BUY" else price - TP_PIPS * point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": deviation,
        "magic": 123456,
        "comment": "Ultimate Forex Bot v4",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to place {order_type} order for {symbol}: {result.comment}")
    else:
        print(f"{order_type} order placed for {symbol} at {price:.5f} with TP {tp:.5f} and SL {sl:.5f}")

def main():
    if not mt5.initialize():
        print("MT5 initialize() failed")
        return

    print("MT5 initialized successfully.")
    print("Ultimate Forex Bot v4 running...")

    while True:
        if is_in_trading_session():
            print("[Session] Inside trading session")
            for symbol in SYMBOLS:
                df = get_data(symbol)
                if df is None:
                    print(f"[{symbol}] No data retrieved.")
                    continue

                df = add_indicators(df)
                signal = check_signal(df)

                if signal:
                    print(f"[{symbol}] {signal} signal detected!")
                    place_order(symbol, signal)
                else:
                    print(f"[{symbol}] No signal - conditions not met")

        else:
            print("[Session] Outside trading session - waiting...")

        t.sleep(60)  # Wait 1 minute before next check

if __name__ == "__main__":
    main()
