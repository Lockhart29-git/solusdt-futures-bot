import ccxt
import time
import pandas as pd
import ta

# Bybit API credentials (replace with your own)
API_KEY = 'YOUR_BYBIT_API_KEY'
API_SECRET = 'YOUR_BYBIT_SECRET'

exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

symbol = 'SOL/USDT'
leverage = 3
rsi_threshold = 35
tp_percent = 0.15  # 15% profit target
sl_percent = 0.08  # 8% stop-loss
timeframe = '15m'

def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['avg_volume'] = df['volume'].rolling(10).mean()
    df['vol_spike'] = df['volume'] > df['avg_volume'] * 1.5
    return df

def get_balance():
    balance = exchange.fetch_balance()
    return balance['total']['USDT']

def check_conditions(df):
    last = df.iloc[-1]
    near_support = last['low'] <= df['low'].rolling(20).min().iloc[-1] * 1.02
    rsi_ok = last['rsi'] < rsi_threshold
    volume_ok = last['vol_spike']
    fakeout = last['rsi'] < 20 and not volume_ok
    return rsi_ok and volume_ok and near_support and not fakeout

def place_trade(usdt_balance, price):
    amount = (usdt_balance * leverage) / price
    exchange.set_leverage(leverage, symbol)
    order = exchange.create_market_buy_order(symbol, amount)
    print("Trade Placed:", order)
    return order, amount

def monitor_trade(entry_price, amount, usdt_balance):
    tp_price = entry_price * (1 + tp_percent / leverage)
    sl_price = entry_price * (1 - sl_percent / leverage)
    print(f"TP: {tp_price}, SL: {sl_price}")

    while True:
        ticker = exchange.fetch_ticker(symbol)
        last_price = ticker['last']
        if last_price >= tp_price:
            exchange.create_market_sell_order(symbol, amount)
            print("TP Hit: Trade Closed")
            break
        elif last_price <= sl_price:
            exchange.create_market_sell_order(symbol, amount)
            print("SL Hit: Trade Closed")
            break
        time.sleep(60)

def run_bot():
    df = fetch_data()
    if not check_conditions(df):
        print("Conditions not met")
        return
    price = df.iloc[-1]['close']
    usdt_balance = get_balance()
    order, amount = place_trade(usdt_balance, price)
    monitor_trade(price, amount, usdt_balance)

if __name__ == "__main__":
    run_bot()
