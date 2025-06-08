import pandas as pd


def EMA(df: pd.DataFrame, period: int):
    """
    Calculate the Exponential Moving Average (EMA) for a given period.
    :param df: DataFrame containing the 'mid_c' column.
    :param period: Period for the EMA calculation.
    :return: DataFrame with the EMA column added.
    """
    print(f"[DEBUG] Calculating EMA for period {period}. DataFrame length: {len(df)}")
    if 'mid_c' not in df.columns:
        raise ValueError("DataFrame must contain a 'mid_c' column for EMA calculation.")
    if len(df) < period:
        print(f"[WARNING] Not enough data to calculate EMA. Required: {period}, Available: {len(df)}")
        df[f'EMA_{period}'] = None
        return df
    df[f'EMA_{period}'] = df['mid_c'].ewm(span=period, min_periods=period).mean()
    return df


def BollingerBands(df: pd.DataFrame, trade_settings):
    """
    Calculate Bollinger Bands.
    :param df: DataFrame containing the 'mid_c', 'mid_h', and 'mid_l' columns.
    :param trade_settings: Object containing Bollinger Bands settings (n_ma, n_std).
    :return: DataFrame with Bollinger Bands columns added.
    """
    print(f"[DEBUG] Calculating Bollinger Bands. DataFrame length: {len(df)}")
    n = trade_settings.n_ma  # Get Bollinger Bands period from TradeSettings
    s = trade_settings.n_std  # Get standard deviation multiplier

    if not {'mid_c', 'mid_h', 'mid_l'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'mid_c', 'mid_h', and 'mid_l' columns for Bollinger Bands calculation.")
    if len(df) < n:
        print(f"[WARNING] Not enough data to calculate Bollinger Bands. Required: {n}, Available: {len(df)}")
        df['BB_MA'], df['BB_UP'], df['BB_LW'] = None, None, None
        return df

    typical_p = (df.mid_c + df.mid_h + df.mid_l) / 3
    stddev = typical_p.rolling(window=n, min_periods=n).std()
    df['BB_MA'] = typical_p.rolling(window=n, min_periods=n).mean()
    df['BB_UP'] = df['BB_MA'] + stddev * s
    df['BB_LW'] = df['BB_MA'] - stddev * s
    return df


def ATR(df: pd.DataFrame, n=14):
    """
    Calculate the Average True Range (ATR).
    :param df: DataFrame containing the 'mid_h', 'mid_l', and 'mid_c' columns.
    :param n: Period for the ATR calculation.
    :return: DataFrame with the ATR column added.
    """
    if not {'mid_h', 'mid_l', 'mid_c'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'mid_h', 'mid_l', and 'mid_c' columns for ATR calculation.")
    if len(df) < n:
        print(f"[WARNING] Not enough data to calculate ATR. Required: {n}, Available: {len(df)}")
        df[f"ATR_{n}"] = None
        return df

    prev_c = df.mid_c.shift(1)
    tr1 = df.mid_h - df.mid_l
    tr2 = abs(df.mid_h - prev_c)
    tr3 = abs(prev_c - df.mid_l)
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    df[f"ATR_{n}"] = tr.rolling(window=n, min_periods=n).mean()
    return df


def KeltnerChannels(df: pd.DataFrame, trade_settings):
    """
    Calculate Keltner Channels.
    :param df: DataFrame containing the 'mid_c' column.
    :param trade_settings: Object containing Keltner Channel settings (ema_period).
    :return: DataFrame with Keltner Channels columns added.
    """
    if 'mid_c' not in df.columns:
        raise ValueError("DataFrame must contain a 'mid_c' column for Keltner Channels calculation.")

    n_ema = trade_settings.ema_period  # Get EMA period from TradeSettings
    n_atr = 10  # Keeping ATR period fixed, but you can add it to settings if needed

    if len(df) < n_ema or len(df) < n_atr:
        print(f"[WARNING] Not enough data to calculate Keltner Channels. Required: {max(n_ema, n_atr)}, Available: {len(df)}")
        df['EMA'], df['KeUp'], df['KeLo'] = None, None, None
        return df

    df['EMA'] = df.mid_c.ewm(span=n_ema, min_periods=n_ema).mean()
    df = ATR(df, n=n_atr)
    c_atr = f"ATR_{n_atr}"
    df['KeUp'] = df[c_atr] * 2 + df.EMA
    df['KeLo'] = df.EMA - df[c_atr] * 2
    df.drop(c_atr, axis=1, inplace=True)
    return df


def RSI(df: pd.DataFrame, trade_settings):
    """
    Calculate the Relative Strength Index (RSI).
    :param df: DataFrame containing the 'mid_c' column.
    :param trade_settings: Object containing RSI settings (rsi_period).
    :return: DataFrame with the RSI column added.
    """
    print(f"[DEBUG] Calculating RSI for period {trade_settings.rsi_period}. DataFrame length: {len(df)}")
    if 'mid_c' not in df.columns:
        raise ValueError("DataFrame must contain a 'mid_c' column for RSI calculation.")

    n = trade_settings.rsi_period  # Get RSI period from TradeSettings
    if len(df) < n:
        print(f"[WARNING] Not enough data to calculate RSI. Required: {n}, Available: {len(df)}")
        df[f"RSI_{n}"] = None
        return df

    gains = df.mid_c.diff()
    wins = gains.where(gains > 0, 0.0)
    losses = -gains.where(gains < 0, 0.0)

    avg_gain = wins.rolling(window=n, min_periods=n).mean()
    avg_loss = losses.rolling(window=n, min_periods=n).mean()

    rs = avg_gain / avg_loss
    df[f"RSI_{n}"] = 100.0 - (100.0 / (1.0 + rs))
    return df


def MACD(df: pd.DataFrame, n_slow=26, n_fast=12, n_signal=9):
    """
    Calculate the Moving Average Convergence Divergence (MACD).
    :param df: DataFrame containing the 'mid_c' column.
    :param n_slow: Period for the slow EMA.
    :param n_fast: Period for the fast EMA.
    :param n_signal: Period for the signal line.
    :return: DataFrame with MACD, Signal, and Histogram columns added.
    """
    if 'mid_c' not in df.columns:
        raise ValueError("DataFrame must contain a 'mid_c' column for MACD calculation.")
    if len(df) < max(n_slow, n_fast, n_signal):
        print(f"[WARNING] Not enough data to calculate MACD. Required: {max(n_slow, n_fast, n_signal)}, Available: {len(df)}")
        df['MACD'], df['SIGNAL'], df['HIST'] = None, None, None
        return df

    ema_long = df.mid_c.ewm(span=n_slow, min_periods=n_slow).mean()
    ema_short = df.mid_c.ewm(span=n_fast, min_periods=n_fast).mean()

    df['MACD'] = ema_short - ema_long
    df['SIGNAL'] = df['MACD'].ewm(span=n_signal, min_periods=n_signal).mean()
    df['HIST'] = df['MACD'] - df['SIGNAL']

    return df