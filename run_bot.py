import pandas as pd
import time
import threading
import os
import traceback
import json
from bot.bot import Bot
from bot.candle_manager import CandleManager
from openfx_api.openfx_api import OpenFxApi
from stream_example.stream_socket import SocketConnection
from technicals.indicator import BollingerBands, RSI
from models.trade_settings import TradeSettings
from utils import preprocess_rolling_data
from infrastructure.log_wrapper import LogWrapper
from models.api_price import ApiPrice
from infrastructure.instrument_collection import instrumentCollection as ic
from bot.technicals_manager import process_candles
from collections import deque

# Initialize a deque to store the last 10 signals
last_signals = deque(maxlen=10)

# Initialize signals.json file if it doesn't exist
signals_file_path = "logs/signals.json"
if not os.path.exists(signals_file_path):
    with open(signals_file_path, "w") as json_file:
        json.dump([], json_file)
    print(f"[INFO] Initialized {signals_file_path} with an empty list.")

def save_signals_to_json(signal_data, file_path="logs/signals.json"):
    """
    Save the last 10 signal data to a JSON file.
    :param signal_data: Dictionary containing signal data.
    :param file_path: Path to the JSON file.
    """
    try:
        # Add the new signal to the deque
        last_signals.append(signal_data)

        # Convert deque to a list and ensure all timestamps are serialized as strings
        serialized_signals = []
        for signal in last_signals:
            if isinstance(signal.get("time"), pd.Timestamp):
                signal["time"] = signal["time"].isoformat()
            serialized_signals.append(signal)

        # Write the serialized signals to the JSON file
        with open(file_path, "w") as json_file:
            json.dump(serialized_signals, json_file, indent=4)
        print(f"[INFO] Last 10 signals saved to {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save signals to JSON: {e}")

if __name__ == "__main__":
    # Load instruments
    ic.LoadInstruments("./data")

    # Initialize API and CandleManager for XAUUSD
    api = OpenFxApi()

    # Define trade settings for XAUUSD
    xauusd_settings = {
        "n_ma": 12,
        "n_std": 2.0,
        "ema_period": 200,
        "rsi_period": 14,
        "maxspread": 1.0,
        "mingain": 0.06,
        "riskreward": 3
    }

    # Create TradeSettings object for XAUUSD
    trade_settings = {"XAUUSD": TradeSettings(xauusd_settings, "XAUUSD")}

    log_message = LogWrapper("run_bot").log_info
    trade_signal_logger = LogWrapper("trade_signals").log_info
    patterns_logger = LogWrapper("patterns").log_info

    granularity = "M1"

    # Initialize CandleManager for rolling data
    candle_manager = CandleManager(api, trade_settings, log_message, granularity)

    # Initialize WebSocket for live feed
    shared_prices = {}
    shared_prices_events = {}
    shared_prices_lock = threading.Lock()

    for pair in trade_settings.keys():
        shared_prices[pair] = {}
        shared_prices_events[pair] = threading.Event()

    socket_connection = SocketConnection(shared_prices, shared_prices_lock, shared_prices_events)
    socket_connection.daemon = True
    socket_connection.start()

    # Initialize the main bot
    b = Bot(trade_settings, log_message, api, trade_signal_logger)

    # Main loop to process live feed and run the bot
    while True:
        try:
            # Check for live price updates
            for pair in trade_settings.keys():
                if shared_prices_events[pair].is_set():
                    shared_prices_events[pair].clear()  # Reset the event

                    # Update rolling data with live price
                    with shared_prices_lock:
                        live_price = shared_prices[pair]
                    if isinstance(live_price, dict):
                        live_price = ApiPrice(live_price)  # Convert dictionary to ApiPrice object

                    candle_manager.update_rolling_data_with_live_prices(pair, live_price)

                    # Load updated rolling data
                    rolling_data_path = candle_manager.rolling_data_files[pair]
                    df = pd.read_pickle(rolling_data_path)

                    # Ensure sufficient rows for indicators
                    settings = trade_settings[pair]
                    required_rows = max(settings.rsi_period, settings.n_ma, 200) + 50
                    if len(df) < required_rows:
                        print(f"[DEBUG] Not enough rows for indicators. Have {len(df)}, need {required_rows}")
                        continue

                    # Calculate indicators for the pair
                    df = BollingerBands(df, settings)
                    df = RSI(df, settings)
                    df['EMA_200'] = df.mid_c.ewm(span=200, min_periods=200).mean()

                    # Add this line to handle NaNs in indicator columns
                    df = preprocess_rolling_data(df)

                    # Save updated rolling data
                    df.to_pickle(rolling_data_path)

                    # Process candles to get the latest row with all signals/indicators
                    processed_row = process_candles(df, pair, settings, log_message, patterns_logger)
                    if processed_row is None:
                        continue

                    # Save the processed row to JSON regardless of the signal value
                    save_signals_to_json(processed_row.to_dict())

                    # Run the bot's strategy using the processed row
                    b.run(pair, processed_row)

            time.sleep(0.5)  # Adjust sleep time as needed

        except KeyboardInterrupt:
            print("[INFO] Bot stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")
            traceback.print_exc()