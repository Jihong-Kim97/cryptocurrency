import pyupbit
import numpy as np
import pandas as pd
from tqdm import tqdm
import datetime
import os
import csv
from collections import deque
from utils import yesterday

cash = 1000000 #자산
purchase_cash = 1000000 #매입가
tickers = pyupbit.get_tickers(fiat="KRW")
allowable_loss = 10.0 #허용 손실
target_profit = 20.0 #목표 수익
max_target_profit = 50.0
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
hold_progress = 0
hold_progresses = []
date_inverted_hammer = {}
mid_inverted_hammer = {}
low_inverted_hammer = {}
high_inverted_hammer = {}
volume_inverted_hammer = {}
accumulate_volume_inverted_hammer = {}
escape_hammer = {}
price = {}
dip = {}
flag_escape =  False
flag_sell =  False
flag_hold = False
flag_activity = False
flag_under_ma224 = False
target_ticker = ''
purchase_price = 0
transaction_dates = []
now = str(datetime.datetime.now())
now_year = now[0:4]
now_month = now[5:7]
now_day = now[8:10]
now_hour = int(now[11:13])
surplus = 0
normal_surplus = 0
max_surplus = 0
max_return_rate = 0.0
deficit = 0
# 코인 종가 담을 deque 변수
ma7 = {}
curr_ma7 = 0
ma224 = {}
curr_ma224 = {}
transaction_list = []
count = 1000
profits = []
high_profits = []

#############초기 세팅##############
if now_hour > 9:
    file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}.csv".format(now_year,now_month,now_day)
else:
    now_year, now_month, now_day = yesterday(now)
    file_directory = "C:/Users/KimJihong/Desktop/김지홍/개발/코인/DB/{}{}{}.csv".format(now_year,now_month,now_day)
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
        accumulate_volume_inverted_hammer[ticker] = 0
        df_all = pd.concat([df_all, df_ticker])
        pre_volumes[ticker] = 1000000000
        mid_inverted_hammer[ticker] = 0
        price[ticker] = 0
        low_inverted_hammer[ticker] = 0
        high_inverted_hammer[ticker] = 0
        dip[ticker] = 0
        ma7[ticker] = deque(maxlen=20)
        ma224[ticker] = deque(maxlen=224)
        curr_ma224[ticker] = 0
    df_all.reset_index(inplace=True)
    df_all = df_all.sort_values(by='index')
    df_all.to_csv(file_directory, mode='w',index=False)
else:
    for ticker in tqdm(tickers, desc='자료 병합중...'):
        flag_inverted_hammer[ticker] = False
        flag_dip[ticker] = False
        flag_rise[ticker] = False
        flag_buy[ticker] = 0
        inverted_hammer[ticker] = 0
        progress[ticker] = 0
        pre_volumes[ticker] = 1000000000
        volume_inverted_hammer[ticker] = 0
        accumulate_volume_inverted_hammer[ticker] = 0
        mid_inverted_hammer[ticker] = 0
        high_inverted_hammer[ticker] = 0
        price[ticker] = 0
        low_inverted_hammer[ticker] = 0
        dip[ticker] = 0
        ma7[ticker] = deque(maxlen=7)
        ma224[ticker] = deque(maxlen=224)
        curr_ma224[ticker] = 0
###################################

df_all = pd.read_csv(file_directory)
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
        ma224[ticker].append(close)
        curr_ma224[ticker] = sum(ma224[ticker]) / len(ma224[ticker])   
        ################################

        #############매집봉 탐색(기준: 거래량, 윗꼬리)###############
        if tail_low_body_ratio < tail_body_standard_ratio and tail_high_body_ratio > tail_body_standard_ratio and volume_ratio > standard_volume_ratio:  # low == open
            if not flag_inverted_hammer[ticker]: 
                flag_inverted_hammer[ticker] = True
                date_inverted_hammer[ticker] = date    
                progress[ticker] = 0 
            mid_inverted_hammer[ticker] = (mid_inverted_hammer[ticker] * volume_inverted_hammer[ticker] + (close + low)/2 * volume) / (volume_inverted_hammer[ticker] + volume)
            low_inverted_hammer[ticker] = low
            high_inverted_hammer[ticker] = high
            accumulate_volume_inverted_hammer[ticker] += volume
            volume_inverted_hammer[ticker] += volume
            inverted_hammer[ticker] += 1
        ######################################           

        ########매집봉 있는 코인#########
        if flag_inverted_hammer[ticker] == True:  
            if close < mid_inverted_hammer[ticker]: #눌림 
                flag_dip[ticker] = True
                curr_dip = (mid_inverted_hammer[ticker] - close) / mid_inverted_hammer[ticker] * 100
                if dip[ticker] < curr_dip:
                    dip[ticker] = curr_dip
                    
            if ticker != target_ticker:
                ##############매수 판단###############         
                if flag_dip[ticker] == True:           
                    if close > mid_inverted_hammer[ticker] and low < mid_inverted_hammer[ticker] and progress[ticker] > 1 and max_ror < 30 and ror > 0: #and volume_ratio < 5
                        flag_buy[ticker] = 1
                        price[ticker] = mid_inverted_hammer[ticker]
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

                    if flag_escape == True:
                        flag_inverted_hammer[ticker] = False
                        flag_dip[ticker] = False
                        progress[ticker] = 0
                        volume_inverted_hammer[ticker] = 0
                        accumulate_volume_inverted_hammer[ticker] = 0
                        mid_inverted_hammer[ticker] = 0
                        low_inverted_hammer[ticker] = 0
                        inverted_hammer[ticker] = 0
                        dip[ticker] = 0
                        flag_buy[ticker] = 0


            progress[ticker] += 1  
        #########################################

        ###########코인 보유시##########
        if target_ticker == ticker and flag_hold and trading_day > 10:
            if dip[ticker] > 20:
                target_profit = max_target_profit
            # elif close > curr_ma224[ticker] * 1.1 and  len(ma224[ticker]) == 224 and flag_under_ma224:
            #     target_profit = max_target_profit
            #     print(date, ticker, curr_ma224[ticker])
            else: 
                target_profit = 20
            ######손절(기준: 허용 손실, 거래량)#########
            if close < purchase_price * (100 - allowable_loss) / 100 and flag_sell == False:
                if flag_standard:
                    if close < purchase_price * (100 - allowable_loss * 2) / 100:
                        volume_inverted_hammer[ticker] -= volume * 2
                    else:
                        volume_inverted_hammer[ticker] -= volume
                    if volume_inverted_hammer[ticker] < 0:
                        flag_sell =  True
                        cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )
                        activity = 'deficit sell'
                        deficit += 1
                else:
                    flag_sell =  True
                    cash = purchase_cash * (100 - allowable_loss) / 100
                    activity = 'deficit sell'
                    deficit += 1
            ############################################

            # ############장기간 보유로 인한 매매#############
            # if hold_progress > 30 and flag_activity == False:
            #     flag_sell =  True
            #     cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )  
            #     activity = 'long time passed sell'
            #     if close > purchase_price:
            #         surplus += 1
            #         if target_profit == max_target_profit:
            #             max_surplus += 1 
            #         else:
            #             normal_surplus += 1
            #     else:
            #         deficit += 1
            # ##############################################

            if  high > purchase_price * (100 + target_profit) / 100 and flag_activity == False and flag_sell == False: #돌파
                flag_rise[ticker] = True
                profits.append([int((high - purchase_price)/purchase_price * 100), hold_progress])
            ###############익절###################
            if flag_rise[ticker] == True and progress[ticker] > 2 and flag_activity == False:
                flag_rise[ticker] = False
                flag_sell =  True
                activity = 'surplus sell'
                cash = cash * (100 + target_profit) / 100
                surplus += 1
                if target_profit == max_target_profit:
                    max_surplus += 1 
                else:
                    normal_surplus += 1
            ####################################

            ############세력탈출 판단###############
            if ((open - low)/open * 100 > 20) and flag_sell == False:
                flag_sell =  True
                cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )
                activity = "escape"
                if close > purchase_price:
                    surplus += 1
                    if target_profit == max_target_profit:
                        max_surplus += 1 
                    else:
                        normal_surplus += 1
                else:
                    deficit += 1
            ####################################### miss 30->40

            ##########목표 수익률 잘못 설정###########
            return_rate = (high - purchase_price)/purchase_price * 100
            if max_return_rate < return_rate:
                max_return_rate = return_rate
            elif max_return_rate > 40 and (close - purchase_price)/purchase_price * 100 < 30 and flag_sell == False:
                flag_sell =  True
                cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )
                activity = "miss"
                if close > purchase_price:
                    surplus += 1
                else:
                    deficit += 1
            elif max_return_rate > 30 and (close - purchase_price)/purchase_price * 100 < 20 and flag_sell == False:
                flag_sell =  True
                cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )
                activity = "miss"
                if close > purchase_price:
                    surplus += 1
                else:
                    deficit += 1
            # elif max_return_rate > 20 and (close - purchase_price)/purchase_price * 100 < 0 and flag_sell == False:
            #     flag_sell =  True
            #     cash = purchase_cash * ( 1 + (close - purchase_price) / purchase_price )
            #     activity = "miss"
            #     if close > purchase_price:
            #         surplus += 1
            #     else:
            #         deficit += 1
            #########################################

            if flag_sell == True:
                print(str(date_inverted_hammer[ticker]) + " ~ " + str(date))
                print("{} {}! at {} cash: {}".format(activity, ticker, date, cash))
                flag_inverted_hammer[ticker] = False
                flag_rise[ticker] = False
                flag_dip[ticker] = False
                flag_hold = False
                hold_progresses.append(hold_progress)
                hold_progress = 0
                df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = activity
                target_ticker = ''
                progress[ticker] = 0
                volume_inverted_hammer[ticker] = 0
                accumulate_volume_inverted_hammer[ticker] = 0
                mid_inverted_hammer[ticker] = 0
                low_inverted_hammer[ticker] = 0
                flag_buy[ticker] = 0
                inverted_hammer[ticker] = 0
                dip[ticker] = 0
                flag_activity = True

        ma7[ticker].append(close)
        curr_ma7 = sum(ma7[ticker]) / len(ma7[ticker])   

    
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
            max_return_rate = 0.0
            if price[target_ticker] < curr_ma224[target_ticker] and  len(ma224[target_ticker]) == 224:
                flag_under_ma224 = True
            else:
                flag_under_ma224 = False
            df_all.loc[(df_all['ticker'] == target_ticker) & (df_all['index'] == date), 'activity'] = activity
            print("buy {} which has {} hammer, {} dip for {}! at {}".format(target_ticker,inverted_hammer[target_ticker], dip[target_ticker], price[target_ticker], date))
    else:
        candidates = [t for t,v in flag_buy.items() if v > 0]
        if len(candidates) > 0:
            inverted_hammer_candidate = {}
            for candidate in candidates:
                inverted_hammer_candidate[candidate] = inverted_hammer[candidate]
            candidates = [t for t,v in inverted_hammer_candidate.items() if max(inverted_hammer_candidate.values()) == v]


    data = [date, cash, target_ticker, activity, candidates]
    writer.writerow(data)

print("거래횟수: " + str(surplus + deficit))
print("성공률: "+ str(round(surplus/(surplus + deficit) * 100, 2)) + "%")
print(normal_surplus, max_surplus)
print(hold_progresses)
print(sum(hold_progresses)/len(hold_progresses))
print(cash)
# print(profits)