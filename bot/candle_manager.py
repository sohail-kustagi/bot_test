import os
import pandas as pd
from datetime import datetime, timedelta
from openfx_api.openfx_api import OpenFxApi
from models.candle_timing import CandleTiming
from infrastructure.collect_data import run_collection_for_pair
from utils import preprocess_rolling_data
from models.api_price import ApiPrice


class CandleManager:
    def __init__(self, api: OpenFxApi, trade_settings, log_message, granularity: str):
        """
        Initialize the CandleManager.
        :param api: OpenFxApi instance for fetching candles.
        :param trade_settings: Dictionary of TradeSettings objects for each pair.
        :param log_message: Logging function.
        :param granularity: Granularity of the candles (e.g., "M1").
        """
        self.api = api
        self.trade_settings = trade_settings
        self.log_message = log_message
        self.granularity = granularity
        self.pairs_list = list(self.trade_settings.keys())
        self.data_dir = "./data/"
        self.rolling_data_files = {p: f"{self.data_dir}{p}_{self.granularity}_rolling.pkl" for p in self.pairs_list}
        self.timings = {p: CandleTiming(self.api.last_complete_candle(p, self.granularity)) for p in self.pairs_list}

        # Ensure the data directory exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self.log_message(f"[INFO] Created data directory: {self.data_dir}")

        # Initialize rolling data files for all pairs
        for pair, file_path in self.rolling_data_files.items():
            if not os.path.exists(file_path):
                self.initialize_rolling_data(pair)

        for p, t in self.timings.items():
            self.log_message(f"CandleManager() init last_candle:{t} for pair {p}")

    def initialize_rolling_data(self, pair: str):
        """
        Initialize rolling data for a trading pair using the run_collection_for_pair function.
        Fetch enough candles to cover the largest required period for indicators.
        """
        self.log_message(f"[INFO] Initializing rolling data for {pair}")

        # Define the start and end dates for data collection
        end_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        start_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")  # Fetch 2 days of data

        # File path for saving the rolling data
        file_prefix = "./data/"

        try:
            run_collection_for_pair(
                pair=pair,
                granularity=self.granularity,
                start_date=start_date,
                end_date=end_date,
                file_prefix=file_prefix,
                api=self.api
            )
            rolling_data_path = self.rolling_data_files[pair]
            if os.path.exists(rolling_data_path):
                self.log_message(f"[INFO] Rolling data file created: {rolling_data_path}")
            else:
                self.log_message(f"[WARNING] Rolling data file not created for {pair}.")
        except Exception as e:
            self.log_message(f"[ERROR] Failed to initialize rolling data for {pair}: {e}")

    def update_rolling_data(self, pair: str):
        """
        Update the rolling data file with new candles for a trading pair.
        """
        file_path = self.rolling_data_files[pair]

        # Check if the rolling data file exists
        if os.path.exists(file_path):
            try:
                rolling_data = pd.read_pickle(file_path)
                self.log_message(f"[DEBUG] Rolling data size before update for {pair}: {len(rolling_data)} rows")
                if rolling_data.empty or len(rolling_data) < 300:
                    self.log_message(f"[WARNING] Rolling data file for {pair} contains insufficient candles. Reinitializing...")
                    self.initialize_rolling_data(pair)
                    return
            except Exception as e:
                self.log_message(f"[ERROR] Failed to load rolling data for {pair}: {e}")
                self.initialize_rolling_data(pair)
                return
        else:
            self.log_message(f"[DEBUG] Rolling data file not found for {pair}. Initializing...")
            self.initialize_rolling_data(pair)
            return

        # Add this validation before proceeding
        settings = self.trade_settings[pair]
        if len(rolling_data) < max(settings.rsi_period, settings.n_ma, 200):
            self.log_message(f"[DEBUG] Not enough rows for indicators. Have {len(rolling_data)}, need {max(settings.rsi_period, settings.n_ma, 200)}")
            return

        # Fetch new candles starting from the last timestamp
        last_timestamp = rolling_data['time'].max() if not rolling_data.empty else None
        self.log_message(f"[DEBUG] Last timestamp in rolling data for {pair}: {last_timestamp}")

        # Calculate the start date for fetching new candles
        if last_timestamp is not None:
            start_date = last_timestamp + timedelta(minutes=1)  # Start from the next minute
        else:
            start_date = datetime.utcnow() - timedelta(hours=5)  # Default to 5 hours back

        end_date = datetime.utcnow()
        self.log_message(f"[DEBUG] Fetching new candles for {pair} from {start_date} to {end_date}")

        # Fetch new candles from the API
        try:
            new_candles = self.api.get_candles_df(
                pair, granularity=self.granularity, date_f=start_date.isoformat(), date_t=end_date.isoformat()
            )
        except Exception as e:
            self.log_message(f"[ERROR] Failed to fetch new candles for {pair}: {e}")
            return

        if new_candles is not None and not new_candles.empty:
            self.log_message(f"[DEBUG] Fetched {len(new_candles)} new candles for {pair}.")

            # Append new candles and maintain a rolling window of 500 candles
            rolling_data = pd.concat([rolling_data, new_candles]).drop_duplicates(subset=['time']).reset_index(drop=True)
            rolling_data = rolling_data.tail(500).reset_index(drop=True)
            self.log_message(f"[DEBUG] Rolling data size after update for {pair}: {len(rolling_data)} rows")

            rolling_data = preprocess_rolling_data(rolling_data)  # Handle NaN values

            # Save updated rolling data
            try:
                rolling_data.to_pickle(file_path)
                self.log_message(f"[DEBUG] Rolling data saved to {file_path}.")
            except Exception as e:
                self.log_message(f"[ERROR] Failed to save rolling data for {pair}: {e}")
        else:
            self.log_message(f"[ERROR] No new candles fetched for {pair}.")

    def update_rolling_data_with_live_prices(self, pair: str, live_price):
        """
        Update the rolling data file with live price updates for a trading pair.
        """
        file_path = self.rolling_data_files[pair]
        try:
            rolling_data = pd.read_pickle(file_path) if os.path.exists(file_path) else pd.DataFrame()
        except Exception as e:
            self.log_message(f"[ERROR] Failed to load rolling data for {pair}: {e}")
            rolling_data = pd.DataFrame()

        self.log_message(f"[DEBUG] Rolling data size before appending live price for {pair}: {len(rolling_data)} rows")

        # Convert live_price to ApiPrice if it's a dictionary
        if isinstance(live_price, dict):
            live_price = ApiPrice(live_price)

        # Extract live price data
        bid = live_price.bid
        ask = live_price.ask
        mid = (bid + ask) / 2
        timestamp = live_price.time

        # Check if the current timestamp already exists in the rolling data
        if not rolling_data.empty and rolling_data['time'].iloc[-1] == timestamp:
            # Update the current row (high, low, close)
            rolling_data.at[len(rolling_data) - 1, 'bid_h'] = max(rolling_data.iloc[-1]['bid_h'], bid)
            rolling_data.at[len(rolling_data) - 1, 'bid_l'] = min(rolling_data.iloc[-1]['bid_l'], bid)
            rolling_data.at[len(rolling_data) - 1, 'bid_c'] = bid
            rolling_data.at[len(rolling_data) - 1, 'ask_h'] = max(rolling_data.iloc[-1]['ask_h'], ask)
            rolling_data.at[len(rolling_data) - 1, 'ask_l'] = min(rolling_data.iloc[-1]['ask_l'], ask)
            rolling_data.at[len(rolling_data) - 1, 'ask_c'] = ask
            rolling_data.at[len(rolling_data) - 1, 'mid_h'] = max(rolling_data.iloc[-1]['mid_h'], mid)
            rolling_data.at[len(rolling_data) - 1, 'mid_l'] = min(rolling_data.iloc[-1]['mid_l'], mid)
            rolling_data.at[len(rolling_data) - 1, 'mid_c'] = mid
        else:
            # Create a new row for the new timestamp
            new_row = {
                "time": timestamp,
                "bid_o": bid,
                "bid_h": bid,
                "bid_l": bid,
                "bid_c": bid,
                "ask_o": ask,
                "ask_h": ask,
                "ask_l": ask,
                "ask_c": ask,
                "mid_o": mid,
                "mid_h": mid,
                "mid_l": mid,
                "mid_c": mid,
            }
            rolling_data = pd.concat([rolling_data, pd.DataFrame([new_row])], ignore_index=True)

        # Maintain a rolling window of 500 rows
        rolling_data = rolling_data.tail(500).reset_index(drop=True)

        self.log_message(f"[DEBUG] Rolling data size after appending live price for {pair}: {len(rolling_data)} rows")

        # Save the updated rolling data
        try:
            rolling_data.to_pickle(file_path)
            self.log_message(f"[DEBUG] Live price data appended and saved to {file_path}.")
        except Exception as e:
            self.log_message(f"[ERROR] Failed to save live price data for {pair}: {e}")

    def update_timings(self):
        """
        Check for new candles and update rolling data.
        :return: List of pairs with new candles detected.
        """
        triggered = []

        for pair in self.pairs_list:
            current = self.api.last_complete_candle(pair, self.granularity)
            self.log_message(f"[DEBUG] CandleManager {pair} current:{current} last:{self.timings[pair].last_time}")

            if current is None:
                self.log_message("Unable to get candle", pair)
                continue

            self.timings[pair].is_ready = False
            if current > self.timings[pair].last_time:
                self.timings[pair].is_ready = True
                self.timings[pair].last_time = current
                self.log_message(f"CandleManager() new candle:{self.timings[pair]}", pair)
                self.log_message(f"[DEBUG] New candle detected for {pair}. Updating rolling data...")
                triggered.append(pair)

                # Update rolling data for the pair
                self.update_rolling_data(pair)

        return triggered