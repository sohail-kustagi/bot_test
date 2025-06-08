import json
from queue import Queue
import threading
import time
import pandas as pd  # Import Pandas

from stream_example.stream_prices import PriceStreamer
from stream_example.stream_processor import PriceProcessor
from stream_example.stream_worker import WorkProcessor
from bot.bot import Bot
from bot.candle_manager import CandleManager
from openfx_api.openfx_api import OpenFxApi
from models.trade_settings import TradeSettings
from technicals.indicator import BollingerBands, RSI  # Import BollingerBands and RSI


def load_settings():
    """
    Load settings from the settings.json file.
    """
    with open("./bot/settings.json", "r") as f:
        return json.loads(f.read())


def run_streamer():
    """
    Run the live feed streamer and initialize the bot.
    """
    settings = load_settings()

    # Shared resources for live price updates
    shared_prices = {}
    shared_prices_events = {}
    shared_prices_lock = threading.Lock()
    work_queue = Queue()

    # Initialize shared resources for each trading pair
    for p in settings['pairs'].keys():
        shared_prices_events[p] = threading.Event()
        shared_prices[p] = {}

    threads = []

    # Start the price streamer thread
    price_stream_t = PriceStreamer(shared_prices, shared_prices_lock, shared_prices_events)
    price_stream_t.daemon = True
    threads.append(price_stream_t)
    price_stream_t.start()

    # Start the work processor thread
    worker_t = WorkProcessor(work_queue)
    worker_t.daemon = True
    threads.append(worker_t)
    worker_t.start()

    # Start a price processor thread for each trading pair
    for p in settings['pairs'].keys():
        processing_t = PriceProcessor(shared_prices, shared_prices_lock, shared_prices_events,
                                      f"PriceProcessor_{p}", p, work_queue)
        processing_t.daemon = True
        threads.append(processing_t)
        processing_t.start()

    # Initialize API and trade settings
    api = OpenFxApi()
    trade_settings = {
        pair: TradeSettings(settings['pairs'][pair], pair)
        for pair in settings['pairs'].keys()
    }
    log_message = print  # Replace with your logging function

    # Initialize CandleManager
    granularity = "M1"
    candle_manager = CandleManager(api, trade_settings, log_message, granularity)

    # Initialize the bot
    b = Bot(trade_settings, log_message, api)

    # Main loop to run the bot
    try:
        while True:
            # Check for live price updates
            for pair in trade_settings.keys():
                if shared_prices_events[pair].is_set():
                    shared_prices_events[pair].clear()  # Reset the event

                    # Update rolling data with live price
                    live_price = shared_prices[pair]
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

                    # Save updated rolling data
                    df.to_pickle(rolling_data_path)

                    # Run the bot's strategy
                    b.run(pair, df)

            time.sleep(0.5)  # Adjust sleep time as needed

    except KeyboardInterrupt:
        print("KeyboardInterrupt: Stopping the streamer and bot.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

    print("ALL DONE")


# Start the live feed streamer
if __name__ == "__main__":
    run_streamer()

