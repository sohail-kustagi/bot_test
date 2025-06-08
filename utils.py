import pandas as pd

def preprocess_rolling_data(df):
    """
    Preprocess the rolling data to handle NaN values in indicators.
    :param df: DataFrame containing rolling data with indicators.
    :return: Cleaned DataFrame with NaN values filled or dropped.
    """
    required_columns = ['EMA_200', 'RSI_14', 'BB_UP', 'BB_LW', 'BB_MA']  # <-- Added 'BB_MA'

    # Add missing columns with default values (e.g., NaN)
    for col in required_columns:
        if col not in df.columns:
            df[col] = None  # Initialize missing columns with NaN

    # Replace NaN values with 0 for required indicators
    df[required_columns] = df[required_columns].fillna(0)

    # Log a warning if NaN values were replaced
    if df[required_columns].isna().any().any():
        print(f"[WARNING] NaN values replaced with 0 in rolling data.")

    return df