import pandas as pd
import datetime as dt
from dateutil import parser

from infrastructure.instrument_collection import InstrumentCollection
from openfx_api.openfx_api import OpenFxApi

import time

CANDLE_COUNT = 900  # Number of candles to fetch in one API call

INCREMENTS = {
    'M1': 1 * CANDLE_COUNT,
    'M5': 5 * CANDLE_COUNT,
    'H1': 60 * CANDLE_COUNT,
    'H4': 240 * CANDLE_COUNT
} 

SLEEP = 0.2  # Sleep time between API calls to avoid rate limits


def save_file(final_df: pd.DataFrame, file_prefix, granularity, pair):
    """Save the final DataFrame to a .pkl file."""
    filename = f"{file_prefix}{pair}_{granularity}_rolling.pkl"

    final_df.drop_duplicates(subset=['time'], inplace=True)
    final_df.sort_values(by='time', inplace=True)
    final_df.reset_index(drop=True, inplace=True)
    final_df.to_pickle(filename)

    s1 = f"*** {pair} {granularity} {final_df.time.min()} {final_df.time.max()}"
    print(f"*** {s1} --> {final_df.shape[0]} candles ***")


def fetch_candles(pair, granularity, date_f: dt.datetime, api: OpenFxApi):
    """Fetch candles for a given pair, granularity, and start date."""
    attempts = 0
    candles_df = None

    while attempts < 3:  # Retry up to 3 times
        candles_df = api.get_candles_df(
            pair,
            granularity=granularity,
            count=CANDLE_COUNT,
            date_f=date_f,
        )

        if candles_df is not None:
            break

        attempts += 1
        print(f"Retrying fetch_candles for {pair} {granularity}... Attempt {attempts}")
        time.sleep(SLEEP)

    if candles_df is not None and not candles_df.empty:
        return candles_df
    else:
        print(f"Failed to fetch candles for {pair} {granularity} starting from {date_f}.")
        return None


def collect_data(pair, granularity, date_f, date_t, file_prefix, api: OpenFxApi):
    """
    Collect candle data for a given pair and granularity over a date range.
    Saves the data to a .pkl file.
    """
    time_step = INCREMENTS[granularity]

    end_date = parser.parse(date_t)
    from_date = parser.parse(date_f)

    candle_dfs = []

    to_date = from_date

    while to_date < end_date:
        to_date = from_date + dt.timedelta(minutes=time_step)
        if to_date > end_date:
            to_date = end_date

        candles = fetch_candles(
            pair,
            granularity,
            from_date,
            api
        )

        if candles is not None:
            print(f"{pair} {granularity} {from_date} {candles.time.min()} {candles.time.max()} {candles.shape[0]} candles")
            candle_dfs.append(candles)
            if candles.time.max() > to_date:
                from_date = candles.time.max()
            else:
                from_date = to_date
        else:
            print(f"{pair} {granularity} {from_date} {to_date} --> NO CANDLES")
            from_date = to_date

        time.sleep(SLEEP)

    if len(candle_dfs) > 0:
        final_df = pd.concat(candle_dfs)
        save_file(final_df, file_prefix, granularity, pair)
    else:
        print(f"{pair} {granularity} --> NO DATA SAVED!")


def run_collection_for_pair(pair, granularity, start_date, end_date, file_prefix, api: OpenFxApi):
    """
    Run the data collection process for a single pair and granularity.
    """
    print(f"[INFO] Initializing rolling data for {pair} with granularity {granularity}")
    try:
        collect_data(
            pair=pair,
            granularity=granularity,
            date_f=start_date,
            date_t=end_date,
            file_prefix=file_prefix,
            api=api
        )
        print(f"[INFO] Rolling data for {pair} with granularity {granularity} saved successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize rolling data for {pair}: {e}")


def run_collection(ic: InstrumentCollection, api: OpenFxApi):
    """
    Run the data collection process for all pairs and granularities.
    """
    our_curr = ["XAU", "USD"]  # Example currencies
    for p1 in our_curr:
        for p2 in our_curr:
            pair = f"{p1}{p2}"
            if pair in ic.instruments_dict.keys():
                for granularity in ["M1", "M5", "H1"]:  # Add granularities as needed
                    print(pair, granularity)
                    collect_data(
                        pair,
                        granularity,
                        "2020-01-01T00:00:00",  # Start date
                        "2025-01-01T00:00:00",  # End date
                        "./data/",  # File prefix for saving data
                        api
                    )