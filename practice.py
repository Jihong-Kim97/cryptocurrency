import pyupbit
# print(pyupbit.get_tickers(fiat="KRW"))

tickers = []
for ticker in pyupbit.get_tickers(fiat="KRW"):
    ticker = '"'+ticker+'",'
    print(ticker)
    ticker = ticker[4:]
    tickers.append(ticker)

# print(tickers)
# print(pyupbit.get_current_price(["KRW-BTC", "KRW-ADA"]))
# df_btc = pyupbit.get_ohlcv("KRW-BTC",interval="minute60", count=10)
# print(df_btc)
# df_eth = pyupbit.get_ohlcv("KRW-ETH",interval="minute60", count=10)
# print(df_eth)
# print(pyupbit.get_ohlcv("KRW-BTC", interval="minute1",count=10, to="20201010"))
# access = "MLySDj0h6kaagBncTW5AxQPwx260snWuIpFPxnB5"          # 본인 값으로 변경
# secret = "a7y7l1Z6UTxslBNF5YQadycA07lAmlc99kAos7lg"          # 본인 값으로 변경
# upbit = pyupbit.Upbit(access, secret)

# print(upbit.get_balance("KRW-BTC"))     # KRW-XRP 조회
# print(upbit.get_balance("KRW"))         # 보유 현금 조회
