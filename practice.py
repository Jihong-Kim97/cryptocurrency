import pyupbit
import numpy as np
import pandas as pd
from tqdm import tqdm
import datetime
import os
import csv
from collections import deque

tickers = pyupbit.get_tickers(fiat="KRW")
allowable_loss = 10.0 #허용 손실
target_profit = 20.0 #목표 수익
max_target_profit = 40.0
flag_standard = 1 # 1:거래량기준 0: 손실률기준
box_loss = 15.00
box_high = 20.00
tail_body_standard_ratio = 0.25
standard_volume_ratio = 10
trading_day = 0
df_all = pd.DataFrame()
pre_volumes = {}
flag_inverted_hammer = {}
inverted_hammer = {}
flag_dip = {}
flag_rise = {}
flag_buy = {} #중간값 들어온 횟수
progress = {} #매집봉 발견 이후 경과일
hold_progress = {}
hold_progresses = []
date_inverted_hammer = {}
mid_inverted_hammer = {}
low_inverted_hammer = {}
high_inverted_hammer = {}
volume_inverted_hammer = {}
escape_hammer = {}
price = {}
dip = {}
flag_escape =  False
flag_sell =  False
flag_hold = False
flag_activity = False
target_ticker = ''
target_tickers = []
purchase_price = {}
transaction_dates = []
now = str(datetime.datetime.now())
now_year = now[0:4]
now_month = now[5:7]
now_day = now[8:10]
surplus = 0
normal_surplus = 0
max_surplus = 0
max_return_rate = 0.0
deficit = 0
transaction_list = []
count = 1000
profits = []
high_profits = []

#############초기 세팅##############
file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}_{}.csv".format(now_year,now_month,now_day,count)
if not os.path.exists(file_directory):
    for ticker in tqdm(tickers, desc='자료 병합중...'):
        df_ticker = pyupbit.get_ohlcv(ticker, count = count)
        df_ticker['ticker'] = ticker
        flag_inverted_hammer[ticker] = False
        flag_dip[ticker] = False
        flag_rise[ticker] = False
        flag_buy[ticker] = 0
        progress[ticker] = 0
        inverted_hammer[ticker] = 0
        volume_inverted_hammer[ticker] = 0
        df_all = pd.concat([df_all, df_ticker])
        pre_volumes[ticker] = 1000000000
        mid_inverted_hammer[ticker] = 0
        price[ticker] = 0
        low_inverted_hammer[ticker] = 0
        purchase_price[ticker] = 0
        high_inverted_hammer[ticker] = 0
        dip[ticker] = 0
        hold_progress[ticker] = 0
    df_all.reset_index(inplace=True)
    df_all = df_all.sort_values(by='index')
    df_all.to_csv(file_directory, mode='w',index=False)
else:
    df_all = pd.read_csv(file_directory)
    for ticker in tqdm(tickers, desc='자료 병합중...'):
        flag_inverted_hammer[ticker] = False
        flag_dip[ticker] = False
        flag_rise[ticker] = False
        flag_buy[ticker] = 0
        inverted_hammer[ticker] = 0
        progress[ticker] = 0
        pre_volumes[ticker] = 1000000000
        volume_inverted_hammer[ticker] = 0
        mid_inverted_hammer[ticker] = 0
        high_inverted_hammer[ticker] = 0
        price[ticker] = 0
        low_inverted_hammer[ticker] = 0
        purchase_price[ticker] = 0
        dip[ticker] = 0
        hold_progress[ticker] = 0
###################################

file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}_database_{}_{}.csv".format(now_year,now_month,now_day,allowable_loss,target_profit)
f = open(file_directory, "w", encoding="utf-8-sig", newline="")
writer = csv.writer(f)
row_title = ['date', 'ticker', 'state','first hammer date','progress', 'num inverted hammer', 'max ror']
writer.writerow(row_title)
df_all['activity'] = ''

dates = df_all['index'].unique()
list_dates = dates.tolist()
for date in tqdm(dates, desc='backtesting 중...'):
    df_single_day = df_all[df_all['index'] == date]
    flag_activity = False
    activity = ''
    accumulation_tickers = []
    trading_day += 1

    for ticker in tickers:
        ########당일 정보 입력###########
        df_ticker_single_day = df_single_day[df_single_day['ticker'] == ticker]
        if(len(df_ticker_single_day['open'])) < 1 :
            continue
        open = df_ticker_single_day['open'].values[0]
        high = df_ticker_single_day['high'].values[0]
        low = df_ticker_single_day['low'].values[0]
        close = df_ticker_single_day['close'].values[0]
        volume = df_ticker_single_day['volume'].values[0]
        flag_escape = False
        flag_sell =  False
        tail_high = high - close
        tail_low = open - low
        body = close - open
        ror = (close - open)/open * 100
        max_ror = (high - open)/open * 100
        if not body == 0:
            tail_high_body_ratio = tail_high/body
            tail_low_body_ratio = tail_low/body
        else:
            tail_high_body_ratio = 0
            tail_low_body_ratio = 0
        volume_ratio = volume / pre_volumes[ticker]
        pre_volumes[ticker] = volume
        if ticker in target_tickers:
            hold_progress[ticker] += 1
        ################################

        #############매집봉 탐색(기준: 거래량, 윗꼬리)###############
        if tail_low_body_ratio < tail_body_standard_ratio and tail_high_body_ratio > tail_body_standard_ratio and volume_ratio > standard_volume_ratio:
            if not flag_inverted_hammer[ticker]: 
                flag_inverted_hammer[ticker] = True
                date_inverted_hammer[ticker] = date    
                progress[ticker] = 0 
                # state = 'find first hammer'
                # data = [date, ticker, state, progress[ticker]]
                # writer.writerow(data)
            # else:
                # state = 'find {} hammer'.format(inverted_hammer[ticker])
                # data = [date, ticker, state, progress[ticker]]
                # writer.writerow(data)
            mid_inverted_hammer[ticker] = (mid_inverted_hammer[ticker] * volume_inverted_hammer[ticker] + (close + low)/2 * volume) / (volume_inverted_hammer[ticker] + volume)
            low_inverted_hammer[ticker] = low
            high_inverted_hammer[ticker] = high
            volume_inverted_hammer[ticker] += volume 
            inverted_hammer[ticker] += 1
        ######################################           

        ########매집봉 있는 코인#########
        if flag_inverted_hammer[ticker] == True and not ticker in target_tickers:  
            ##############매수 판단###############         
            if flag_dip[ticker] == True:           
                if close > mid_inverted_hammer[ticker] and low < mid_inverted_hammer[ticker] and progress[ticker] > 1 and max_ror < 30 and ror > 0: #and volume_ratio < 5
                    flag_buy[ticker] = 1
                    price[ticker] = mid_inverted_hammer[ticker]
                    target_tickers.append(ticker)
                    purchase_price[ticker]= mid_inverted_hammer[ticker]
                    # state = 'buy signal'
                    # data = [date, ticker, state, date_inverted_hammer[ticker], progress[ticker] , inverted_hammer[ticker], hold_progress[ticker]]
                    # writer.writerow(data)
                elif high > high_inverted_hammer[ticker]:
                    False
                else:
                    flag_buy[ticker] = 0
            #####################################

            if progress[ticker] > 0:
                ##########가격유지 판단#############
                if close < mid_inverted_hammer[ticker] * (100 - box_loss) / 100:
                    volume_inverted_hammer[ticker] -= volume
                    if volume_inverted_hammer[ticker] < 0:
                        flag_escape = True
                elif high > mid_inverted_hammer[ticker] * (100 + box_high) / 100:
                    volume_inverted_hammer[ticker] -= volume
                    if volume_inverted_hammer[ticker] < 0:
                        flag_escape = True

                if (open - close)/ open * 100  > 25:
                    flag_escape = True
                ###################################

                ############세력탈출 판단###############
                if ror < 0 and volume_ratio > standard_volume_ratio:
                    flag_escape = True
                #######################################

                if (high - open)/open * 100 > 20 and progress[ticker] > 5: 
                    state = 'rise'
                    data = [date, ticker, state, date_inverted_hammer[ticker], progress[ticker], inverted_hammer[ticker] , max_ror]
                    writer.writerow(data)
                    flag_escape = True

                if flag_escape == True:
                    flag_inverted_hammer[ticker] = False
                    flag_dip[ticker] = False
                    progress[ticker] = 0
                    volume_inverted_hammer[ticker] = 0
                    mid_inverted_hammer[ticker] = 0
                    low_inverted_hammer[ticker] = 0
                    inverted_hammer[ticker] = 0
                    dip[ticker] = 0
                    flag_buy[ticker] = 0

                if close < mid_inverted_hammer[ticker]: #눌림 
                    flag_dip[ticker] = True
                    curr_dip = (mid_inverted_hammer[ticker] - close) / mid_inverted_hammer[ticker] * 100
                    if dip[ticker] < curr_dip:
                        dip[ticker] = curr_dip

            progress[ticker] += 1  
        #########################################