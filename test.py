import pyupbit
import numpy as np


print((pyupbit.get_ohlcv("KRW-BTC", interval="minute1",count=1440 , to="20230210 09:00:00")).tolist())