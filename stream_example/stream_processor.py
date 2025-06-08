import copy
from queue import Queue
import threading
from stream_example.stream_base import StreamBase
from models.live_api_price import LiveApiPrice


class PriceProcessor(StreamBase):
    """
    A class to process live price updates for a specific trading pair and add them to a work queue.
    """

    def __init__(self, shared_prices, price_lock: threading.Lock, price_events, logname, pair, work_queue: Queue):
        """
        Initialize the PriceProcessor.
        :param shared_prices: Shared dictionary containing live prices for all pairs.
        :param price_lock: Threading lock for accessing shared_prices.
        :param price_events: Dictionary of threading events for price updates.
        :param logname: Name for the logger.
        :param pair: The trading pair (e.g., "XAUUSD") to process.
        :param work_queue: Queue to add processed prices for further handling.
        """
        super().__init__(shared_prices, price_lock, price_events, logname)
        self.pair = pair
        self.work_queue = work_queue

    def process_price(self):
        """
        Process the latest price for the given pair and add it to the work queue.
        """
        price = None
        try:
            # Acquire the lock to safely access shared_prices
            self.price_lock.acquire()
            if self.pair in self.shared_prices:
                price = copy.deepcopy(self.shared_prices[self.pair])
        except Exception as error:
            self.log_message(f"Error processing price for {self.pair}: {error}", error=True)
        finally:
            # Release the lock
            self.price_lock.release()

        if price is None:
            self.log_message(f"No price available for {self.pair}", error=True)
        else:
            self.log_message(f"Processing price for {self.pair}: {price}")
            # Convert the price to a LiveApiPrice object and add it to the work queue
            self.work_queue.put(LiveApiPrice(price))

    def run(self):
        """
        Continuously process prices when new events are triggered.
        """
        self.log_message(f"PriceProcessor started for {self.pair}")
        while True:
            # Wait for a new price event
            self.price_events[self.pair].wait()
            self.log_message(f"New price event detected for {self.pair}")
            # Process the price and clear the event
            self.process_price()
            self.price_events[self.pair].clear()