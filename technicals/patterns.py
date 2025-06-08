import pandas as pd

# Constants for pattern detection
HANGING_MAN_BODY = 15.0
HANGING_MAN_HEIGHT = 75.0
SHOOTING_STAR_HEIGHT = 25.0
SPINNING_TOP_MIN = 40.0
SPINNING_TOP_MAX = 60.0
MARUBOZU = 98.0
ENGULFING_FACTOR = 1.1
PIERCING_LINE_FACTOR = 0.5
MORNING_STAR_PREV2_BODY = 90.0
MORNING_STAR_PREV_BODY = 10.0
TWEEZER_BODY = 15.0
TWEEZER_HL = 0.01
TWEEZER_TOP_BODY = 40.0
TWEEZER_BOTTOM_BODY = 60.0
PIN_BAR_SHADOW_RATIO = 2.0  # Shadow must be 2x the body

def apply_hanging_man(row):
    return row.body_bottom_perc > HANGING_MAN_HEIGHT and row.body_perc < HANGING_MAN_BODY

def apply_shooting_star(row):
    return row.body_top_perc < SHOOTING_STAR_HEIGHT and row.body_perc < HANGING_MAN_BODY

def apply_spinning_top(row):
    return SPINNING_TOP_MIN < row.body_bottom_perc < SPINNING_TOP_MAX and row.body_perc < HANGING_MAN_BODY

def apply_engulfing(row):
    return row.direction != row.direction_prev and row.body_size > row.body_size_prev * ENGULFING_FACTOR

def apply_tweezer_top(row):
    return (
        abs(row.body_size_change) < TWEEZER_BODY
        and row.direction == -1 and row.direction != row.direction_prev
        and abs(row.low_change) < TWEEZER_HL and abs(row.high_change) < TWEEZER_HL
        and row.body_top_perc < TWEEZER_TOP_BODY
    )

def apply_tweezer_bottom(row):
    return (
        abs(row.body_size_change) < TWEEZER_BODY
        and row.direction == 1 and row.direction != row.direction_prev
        and abs(row.low_change) < TWEEZER_HL and abs(row.high_change) < TWEEZER_HL
        and row.body_bottom_perc > TWEEZER_BOTTOM_BODY
    )

def apply_morning_star(row, direction=1):
    return (
        row.body_perc_prev_2 > MORNING_STAR_PREV2_BODY
        and row.body_perc_prev < MORNING_STAR_PREV_BODY
        and row.direction == direction
        and row.direction_prev_2 != direction
        and (
            (direction == 1 and row.mid_c > row.mid_point_prev_2) or
            (direction == -1 and row.mid_c < row.mid_point_prev_2)
        )
    )

def apply_piercing_line(row):
    return (
        row.direction_prev == -1 and row.direction == 1
        and row.open_price < row.close_price_prev
        and row.close_price > row.mid_point_prev
    )

def apply_three_white_soldiers(df):
    df["THREE_WHITE_SOLDIERS"] = False  # Initialize column
    for i in range(2, len(df)):
        if (
            df.iloc[i - 2].direction == 1
            and df.iloc[i - 1].direction == 1
            and df.iloc[i].direction == 1
            and df.iloc[i - 1].open_price > df.iloc[i - 2].close_price
            and df.iloc[i].open_price > df.iloc[i - 1].close_price
        ):
            df.loc[df.index[i], "THREE_WHITE_SOLDIERS"] = True
    return df

# Pin Bar Detection
def apply_pin_bar(row):
    upper_shadow = row.mid_h - row.body_upper
    lower_shadow = row.body_lower - row.mid_l
    body = row.body_size

    # Bullish Pin Bar (Long Lower Shadow)
    bullish_pin_bar = lower_shadow > PIN_BAR_SHADOW_RATIO * body and upper_shadow < body

    # Bearish Pin Bar (Long Upper Shadow)
    bearish_pin_bar = upper_shadow > PIN_BAR_SHADOW_RATIO * body and lower_shadow < body

    return bullish_pin_bar or bearish_pin_bar

def apply_candle_props(df: pd.DataFrame):
    df_an = df.copy()
    df_an['direction'] = df_an.mid_c - df_an.mid_o
    df_an['body_size'] = abs(df_an['direction'])
    df_an['direction'] = df_an['direction'].apply(lambda x: 1 if x >= 0 else -1)
    df_an['full_range'] = df_an.mid_h - df_an.mid_l

    # Avoid division by zero
    epsilon = 1e-9
    safe_range = df_an['full_range'].replace(0, epsilon)

    df_an['body_perc'] = (df_an.body_size / safe_range) * 100
    df_an['body_lower'] = df_an[['mid_c', 'mid_o']].min(axis=1)
    df_an['body_upper'] = df_an[['mid_c', 'mid_o']].max(axis=1)
    df_an['body_bottom_perc'] = ((df_an['body_lower'] - df_an.mid_l) / safe_range) * 100
    df_an['body_top_perc'] = 100 - (((df_an.mid_h - df_an['body_upper']) / safe_range) * 100)
    df_an['mid_point'] = df_an.full_range / 2 + df_an.mid_l
    df_an['low_change'] = df_an.mid_l.pct_change() * 100
    df_an['high_change'] = df_an.mid_h.pct_change() * 100
    df_an['body_size_change'] = df_an.body_size.pct_change() * 100

    # Adding missing shifted columns
    df_an['mid_point_prev'] = df_an.mid_point.shift(1)
    df_an['mid_point_prev_2'] = df_an.mid_point.shift(2)  # FIX MISSING COLUMN
    df_an['body_size_prev'] = df_an.body_size.shift(1)
    df_an['direction_prev'] = df_an.direction.shift(1)
    df_an['direction_prev_2'] = df_an.direction.shift(2)  # FIX MISSING COLUMN
    df_an['body_perc_prev'] = df_an.body_perc.shift(1)
    df_an['body_perc_prev_2'] = df_an.body_perc.shift(2)  # FIX MISSING COLUMN
    df_an['close_price_prev'] = df_an.mid_c.shift(1)
    df_an['open_price'] = df_an.mid_o
    df_an['close_price'] = df_an.mid_c
    
    return df_an

def set_candle_patterns(df_an: pd.DataFrame):
    df_an['HANGING_MAN'] = df_an.apply(apply_hanging_man, axis=1)
    df_an['SHOOTING_STAR'] = df_an.apply(apply_shooting_star, axis=1)
    df_an['SPINNING_TOP'] = df_an.apply(apply_spinning_top, axis=1)
    df_an['MARUBOZU'] = df_an.body_perc > MARUBOZU
    df_an['ENGULFING'] = df_an.apply(apply_engulfing, axis=1)
    df_an['TWEEZER_TOP'] = df_an.apply(apply_tweezer_top, axis=1)
    df_an['TWEEZER_BOTTOM'] = df_an.apply(apply_tweezer_bottom, axis=1)
    df_an['MORNING_STAR'] = df_an.apply(apply_morning_star, axis=1)
    df_an['EVENING_STAR'] = df_an.apply(apply_morning_star, axis=1, direction=-1)
    df_an['PIERCING_LINE'] = df_an.apply(apply_piercing_line, axis=1)
    df_an['PIN_BAR'] = df_an.apply(apply_pin_bar, axis=1)  # Added Pin Bar Pattern
    df_an = apply_three_white_soldiers(df_an)
    return df_an

def apply_patterns(df: pd.DataFrame):
    df_an = apply_candle_props(df)
    df_an = set_candle_patterns(df_an)
    return df_an