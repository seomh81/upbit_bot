import time
import os
import sys
import logging
import traceback
import pandas as pd
import numpy

from decimal import Decimal

# 공통 모듈 Import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module.old import oldupbit


# -----------------------------------------------------------------------------
# - Name : start_selltrade
# - Desc : 매도 로직
# - Input
# 1) sell_pcnt : 매도 수익률
# 2) dcnt_pcnt : 고점대비 하락률
# -----------------------------------------------------------------------------
def start_selltrade(sell_pcnt, dcnt_pcnt):
    try:

        # ----------------------------------------------------------------------
        # 반복 수행
        # ----------------------------------------------------------------------
        while True:

            # ------------------------------------------------------------------
            # 보유 종목조회
            # ------------------------------------------------------------------
            target_items = upbit.get_accounts('Y', 'KRW')

            # ------------------------------------------------------------------
            # 보유 종목 현재가 조회
            # ------------------------------------------------------------------
            target_items_comma = upbit.chg_account_to_comma(target_items)
            tickers = oldupbit.get_ticker(target_items_comma)

            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # -----------------------------------------------------------------
            for target_item in target_items:
                for ticker in tickers:
                    time.sleep(0.1)
                    if target_item['market'] == ticker['market']:

                        # -----------------------------------------------------
                        # 수익률 계산
                        # ((현재가 - 평균매수가) / 평균매수가) * 100
                        # -----------------------------------------------------
                        rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(
                            str(target_item['avg_buy_price']))) / Decimal(str(target_item['avg_buy_price']))) * 100, 2)

                        logging.info('')
                        logging.info('------------------------------------------------------')
                        logging.info('- 종목:' + str(target_item['market']))
                        logging.info('- 평균매수가:' + str(target_item['avg_buy_price']))
                        logging.info('- 현재가:' + str(ticker['trade_price']))
                        logging.info('- 수익률:' + str(rev_pcnt))

                        # -----------------------------------------------------
                        # 현재 수익률이 매도 수익률 이상인 경우에만 진행
                        # -----------------------------------------------------
                        if Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)):
                            logging.info('- 현재 수익률이 매도 수익률 보다 낮아 진행하지 않음!!!')
                            logging.info('------------------------------------------------------')
                            continue

                        # -------------------------------------------------
                        # 고점을 계산하기 위해 최근 매수일자 조회
                        # 1. 해당 종목에 대한 거래 조회(done, cancel)
                        # 2. 거래일시를 최근순으로 정렬
                        # 3. 매수 거래만 필터링
                        # 4. 가장 최근 거래일자부터 현재까지 고점을 조회
                        # -------------------------------------------------
                        order_done = oldupbit.get_order_status(target_item['market'], 'done') + upbit.get_order_status(
                            target_item['market'], 'cancel')
                        order_done_sorted = oldupbit.orderby_dict(order_done, 'created_at', True)
                        order_done_filtered = oldupbit.filter_dict(order_done_sorted, 'side', 'bid')

                        # ------------------------------------------------------------------
                        # 캔들 조회
                        # ------------------------------------------------------------------
                        candles = upbit.get_candle(target_item['market'], '15', 200)

                        # ------------------------------------------------------------------
                        # 최근 매수일자 다음날부터 현재까지의 최고가를 계산
                        # ------------------------------------------------------------------
                        df = pd.DataFrame(candles)
                        mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                        filtered_df = df.loc[mask]

                        higest_high_price = numpy.max(filtered_df['high_price'])

                        # -----------------------------------------------------
                        # 고점대비 하락률
                        # ((현재가 - 최고가) / 최고가) * 100
                        # -----------------------------------------------------
                        cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(
                            str(higest_high_price))) / Decimal(str(higest_high_price))) * 100, 2)

                        logging.info('- 매수 후 최고가:' + str(higest_high_price))
                        logging.info('- 고점대비 하락률:' + str(cur_dcnt_pcnt))

                        if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(dcnt_pcnt)):

                            # ------------------------------------------------------------------
                            # 시장가 매도
                            # 실제 매도 로직은 안전을 위해 주석처리 하였습니다.
                            # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                            # ------------------------------------------------------------------
                            logging.info('시장가 매도 시작! [' + str(target_item['market']) + ']')
                            rtn_sellcoin_mp = upbit.sellcoin_mp(target_item['market'], 'Y')
                            logging.info('시장가 매도 종료! [' + str(target_item['market']) + ']')
                            logging.info(rtn_sellcoin_mp)
                            logging.info('------------------------------------------------------')

                        else:
                            logging.info('- 고점 대비 하락률 조건에 맞지 않아 매도하지 않음!!!')
                            logging.info('------------------------------------------------------')


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
        # 2. 매도 수익률
        #   1) 2% = 2로 입력
        #
        # 3. 고점대비 하락률
        #   1) 1% = 1로 입력
        # ---------------------------------------------------------------------

        # 1. 로그레벨
        log_level = 'I'#input("로그레벨(D:DEBUG, E:ERROR, 그 외:INFO) : ").upper()
        sell_pcnt = -1#input("매도 수익률(ex:2%=2) : ")
        dcnt_pcnt = -1#input("고점대비 하락률(ex:-1%=-1) : ")

        oldupbit.set_loglevel(log_level)

        logging.info("*********************************************************")
        logging.info("1. 로그레벨 : " + str(log_level))
        logging.info("2. 매도 수익률 : " + str(sell_pcnt))
        logging.info("3. 고점대비 하락률 : " + str(dcnt_pcnt))
        logging.info("*********************************************************")

        # 매수 로직 시작
        start_selltrade(sell_pcnt, dcnt_pcnt)


    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)

    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)