import os
import sys
import logging
import traceback
import time
import math

from decimal import Decimal
from datetime import datetime
import dateutil.parser
# 공통 모듈 Import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module import upbit


# -----------------------------------------------------------------------------
# - Name : start_buytrade
# - Desc : 매수 로직
# - Input
# 1) buy_amt : 매수금액
# -----------------------------------------------------------------------------
def start_buytrade(buy_amtp):
    try:

        # ----------------------------------------------------------------------
        # 반복 수행
        # ----------------------------------------------------------------------
        while True:
            #
            # logging.info("*********************************************************")
            # logging.info("1. 로그레벨 : " + str(log_level))
            # logging.info("2. 매수금액 % : " + str(buy_amtp))
            # logging.info("*********************************************************")

            # -----------------------------------------------------------------
            # 전체 종목 리스트 추출
            # -----------------------------------------------------------------
            target_items = upbit.get_items('KRW', 'ASTR,ID,PYTH')

            # -----------------------------------------------------------------
            # 종목별 체크 #
            # -----------------------------------------------------------------
            for target_item in target_items:

                #rsi_val = False
                #mfi_val = False
                #ocl_val = False
                logging.info('------------------------------------------------------')
                # logging.info('')
                # logging.info('------------------------------------------------------')

                logging.info('체크중....[' + str(target_item['market']) + ']')
                #time.sleep(0.001)




                # ------------------------------------------------------------------
                # 잦은 거래 방지
                # ------------------------------------------------------------------

                order_done = upbit.get_order_status(target_item['market'], 'done') + upbit.get_order_status(
                    target_item['market'], 'cancel')
                order_done_sorted = upbit.orderby_dict(order_done, 'created_at', True)
                order_done_filtered = upbit.filter_dict(order_done_sorted, 'side', 'bid')

                # -------------------------------------------------
                # 매수 직후 나타나는 오류 체크용 마지막 매수 시간 차이 계산
                # -------------------------------------------------
                # 마지막 매수 시간
                last_buy_dt = datetime.strptime(
                    dateutil.parser.parse(order_done_filtered[0]['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                    '%Y-%m-%d %H:%M:%S')

                # 현재 시간 추출
                current_dt = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                               '%Y-%m-%d %H:%M:%S')

                # 시간 차이 추출
                diff = current_dt - last_buy_dt

                # logging.info(str(last_buy_dt) + '     ' + str(current_dt))
                # logging.info(str(diff) + '시간 차이')
                # logging.info(str(diff.seconds) + '초 차이') # 초 계산이 안맞네;;;
                #
                # logging.info(str(diff.days) + '날 차이')

                # 매수 후 10시간은 진행하지 않음(너무 잦은 거래 방지) - 잠시 꺼두자
                if diff.days < 3:
                    logging.info('+_+ 3일에 한 번 거래 +_+ ')
                    logging.info('------------------------------------------------------')
                    continue

                # -------------------------------------------------------------
                # 종목별 보조지표를 조회
                # 1. 조회 기준 : 일캔들, 최근 5개 지표 조회
                # 2. 속도를 위해 원하는 지표만 조회(RSI, MFI, MACD, CANDLE) - 수정
                # -------------------------------------------------------------
                indicators = upbit.get_indicator_sel(target_item['market'], '60', 200, 3,
                                                     ['BB', 'BB2', 'CANDLE'])
                # ['RSI', 'MFI', 'MACD', 'BB', 'CANDLE'])


                # --------------------------------------------------------------
                # 최근 상장하여 캔들 갯수 부족으로 보조 지표를 구하기 어려운 건은 제외
                # --------------------------------------------------------------
                if 'CANDLE' not in indicators or len(indicators['CANDLE']) < 199: #원래 200
                    logging.info('캔들 데이터 부족으로 데이터 산출 불가...[' + str(target_item['market']) + ']')
                    continue

                # --------------------------------------------------------------
                # 보조 지표 추출
                # --------------------------------------------------------------
                #rsi = indicators['RSI']
                #mfi = indicators['MFI']
                #macd = indicators['MACD']
                bb = indicators['BB']
                bb2 = indicators['BB2']
                candle = indicators['CANDLE']

                # --------------------------------------------------------------
                # 구매 비용 조절
                # --------------------------------------------------------------

                krw_balance = upbit.get_krwbal()
                avg_buy_price = 0

                account_data = upbit.get_accounts("N", "KRW")
                for account_data_for in account_data:
                    # logging.info(account_data_for)
                    # logging.info(account_data_for['avg_buy_price'])
                    avg_buy_price = avg_buy_price + Decimal(account_data_for['avg_buy_price']) * Decimal(account_data_for['balance'])

                #logging.info(avg_buy_price)
                avg_buy_price = round(avg_buy_price)

                buy_amt = math.floor((krw_balance['krw_balance'] + avg_buy_price) * buy_amtp / 100 / 10000) * 10000

                logging.info("{:,}".format(krw_balance['krw_balance']) + ' 원 매수 가능 --> ' + str(avg_buy_price) + ' 원 기매수 금액 --> ' \
                             + str(buy_amt) + ' 원 매수 시도 (' + str(buy_amtp) + ' %)')
                logging.info(str(round((candle[0]['trade_price'] - bb2[0]['BBL']) / bb2[0]['BBL'] * 100, 1)) + ' % BBL diff. || BBH diff. ' + str(round((bb2[0]['BBH'] - candle[0]['trade_price']) / bb2[0]['BBH'] * 100, 1)) + ' %')

                # if krw_balance['krw_balance'] + avg_buy_price > 1400000:
                #     buy_amt = buy_amt + 30000
                # else:
                #     buy_amt = buy_amt - 30000

                i = 0 # i 초기화
                # --------------------------------------------------------------
                # 볼린저 밴드 추가
                # --------------------------------------------------------------
                if bb2[0]['BBL'] > candle[0]['low_price'] and bb[0]['BBL'] > bb2[0]['BBL'] and bb[1]['BBL'] > bb2[1]['BBL'] and bb[2]['BBL'] > bb2[2]['BBL'] and candle[2]['high_price'] != candle[1]['high_price'] and candle[2]['low_price'] != candle[1]['low_price']:

                # if (bb2[0]['BBL'] > candle[0]['low_price'] and bb[0]['BBL'] > bb2[0]['BBL'] and bb[1]['BBL'] > bb2[1]['BBL'] and bb[2]['BBL'] > bb2[2]['BBL'] and candle[2]['high_price'] != candle[1]['high_price'] and candle[2]['low_price'] != candle[1]['low_price'] and (candle[1]['high_price'] - candle[1]['low_price']) != (candle[2]['high_price'] - candle[2]['low_price'])) or (bb2[0]['BBH'] < candle[0]['high_price'] and all(bb2[i+1]['BBH'] > candle[i+1]['high_price'] for i in range(50))): #보관, 왜 매수가 안될까? 원복하자

                # --------------------------------------------------------------
                # 매수 로직
                # 1. RSI : 2일전 < 30미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # 2. MFI : 2일전 < 20미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # 3. MACD(OCL) : 3일전 < 0, 2일전 < 0, 1일전 < 0, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # --------------------------------------------------------------
                #
                # # --------------------------------------------------------------
                # # RSI : 2일전 < 30미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # # rsi[0]['RSI'] : 현재
                # # rsi[1]['RSI'] : 1일전
                # # rsi[2]['RSI'] : 2일전
                # # rsi[3]['RSI'] : 3일전
                # # --------------------------------------------------------------
                # if (Decimal(str(rsi[0]['RSI'])) > Decimal(str(rsi[1]['RSI'])) > Decimal(str(rsi[2]['RSI']))
                #         and Decimal(str(rsi[3]['RSI'])) > Decimal(str(rsi[2]['RSI']))
                #         and Decimal(str(rsi[2]['RSI'])) < Decimal(str(30))):
                #     rsi_val = True
                #
                # # --------------------------------------------------------------
                # # MFI : 2일전 < 20미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # # mfi[0]['MFI'] : 현재
                # # mfi[1]['MFI'] : 1일전
                # # mfi[2]['MFI'] : 2일전
                # # mfi[3]['MFI'] : 3일전
                # # --------------------------------------------------------------
                # if (Decimal(str(mfi[0]['MFI'])) > Decimal(str(mfi[1]['MFI'])) > Decimal(str(mfi[2]['MFI']))
                #         and Decimal(str(mfi[3]['MFI'])) > Decimal(str(mfi[2]['MFI']))
                #         and Decimal(str(mfi[2]['MFI'])) < Decimal(str(20))):
                #     mfi_val = True
                #
                # # --------------------------------------------------------------
                # # MACD(OCL) : 3일전 < 0, 2일전 < 0, 1일전 < 0, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # # macd[0]['OCL'] : 현재
                # # macd[1]['OCL'] : 1일전
                # # macd[2]['OCL'] : 2일전
                # # macd[3]['OCL'] : 3일전
                # # --------------------------------------------------------------
                #
                # if (Decimal(str(macd[0]['OCL'])) > Decimal(str(macd[1]['OCL'])) > Decimal(str(macd[2]['OCL']))
                #         and Decimal(str(macd[3]['OCL'])) > Decimal(str(macd[2]['OCL']))
                #         and Decimal(str(macd[1]['OCL'])) < Decimal(str(0))
                #         and Decimal(str(macd[2]['OCL'])) < Decimal(str(0))
                #         and Decimal(str(macd[3]['OCL'])) < Decimal(str(0))):
                #     ocl_val = True
                #
                #
                # # --------------------------------------------------------------
                # # 매수대상 발견
                # # --------------------------------------------------------------
                # if rsi_val and mfi_val and ocl_val:
                #     logging.info('매수대상 발견....[' + str(target_item['market']) + ']')
                #     logging.info('RSI : ' + str(rsi))
                #     logging.info('MFI : ' + str(mfi))
                #     logging.info('MACD : ' + str(macd))

                    # ------------------------------------------------------------------
                    # 기매수 여부 판단
                    # ------------------------------------------------------------------
                    accounts = upbit.get_accounts('Y', 'KRW')
                    account = list(filter(lambda x: x.get('market') == target_item['market'], accounts))

                    # 이미 매수한 종목이면 다시 매수하지 않음
                    # sell_bot.py에서 매도 처리되면 보유 종목에서 사라지고 다시 매수 가능
                    if len(account) > 0:
                        logging.info('기 매수 종목....[' + str(target_item['market']) + ']')
                        continue

                    # ------------------------------------------------------------------
                    # 거래 금액 낮은것 판단
                    # ------------------------------------------------------------------

                    if candle[0]['trade_price'] < 1:
                        logging.info('1원 미만 종목....[' + str(target_item['market']) + ']')
                        continue





                    # ------------------------------------------------------------------
                    # 매수금액 설정
                    # 1. M : 수수료를 제외한 최대 가능 KRW 금액만큼 매수
                    # 2. 금액 : 입력한 금액만큼 매수
                    # ------------------------------------------------------------------
                    available_amt = upbit.get_krwbal()['available_krw']

                    if buy_amt == 'M':
                        buy_amt = available_amt

                    # ------------------------------------------------------------------
                    # 입력 금액이 주문 가능금액보다 작으면 종료
                    # ------------------------------------------------------------------
                    if Decimal(str(available_amt)) < Decimal(str(buy_amt)):
                        logging.info('주문 가능금액[' + str(available_amt) + ']이 입력한 주문금액[' + str(buy_amt) + '] 보다 작습니다.')
                        continue

                    # ------------------------------------------------------------------
                    # 최소 주문 금액(업비트 기준 5000원) 이상일 때만 매수로직 수행 ---- 10000원으로 올림
                    # ------------------------------------------------------------------
                    if Decimal(str(buy_amt)) < Decimal(str(upbit.min_order_amt)):
                        logging.info('주문금액[' + str(buy_amt) + ']이 최소 주문금액[' + str(upbit.min_order_amt) + '] 보다 작습니다.')
                        continue




                # ------------------------------------------------------------------
                    # 시장가 매수
                    # 실제 매수 로직은 안전을 위해 주석처리 하였습니다.
                    # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                    # ------------------------------------------------------------------

                    logging.info('시장가 매수 시작! [' + str(target_item['market']) + ']')
                    rtn_buycoin_mp = upbit.buycoin_mp(target_item['market'], buy_amt)
                    logging.info('시장가 매수 종료! [' + str(target_item['market']) + ']')
                    logging.info(rtn_buycoin_mp)
                    continue


    # ---------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise


# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':

    # noinspection PyBroadException
    try:

        # ---------------------------------------------------------------------
        # 입력 받을 변수
        #
        # 1. 로그레벨
        #   1) 레벨 값 : D:DEBUG, E:ERROR, 그 외:INFO
        #
        # 2. 매수금액
        #   1) M : 수수료를 제외한 최대 가능 금액으로 매수
        #   2) 금액 : 입력한 금액만 매수(수수료 포함)
        #
        # 3. 매수 제외종목
        #   1) 종목코드(콤마구분자) : BTC,ETH
        # ---------------------------------------------------------------------

        # 1. 로그레벨
        log_level = 'I'#input("로그레벨(D:DEBUG, E:ERROR, 그 외:INFO) : ").upper()
        # buy_amt = 20000#input("매수금액(M:최대, 10000:1만원) : ").upper()
        buy_amtp = 10 #몇 %씩 매수할지?
        upbit.set_loglevel(log_level)

        logging.info("*********************************************************")
        logging.info("1. 로그레벨 : " + str(log_level))
        logging.info("2. 매수금액 % : 총액의 " + str(buy_amtp) + "%")
        logging.info("*********************************************************")

        # 매수 로직 시작
        start_buytrade(buy_amtp)

    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)

    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)