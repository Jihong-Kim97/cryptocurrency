import pyupbit
import numpy as np
import pandas as pd
from tqdm import tqdm
import datetime
import os

cash = 1000000 #자산
purchase_cash = 1000000 #매입가
tickers = pyupbit.get_tickers(fiat="KRW")
allowable_loss = 15.0 #허용 손실
target_profit = 10.0 #목표 수익
df_all = pd.DataFrame()
pre_volumes = {}
flag_inverted_hammer = {}
flag_dip = {}
flag_rise = {}
progress = {} #보유일
date_inverted_hammer = {}
mid_inverted_hammer = {}
volume_inverted_hammer = {}
flag_hold = False
flag_activity = False
target_ticker = ''
purchase_price = 0
transaction_dates = []
now = str(datetime.datetime.now())
now_year = now[0:4]
now_month = now[5:7]
now_day = now[8:10]
surplus = 0
deficit = 0

file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}.csv".format(now_year,now_month,now_day)
if not os.path.exists(file_directory):
    for ticker in tqdm(tickers, desc='자료 병합중...'):
        df_ticker = pyupbit.get_ohlcv(ticker, count = 365)
        df_ticker['ticker'] = ticker
        flag_inverted_hammer[ticker] = False
        flag_dip[ticker] = False
        flag_rise[ticker] = False
        progress[ticker] = 0
        volume_inverted_hammer[ticker] = 0
        df_all = pd.concat([df_all, df_ticker])
        pre_volumes[ticker] = 1000000000
        mid_inverted_hammer[ticker] = 0
    df_all.reset_index(inplace=True)
    df_all = df_all.sort_values(by='index')
    df_all.to_csv(file_directory, mode='w',index=False)
else:
    df_all = pd.read_csv(file_directory)
    for ticker in tqdm(tickers, desc='자료 병합중...'):
        flag_inverted_hammer[ticker] = False
        flag_dip[ticker] = False
        flag_rise[ticker] = False
        progress[ticker] = 0
        pre_volumes[ticker] = 1000000000
        volume_inverted_hammer[ticker] = 0
        mid_inverted_hammer[ticker] = 0

dates = df_all['index'].unique()
for date in tqdm(dates, desc='backtesting 중...'):
    df_single_day = df_all[df_all['index'] == date]
    flag_activity = False
    for ticker in tickers:
        ########당일 정보 입력###########
        tmp_progress = progress[ticker]
        tmp_flag_inverted_hammer = flag_inverted_hammer[ticker]
        tmp_flag_dip = flag_dip[ticker]
        tmp_flag_rise = flag_rise[ticker]
        tmp_mid_inverted_hammer = mid_inverted_hammer[ticker]
        df_ticker_single_day = df_single_day[df_single_day['ticker'] == ticker]
        if(len(df_ticker_single_day['open'])) < 1 :
            continue
        open = df_ticker_single_day['open'].values[0]
        high = df_ticker_single_day['high'].values[0]
        low = df_ticker_single_day['low'].values[0]
        close = df_ticker_single_day['close'].values[0]
        volume = df_ticker_single_day['volume'].values[0]
        tail = high - close
        body = close - open
        ror = (close - open)/open * 100
        max_ror = (high - open)/open * 100
        if not body == 0:
            ratio = tail/body
        else:
            ratio = 0
        volume_ratio = volume / pre_volumes[ticker]
        pre_volumes[ticker] = volume
        ################################

        #############매집봉 탐색(기준: 거래량, 윗꼬리)###############
        if low == open and ratio > 0.25 and volume_ratio > 3 and not tmp_flag_inverted_hammer: 
            tmp_flag_inverted_hammer = True
            mid_inverted_hammer[ticker] = (close + low)/2
            low_inverted_hammer = low
            high_inverted_hammer = high
            close_inverted_hammer = close
            volume_inverted_hammer[ticker] = volume 
            date_inverted_hammer[ticker] = date    
            tmp_progress = 0 
            if ticker == target_ticker:
                print(date)
        ######################################

        ######매도 판단(기준: 허용 손실, 거래량)#########
        if target_ticker == ticker and flag_hold == True and close < purchase_price * (100 - allowable_loss) / 100:
            volume_inverted_hammer[ticker] -= volume * 2
            if volume_inverted_hammer[ticker] < 0:
                print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
                cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )  
                tmp_flag_inverted_hammer = False
                flag_hold = False
                target_ticker = ''
                tmp_progress = 0
                flag_activity = True
                deficit += 1
                volume_inverted_hammer[ticker] = 0
                mid_inverted_hammer[ticker] = 0
                print("deficit sell {}! at {} cash: {}".format(ticker, date, cash))            


        if tmp_flag_inverted_hammer == True: #박스권 형성 여부 탐색
            ##############매수 판단###############
            if low < tmp_mid_inverted_hammer and flag_hold == False and tmp_progress > 0 and not flag_activity == True: #눌림
                tmp_flag_dip = True

            if tmp_progress > 30 and flag_hold == False:
                tmp_flag_inverted_hammer = False
                tmp_flag_dip = False
                tmp_progress = 0
                
            if flag_activity == False and flag_hold == False and tmp_flag_dip == True and high > tmp_mid_inverted_hammer and tmp_progress > 1: #가격 유지해주면 매수
                purchase_price = tmp_mid_inverted_hammer
                purchase_cash = cash
                target_ticker = ticker
                flag_hold = True
                flag_activity = True
                print(" buy {}! at {}".format(ticker, date))
            #####################################

            if target_ticker == ticker and flag_hold == True and tmp_flag_dip == True and high > purchase_price * (100 + target_profit) / 100 and flag_activity == False: #돌파
                tmp_flag_rise = True
            
            tmp_progress += 1

        if target_ticker == ticker and tmp_flag_inverted_hammer == True and tmp_flag_rise == True and tmp_flag_dip == True and tmp_progress > 2 and flag_activity == False: #매도
            print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
            tmp_flag_inverted_hammer = False
            tmp_flag_rise = False
            tmp_flag_dip = False
            flag_hold = False
            cash = cash * (100 + target_profit) / 100
            tmp_progress = 0
            volume_inverted_hammer[ticker] = 0
            mid_inverted_hammer[ticker] = 0
            flag_activity = True
            target_ticker = ''
            surplus += 1
            print("surplus sell {} at {}!  cash: {}".format(ticker,date,cash))

        progress[ticker] = tmp_progress
        flag_inverted_hammer[ticker] = tmp_flag_inverted_hammer
        flag_dip[ticker] = tmp_flag_dip
        flag_rise[ticker] = tmp_flag_rise
        #mid_inverted_hammer[ticker] = tmp_mid_inverted_hammer

print(surplus/(surplus + deficit) * 100)
print(cash)