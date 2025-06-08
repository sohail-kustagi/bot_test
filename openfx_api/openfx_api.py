import requests
import pandas as pd
import json
import constants.defs as defs
import time
import datetime as dt
import os

from infrastructure.instrument_collection import instrumentCollection as ic
from models.api_price import ApiPrice
from models.open_trade import OpenTrade
from infrastructure.log_wrapper import LogWrapper

LABEL_MAP = {
    'Open': 'o',
    'High': 'h',
    'Low': 'l',
    'Close': 'c',
}

THROTTLE_TIME = 0.3


class OpenFxApi:
    def __init__(self):
        """
        Initialize the OpenFxApi class.
        Sets up the session, logger, and a single instance of OandaApi.
        """
        self.session = requests.Session()
        self.session.headers.update(defs.SECURE_HEADER)
        self.last_req_time = dt.datetime.now()
        self.log = LogWrapper("OpenFxApi")
        #self.oanda_api = OandaApi()  # Ensure this attribute is properly initialized

    def throttle(self):
        """Throttle API requests to avoid hitting rate limits."""
        elapsed_time = (dt.datetime.now() - self.last_req_time).total_seconds()
        if elapsed_time < THROTTLE_TIME:
            time.sleep(THROTTLE_TIME - elapsed_time)
        self.last_req_time = dt.datetime.now()

    def save_response(self, response, filename):
        """Save the API response to a file for debugging purposes."""
        try:
            with open(filename, 'w') as file:
                d = {}
                d['local_request_date'] = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                d['response_data'] = response.json()
                file.write(json.dumps(d, indent=2))
            print(f"[DEBUG] Response saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to save response to {filename}: {e}")

    def make_request(self, url, verb='get', code=200, params=None, data=None, headers=None, save_filename=""):
        retries = 3
        full_url = f"{defs.OPENFX_URL}/{url}"
        print(f"[DEBUG] Making {verb.upper()} request to {full_url}")
        timeout = 10  # seconds
        for attempt in range(retries):
            try:
                response = None
                start_time = time.time()
                if verb == "get":
                    response = self.session.get(full_url, params=params, headers=headers, timeout=timeout)
                elif verb == "post":
                    response = self.session.post(full_url, json=data, headers=headers, timeout=timeout)
                else:
                    print(f"[ERROR] Unsupported HTTP verb: {verb}")
                    return False, None

                elapsed = time.time() - start_time
                print(f"[DEBUG] Request took {elapsed:.2f} seconds")
                print(f"[DEBUG] Raw response: {response.text if response else 'No response'}")
                print(f"[DEBUG] Status code: {response.status_code if response else 'No response'}")

                if response and response.status_code == code:
                    print(f"[DEBUG] Response content: {response.json()}")
                    if save_filename:
                        self.save_response(response, save_filename)
                    return True, response.json()
                else:
                    print(f"[ERROR] Attempt {attempt + 1}: API request failed with status code {response.status_code if response else 'None'}")
            except Exception as error:
                print(f"[ERROR] Attempt {attempt + 1}: Exception during API request: {error}")
            time.sleep(1)  # Wait before retrying
        return False, None

    def fetch_candles(self, pair_name, count=-10, granularity="M1", ts_f=None):
        """
        Fetch candle data for a given pair and granularity.
        :param pair_name: Trading pair (e.g., "XAUUSD").
        :param count: Number of candles to fetch (negative for historical data).
        :param granularity: Granularity of the candles (e.g., "M1").
        :param ts_f: Timestamp to start fetching candles from (in milliseconds).
        :return: Tuple (success, [ask_data, bid_data]).
        """
        if ts_f is None:
            ts_f = int(pd.Timestamp(dt.datetime.utcnow()).timestamp() * 1000)

        params = {
            "timestamp": ts_f,
            "count": count
        }

        base_url = f"quotehistory/{pair_name}/{granularity}/bars/"

        # Fetch bid and ask data
        ok_bid, bid_data = self.make_request(base_url + "bid", params=params, save_filename="bids.json")
        ok_ask, ask_data = self.make_request(base_url + "ask", params=params, save_filename="asks.json")

        # Log the raw responses for debugging
        print(f"[DEBUG] Bid Data: {bid_data if ok_bid else 'Failed to fetch'}")
        print(f"[DEBUG] Ask Data: {ask_data if ok_ask else 'Failed to fetch'}")

        # Check if both requests were successful
        if ok_bid and ok_ask:
            return True, [ask_data, bid_data]

        return False, None

    def get_price_dict(self, price_label: str, item):
        """Convert API response to a dictionary with OHLC data."""
        try:
            data = {"time": pd.to_datetime(item['Timestamp'], unit='ms')}
            for ohlc in LABEL_MAP.keys():
                data[f"{price_label}_{LABEL_MAP[ohlc]}"] = item[ohlc]
            return data
        except KeyError as e:
            print(f"[ERROR] Missing key in API response: {e}")
            return {}

    def get_candles_df(self, pair_name, count=-10, granularity="M1", date_f=None, date_t=None):
        """
        Fetch candle data and convert it to a DataFrame.
        """
        ts_f = int(pd.Timestamp(date_f).timestamp() * 1000) if date_f else None
        ts_t = int(pd.Timestamp(date_t).timestamp() * 1000) if date_t else None

        print(f"[DEBUG] Fetching candles for {pair_name} with granularity {granularity}")
        print(f"[DEBUG] Date range: {date_f} to {date_t}")

        ok, data = self.fetch_candles(pair_name, count=count, granularity=granularity, ts_f=ts_f)

        if not ok or data is None:
            print(f"[ERROR] Failed to fetch candles for {pair_name}")
            return None

        data_ask, data_bid = data

        if not isinstance(data_ask, dict) or not isinstance(data_bid, dict):
            print(f"[ERROR] Invalid data format for {pair_name}.")
            return None

        if "Bars" not in data_ask or "Bars" not in data_bid:
            print(f"[ERROR] Missing 'Bars' key in API response for {pair_name}")
            return None

        ask_bars = data_ask["Bars"]
        bid_bars = data_bid["Bars"]

        if len(ask_bars) == 0 or len(bid_bars) == 0:
            print(f"[ERROR] No candles found for {pair_name}")
            return None

        bids = [self.get_price_dict('bid', item) for item in bid_bars]
        asks = [self.get_price_dict('ask', item) for item in ask_bars]

        df_bid = pd.DataFrame.from_dict(bids)
        df_ask = pd.DataFrame.from_dict(asks)
        df_merged = pd.merge(left=df_bid, right=df_ask, on='time')

        # Calculate mid prices
        for i in ['_o', '_h', '_l', '_c']:
            df_merged[f"mid{i}"] = (df_merged[f"bid{i}"] + df_merged[f"ask{i}"]) / 2

        # Filter by date_t if provided
        if date_t:
            df_merged = df_merged[df_merged['time'] <= pd.Timestamp(date_t)]

        print(f"[DEBUG] Successfully fetched {len(df_merged)} candles for {pair_name}.")
        return df_merged

    def last_complete_candle(self, pair_name, granularity):
        """
        Get the timestamp of the last complete candle for a given pair and granularity.
        :param pair_name: Trading pair (e.g., "XAUUSD").
        :param granularity: Granularity of the candles (e.g., "M1").
        :return: Timestamp of the last complete candle or None if no data is available.
        """
        df = self.get_candles_df(pair_name, granularity=granularity)
        if df is None or df.shape[0] == 0:
            print(f"[ERROR] No data available for {pair_name} with granularity {granularity}.")
            return None

        # Log the DataFrame for debugging
        print(f"[DEBUG] DataFrame for last_complete_candle:\n{df.tail()}")

        return df.iloc[-1]

    def place_trade(self, pair_name: str, amount: int, direction: int, stop_loss: float = None, take_profit: float = None):
        """
        Place a trade via the API.
        """
        dir_str = "Buy" if direction == defs.BUY else "Sell"
        url = "trade"

        # Get instrument details
        instrument = ic.instruments_dict.get(pair_name)
        if not instrument:
            print(f"[ERROR] Instrument {pair_name} not found in instruments_dict.")
            return None

        # Validate Stop Loss and Take Profit
        if stop_loss is not None and take_profit is not None:
            min_distance = 0.1  # Example minimum distance
            if abs(stop_loss - take_profit) < min_distance:
                print(f"[ERROR] Stop Loss and Take Profit are too close for {pair_name}.")
                return None

        # Construct the payload
        data = {
            "Type": "Market",
            "Symbol": pair_name,
            "Amount": amount,
            "Side": dir_str,
            "StopLoss": round(max(stop_loss, 0.1), instrument.displayPrecision) if stop_loss else None,
            "TakeProfit": round(max(take_profit, 0.1), instrument.displayPrecision) if take_profit else None
        }

        # Debugging logs
        print(f"[DEBUG] Place Trade Payload: {data}")

        # Make the API request
        try:
            ok, response = self.make_request(url, verb="post", data=data, code=200)
            if not ok or response is None:
                print(f"[ERROR] Failed to place trade. Response: {response}")
                return None

            print(f"[DEBUG] API Response: {response}")
            return response
        except Exception as e:
            print(f"[ERROR] Exception while placing trade: {e}")
            return None

    def monitor_trade(self, trade_id):
        """
        Monitor the status of a trade and retry if necessary.
        """
        url = f"trade/{trade_id}"
        for _ in range(5):  # Retry up to 5 times
            ok, response = self.make_request(url, verb="get", code=200)
            if ok and response:
                status = response.get("Status")
                print(f"[DEBUG] Trade {trade_id} status: {status}")
                if status == "Filled":
                    print(f"[INFO] Trade {trade_id} successfully filled.")
                    return response
                time.sleep(2)  # Wait before retrying
            else:
                print(f"[ERROR] Failed to fetch trade status for {trade_id}.")
        print(f"[ERROR] Trade {trade_id} not filled after retries.")
        return None

    def get_open_trades(self):
        """
        Fetch the list of open trades from the API.
        :return: A list of OpenTrade objects representing the open trades.
        """
        from infrastructure.log_wrapper import LogWrapper
        logger = LogWrapper("OpenFxApi")
        logger.log_info("[DEBUG] Fetching open trades from the API.")
        try:
            ok, response = self.make_request("trade", verb="get")
            logger.log_info(f"[DEBUG] Raw open trades API response: {response}")
            open_trades = []
            if ok and response:
                # Handle both dict with 'Trades' key and direct list
                if isinstance(response, dict) and "Trades" in response:
                    trades_list = response["Trades"]
                elif isinstance(response, list):
                    trades_list = response
                else:
                    trades_list = []
                for trade in trades_list:
                    logger.log_info(f"[DEBUG] Inspecting trade: {trade}")
                    open_trades.append(OpenTrade(trade))
                logger.log_info(f"[DEBUG] All trades returned: {open_trades}")
                return open_trades
            else:
                logger.log_info(f"[ERROR] Failed to fetch open trades. Response: {response}")
                return []
        except Exception as e:
            logger.log_info(f"[ERROR] Exception while fetching open trades: {e}")
            return []

    def get_pip_value(self, pairs):
        """
        Fetch the pip value for the given trading pairs.
        :param pairs: List of trading pairs (e.g., ["XAUUSD"]).
        :return: Dictionary with pairs as keys and pip values as values.
        """
        print(f"[DEBUG] Fetching pip values for pairs: {pairs}")
        try:
            # Example: Use a predefined dictionary for pip values
            pip_values = {
                "XAUUSD": 0.01,  # Example pip value for XAUUSD
                "EURUSD": 0.0001,
                "GBPUSD": 0.0001,
                # Add more pairs as needed
            }

            # Filter the pip values for the requested pairs
            result = {pair: pip_values.get(pair, None) for pair in pairs}

            # Check for missing pip values
            for pair, value in result.items():
                if value is None:
                    print(f"[WARNING] Pip value not found for pair: {pair}")

            return result
        except Exception as e:
            print(f"[ERROR] Exception while fetching pip values: {e}")
            return {}

    def get_account_summary(self):
        url = f"account"
        save_path = os.path.join(os.path.dirname(__file__), "api_data", "account.json")
        ok, data = self.make_request(url, save_filename=save_path)

        if ok:
            return data
        else:
            print("ERROR get_account_summary()", data)
            return None

    def get_account_instruments(self, StatusGroupId='Forex'):
        url = f"symbol"
        ok, symbol_data = self.make_request(url, save_filename="symbol")

        if ok == False:
            print("ERROR get_account_instruments()", symbol_data)
            return None


    def web_api_candles(self, pair_name, granularity, count):

        pair_name = pair_name.replace('_', '')
        df = self.get_candles_df(pair_name, granularity=granularity, count=int(count)*-1)
        if df.shape[0] == 0:
            return None

        cols = ['time', 'mid_o', 'mid_h', 'mid_l', 'mid_c']
        df = df[cols].copy()

        df['time'] = df.time.dt.strftime("%y-%m-%d %H:%M")

        return df.to_dict(orient='list')
