import pyupbit
import numpy as np
import pandas as pd
from tqdm import tqdm
import datetime
import os
import csv
from collections import deque

cash = 1000000 #자산
purchase_cash = 1000000 #매입가
tickers = pyupbit.get_tickers(fiat="KRW")
allowable_loss = 10.0 #허용 손실
target_profit = 20.0 #목표 수익
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
hold_progress = 0
date_inverted_hammer = {}
mid_inverted_hammer = {}
low_inverted_hammer = {}
volume_inverted_hammer = {}
price = {}
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
# 코인 종가 담을 deque 변수
ma7 = {}
curr_ma7 = 0
transaction_list = []
count = 1000

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
        ma7[ticker] = deque(maxlen=20)
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
        price[ticker] = 0
        low_inverted_hammer[ticker] = 0
        ma7[ticker] = deque(maxlen=7)
###################################

file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}_transaction_{}_{}.csv".format(now_year,now_month,now_day,allowable_loss,target_profit)
f = open(file_directory, "w", encoding="utf-8-sig", newline="")
writer = csv.writer(f)
row_title = ['date', 'cash', 'ticker', 'activity', 'interest ticker']
writer.writerow(row_title)
df_all['activity'] = ''

dates = df_all['index'].unique()
for date in tqdm(dates, desc='backtesting 중...'):
    df_single_day = df_all[df_all['index'] == date]
    flag_activity = False
    activity = ''
    accumulation_tickers = []
    trading_day += 1
    if flag_hold:
        hold_progress += 1

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
        ################################

        #############매집봉 탐색(기준: 거래량, 윗꼬리)###############
        if low == open and tail_high_body_ratio > tail_body_standard_ratio and volume_ratio > standard_volume_ratio:  
            if not flag_inverted_hammer[ticker]: 
                flag_inverted_hammer[ticker] = True
                date_inverted_hammer[ticker] = date    
                progress[ticker] = 0 
                if ticker == target_ticker:
                    print(date)
            mid_inverted_hammer[ticker] = (mid_inverted_hammer[ticker] * volume_inverted_hammer[ticker] + (close + low)/2 * volume) / (volume_inverted_hammer[ticker] + volume)
            low_inverted_hammer[ticker] = low
            volume_inverted_hammer[ticker] += volume 
            inverted_hammer[ticker] += 1
        ######################################           

        ########매집봉 있는 코인#########
        if flag_inverted_hammer[ticker] == True and ticker != target_ticker:  
            ##############매수 판단###############                    
            if flag_dip[ticker] == True and close > mid_inverted_hammer[ticker] and low < mid_inverted_hammer[ticker] and progress[ticker] > 1: #and volume_ratio < 5
                flag_buy[ticker] = 1
                price[ticker] = close
            else:
                flag_buy[ticker] = 0
            #####################################

            if progress[ticker] > 0:
                ##########가격유지 판단#############
                if close < mid_inverted_hammer[ticker] * (100 - box_loss) / 100:
                    volume_inverted_hammer[ticker] -= volume * 2
                    if volume_inverted_hammer[ticker] < 0:
                        flag_inverted_hammer[ticker] = False
                        flag_dip[ticker] = False
                        progress[ticker] = 0
                        volume_inverted_hammer[ticker] = 0
                        mid_inverted_hammer[ticker] = 0
                        low_inverted_hammer[ticker] = 0
                        inverted_hammer[ticker] = 0
                        flag_buy[ticker] = 0
                elif high > mid_inverted_hammer[ticker] * (100 + box_high) / 100:
                    volume_inverted_hammer[ticker] -= volume
                    if volume_inverted_hammer[ticker] < 0:
                        flag_inverted_hammer[ticker] = False
                        flag_dip[ticker] = False
                        progress[ticker] = 0
                        volume_inverted_hammer[ticker] = 0
                        mid_inverted_hammer[ticker] = 0
                        low_inverted_hammer[ticker] = 0
                        inverted_hammer[ticker] = 0
                        flag_buy[ticker] = 0
                ###################################

                if close < mid_inverted_hammer[ticker]: #눌림 
                    flag_dip[ticker] = True
            progress[ticker] += 1  
        #########################################

        ###########코인 보유시##########
        if target_ticker == ticker and flag_hold and trading_day > 10:
            ######손절(기준: 허용 손실, 거래량)#########
            if close < purchase_price * (100 - allowable_loss) / 100:
                if close < purchase_price * (100 - allowable_loss * 2) / 100:
                    volume_inverted_hammer[ticker] -= volume * 2
                else:
                    volume_inverted_hammer[ticker] -= volume
                if volume_inverted_hammer[ticker] < 0:
                    print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
                    cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )  
                    flag_inverted_hammer[ticker] = False
                    flag_hold = False                    
                    progress[ticker] = 0
                    flag_activity = True
                    activity = 'deficit sell'
                    deficit += 1
                    volume_inverted_hammer[ticker] = 0
                    mid_inverted_hammer[ticker] = 0
                    low_inverted_hammer[ticker] = 0
                    inverted_hammer[ticker] = 0
                    flag_buy[ticker] = 0
                    hold_progress = 0
                    df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = 'sell'
                    target_ticker = ''
                    print("deficit sell {}! at {} cash: {}".format(ticker, date, cash))
            ############################################

            ############장기간 보유로 인한 매매############
            if hold_progress > 30 and flag_activity == False:
                print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
                cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )  
                flag_inverted_hammer[ticker] = False
                flag_hold = False
                flag_dip[ticker] = False
                flag_rise[ticker] = False
                progress[ticker] = 0
                flag_activity = True
                activity = 'long time passed sell'
                if close > purchase_price:
                    surplus += 1
                else:
                    deficit += 1
                volume_inverted_hammer[ticker] = 0
                mid_inverted_hammer[ticker] = 0
                low_inverted_hammer[ticker] = 0
                inverted_hammer[ticker] = 0
                hold_progress = 0
                flag_buy[ticker] = 0
                df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = activity
                target_ticker = ''
                print("long time passed sell {}! at {} cash: {}".format(ticker, date, cash))
            ##############################################

            if  high > purchase_price * (100 + target_profit) / 100 and flag_activity == False: #돌파
                flag_rise[ticker] = True
            ###############익절###################
            if flag_rise[ticker] == True and progress[ticker] > 2 and flag_activity == False:
                print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
                flag_inverted_hammer[ticker] = False
                flag_rise[ticker] = False
                flag_dip[ticker] = False
                flag_hold = False
                cash = cash * (100 + target_profit) / 100
                progress[ticker] = 0
                volume_inverted_hammer[ticker] = 0
                mid_inverted_hammer[ticker] = 0
                low_inverted_hammer[ticker] = 0
                inverted_hammer[ticker] = 0
                flag_activity = True
                flag_buy[ticker] = 0
                activity = 'surplus sell'
                surplus += 1
                hold_progress = 0
                df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = activity
                target_ticker = ''
                print("surplus sell {} at {}!  cash: {}".format(ticker,date,cash))
            ####################################

        ma7[ticker].append(close)
        curr_ma7 = sum(ma7[ticker]) / len(ma7[ticker])   
        if flag_inverted_hammer[ticker] and flag_dip[ticker]:
            accumulation_tickers.append(ticker)

    
    if flag_hold == False:
        candidates = [t for t,v in flag_buy.items() if v > 0]
        if len(candidates) > 0 and flag_activity == False:
            hold_progress = 0
            volume_candidate = {}
            inverted_hammer_candidate = {}
            for candidate in candidates:
                inverted_hammer_candidate[candidate] = inverted_hammer[candidate]
            candidates = [t for t,v in inverted_hammer_candidate.items() if max(inverted_hammer_candidate.values()) == v]
            for candidate in candidates:
                volume_candidate[candidate] = volume_inverted_hammer[candidate]
            target_ticker = max(volume_candidate, key=volume_candidate.get)
            purchase_price = price[target_ticker]
            flag_hold = True
            purchase_cash = cash
            activity = 'buy'
            transaction_list.append(target_ticker)
            df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = activity
            print("buy {} which has {} hammer for {}! at {}".format(target_ticker,inverted_hammer[target_ticker], price[target_ticker], date))


    data = [date, cash, target_ticker, activity, candidates]
    writer.writerow(data)

# file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}_transaction_ticker_{}_{}.csv".format(now_year,now_month,now_day,allowable_loss,target_profit)
# df_transaction_icker = pd.DataFrame()
# for ticker in tqdm(transaction_list, desc='거래 티커 병합중'):
#     df_transaction_icker = pd.concat([df_transaction_icker, df_all[df_all['ticker'] == ticker]])
# df_transaction_icker.to_csv(file_directory, mode='w',index=False)

print(surplus/(surplus + deficit) * 100)
print(cash)