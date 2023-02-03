import time
from turtle import end_fill

from numpy import tri
import pyupbit
import datetime
import schedule
from fbprophet import Prophet

access = "your-access"
secret = "your-secret"
tickers = pyupbit.get_tickers(fiat="KRW")
ascents = []
ror = []

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = pyupbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

predicted_close_price = 0
def predict_price(ticker):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    currentValue = pyupbit.get_current_price(ticker)
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
    ascents.append(round(closeValue))
    ror.append((closeValue - currentValue)/currentValue * 100)
    return round(closeValue)

def get_volatility(ticker):
    """변동성 높았던 날 return"""
    df = pyupbit.get_ohlcv(ticker, count = 365)
    if df is not None:
        rors = (df['high'] - df['open']) / df['open'] * 100
    else:
        rors = [0]
    vol = 0
    for ror in rors:
        if ror >=30:
            vol += 1
    print(ticker, vol)
    return ticker, vol

def get_accumulation(ticker):
    '''기관 매집 흔적'''
    df = pyupbit.get_ohlcv(ticker, count = 365)
    flag_inverted_hammer = False
    num_inverted_hammer = 0
    num_accumulation = 0
    flag_dip = False
    flag_rise = False
    pre_volume = 100000000
    rise = 0.0
    dates = []

    for day in df.itertuples():
        open = day.open
        high = day.high
        low = day.low
        close = day.close
        volume = day.volume
        tail = high - close
        body = close - open
        ror = (high - open)/open * 100
        date = day.Index
        if not body == 0:
            ratio = tail/body
        else:
            ratio = 0
        volume_ratio = volume / pre_volume
        if low == open and ratio > 0.25 and volume_ratio > 3 and not flag_inverted_hammer: #매집봉 탐색
            flag_inverted_hammer = True
            mid_inverted_hammer = (close + low)/2
            low_inverted_hammer = low
            high_inverted_hammer = high
            close_inverted_hammer = close
            volume_inverted_hammer = volume
            date_inverted_hammer = day.Index
            num_dip = 0
            num_day = 0
            num_inverted_hammer += 1

        if flag_inverted_hammer == True: #박스권 형성 여부 탐색
            num_day += 1
            if low < mid_inverted_hammer:
                flag_dip = True
            
            if close < low_inverted_hammer:
                num_dip += 1

            if high > close_inverted_hammer and flag_dip == True and ror > 15 and num_day > 2: #돌파
                flag_rise = True
            
            if num_dip > 4:
                flag_inverted_hammer = False
        
        if flag_inverted_hammer == True and flag_rise == True and flag_dip == True:
            num_accumulation += 1
            dates.append(str(date_inverted_hammer) + " ~ " + str(date))
            flag_inverted_hammer = False
            flag_rise = False
            flag_dip = False
            rise += (high - mid_inverted_hammer)/mid_inverted_hammer * 100
            num_day = 0
        pre_volume = volume
    print(ticker, num_accumulation, dates)
    print(num_accumulation, num_inverted_hammer, rise)
    return num_accumulation, num_inverted_hammer, rise

v = 0
tick = ""
success = 0
trial = 0
rises = []
for ticker in tickers:
    acc, h, r = get_accumulation(ticker) # get_accumulation(ticker) #get_volatility(ticker)
    success += acc
    trial += h
    if r > 0.0:
        rises.append(r) 

    if v < acc:
        v = acc
        tick = ticker
print(tick, v)
print(success/trial * 100, sum(rises)/success, max(rises), min(rises))
print(rises)