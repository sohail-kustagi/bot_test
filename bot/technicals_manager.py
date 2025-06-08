import pandas as pd
from models.trade_decision import TradeDecision
from datetime import timedelta


from technicals.indicator import BollingerBands, RSI, KeltnerChannels  # Ensure indicators are imported
from technicals.indicator import ATR
from technicals.indicator import MACD
from technicals.patterns import apply_patterns
 

pd.set_option('display.max_columns', None)
pd.set_option('expand_frame_repr', False)


from openfx_api.openfx_api import OpenFxApi
from models.trade_settings import TradeSettings
import constants.defs as defs

ADDROWS = 20
RSI_LOWER_LIMIT = 40.0
RSI_UPPER_LIMIT = 60.0
MIN_SL_DISTANCE = 2.0  # Set a reasonable minimum SL distance for XAUUSD

def apply_signal(row, trade_settings: TradeSettings):
    """
    Simple strategy:
    - Generate a BUY signal when RSI is below 30 (oversold).
    - Generate a SELL signal when RSI is above 70 (overbought).
    """
    print(f"[DEBUG] apply_signal called for row: {row['time']}, RSI: {row['RSI_14']}, SPREAD: {row['SPREAD']}")
    
    if row.SPREAD <= trade_settings.maxspread:
        if row.RSI_14 < 30:  # Oversold condition
            print(f"[DEBUG] BUY signal generated for {row['PAIR']} at {row['time']}")
            return defs.BUY
        elif row.RSI_14 > 70:  # Overbought condition
            print(f"[DEBUG] SELL signal generated for {row['PAIR']} at {row['time']}")
            return defs.SELL
    
    print(f"[DEBUG] No signal generated for {row['PAIR']} at {row['time']}")
    return defs.NONE

def apply_SL(row, trade_settings: TradeSettings):
    if row.SIGNAL == defs.BUY:
        sl_dist = max(row.GAIN / trade_settings.riskreward, MIN_SL_DISTANCE)
        return round(row.mid_c - sl_dist, 2)
    elif row.SIGNAL == defs.SELL:
        sl_dist = max(row.GAIN / trade_settings.riskreward, MIN_SL_DISTANCE)
        return round(row.mid_c + sl_dist, 2)
    return 0.0

def apply_TP(row):
    if row.SIGNAL == defs.BUY:
        return round(row.mid_c + max(row.GAIN, MIN_SL_DISTANCE), 2)
    elif row.SIGNAL == defs.SELL:
        return round(row.mid_c - max(row.GAIN, MIN_SL_DISTANCE), 2)
    return 0.0


def process_candles(df: pd.DataFrame, pair, trade_settings: TradeSettings, log_message, patterns_logger=None):
    df.reset_index(drop=True, inplace=True)
    df['PAIR'] = pair

    # Ensure required columns exist
    if 'ask_c' not in df.columns or 'bid_c' not in df.columns:
        raise ValueError("Missing required columns 'ask_c' or 'bid_c' for SPREAD calculation.")

    # Calculate SPREAD
    df['SPREAD'] = df.ask_c - df.bid_c
    print("[DEBUG] SPREAD column added. Sample values:", df['SPREAD'].head())

    # --- Add this debug block here ---
    neg_spread = df[df['ask_c'] < df['bid_c']]
    if not neg_spread.empty:
        print("[WARNING] Negative spread detected! Sample rows:")
        print(neg_spread[['time', 'ask_c', 'bid_c', 'SPREAD']].tail())
    # --- End debug block ---

    # Require enough data for indicators
    required_rows = max(trade_settings.rsi_period, trade_settings.n_ma, 200) + 50  # Add a buffer
    if len(df) < required_rows:
        print(f"[DEBUG] Not enough rows for indicators. Have {len(df)}, need {required_rows}")
        return None

    # Continue with indicator calculations
    print("[DEBUG] Before apply_patterns")
    df = apply_patterns(df)
    print("[DEBUG] After apply_patterns")

    print("[DEBUG] Before BollingerBands")
    df = BollingerBands(df, trade_settings)
    print("[DEBUG] After BollingerBands")

    df = RSI(df, trade_settings)
    print(f"[DEBUG] RSI calculated:\n{df[['time', f'RSI_{trade_settings.rsi_period}']].tail()}")
    df['EMA_200'] = df.mid_c.ewm(span=200, min_periods=200).mean()
    print(f"[DEBUG] EMA calculated:\n{df[['time', 'EMA_200']].tail()}")

    print(f"[DEBUG] DataFrame after recalculating indicators:\n{df.tail()}")

    df['GAIN'] = abs(df.mid_c - df.BB_MA)
    df['SIGNAL'] = df.apply(apply_signal, axis=1, trade_settings=trade_settings)
    df['TP'] = df.apply(apply_TP, axis=1)
    df['SL'] = df.apply(apply_SL, axis=1, trade_settings=trade_settings)  # <-- Calculate SL before LOSS
    df['LOSS'] = abs(df.mid_c - df.SL)                                   # <-- Now LOSS can use SL

    # After pattern calculation and before returning, log patterns if logger is provided
    pattern_cols = [
        'HANGING_MAN', 'SHOOTING_STAR', 'SPINNING_TOP', 'MARUBOZU', 'ENGULFING',
        'TWEEZER_TOP', 'TWEEZER_BOTTOM', 'MORNING_STAR', 'EVENING_STAR',
        'PIERCING_LINE', 'PIN_BAR', 'THREE_WHITE_SOLDIERS'
    ]

    if patterns_logger:
        patterns_to_log = [col for col in pattern_cols if col in df.columns]
        patterns_logger(f"patterns [{pair}]:\n{df[patterns_to_log + ['time']].tail()}")

    print("[DEBUG] process_candles completed")
    log_cols = ['PAIR', 'time', 'mid_c', 'mid_o', 'SL', 'TP', 'SPREAD', 'GAIN', 'LOSS', 'SIGNAL']
    log_message(f"process_candles [{pair}]:\n{df[log_cols].tail()}")

    return df[log_cols].iloc[-1]


def fetch_candles(pair, row_count, candle_time, granularity,
                    api: OpenFxApi, log_message):

    df = api.get_candles_df(pair, count=row_count, granularity=granularity)

    if df is None or df.empty:
        log_message("tech_manager fetch_candles failed to get candles", pair)
        return None

    # Prefer exact match first
    if candle_time in df['time'].values:
        df = df[df['time'] <= candle_time]
        return df

    # If not exact match, allow last row to be slightly newer (1 min tolerance)
    latest_time = df.iloc[-1]['time']
    if latest_time <= candle_time + timedelta(minutes=1):
        log_message(f"tech_manager fetch_candles: used {latest_time} instead of {candle_time}", pair)
        df = df[df['time'] <= latest_time]
        return df

    log_message(f"tech_manager fetch_candles: no candles found <= {candle_time} or near it", pair)
    return None


def get_trade_decision(candle_time, pair, granularity, api: OpenFxApi, 
                            trade_settings: TradeSettings, log_message):
    max_rows = max(trade_settings.n_ma + ADDROWS, 50)

    log_message(f"tech_manager: max_rows:{max_rows} candle_time:{candle_time} granularity:{granularity}", pair)

    df = fetch_candles(pair, max_rows, candle_time, granularity, api, log_message)

    if df is not None:
        last_row = process_candles(df, pair, trade_settings, log_message)
        signal = last_row['SIGNAL']
        if signal == defs.BUY or signal == defs.SELL:
            print(f"Placing {signal} order for {pair} at {last_row['time']}")
        return TradeDecision(last_row)

    return None


