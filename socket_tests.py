import threading
import time
from stream_example.stream_socket import SocketConnection
from models.live_api_price import LiveApiPrice


def log_message(message):
    """
    Simple logging function for debugging.
    """
    print(f"[LOG] {message}")


def process_live_price(pair, shared_prices, shared_prices_lock):
    """
    Process the live price for a given pair.
    :param pair: The trading pair (e.g., "XAUUSD").
    :param shared_prices: Shared dictionary containing live prices.
    :param shared_prices_lock: Lock for thread-safe access to shared_prices.
    """
    with shared_prices_lock:
        if pair in shared_prices and isinstance(shared_prices[pair], LiveApiPrice):
            live_price = shared_prices[pair]
            log_message(f"Processed live price for {pair}: {live_price}")
        else:
            log_message(f"No live price available for {pair}")


if __name__ == "__main__":
    shared_prices = {}
    shared_prices_events = {}
    shared_prices_lock = threading.Lock()

    # Add trading pairs to monitor
    pairs = ["XAUUSD"]
    for pair in pairs:
        shared_prices_events[pair] = threading.Event()
        shared_prices[pair] = {}

    # Create and start the WebSocket thread
    socket_t = SocketConnection(shared_prices, shared_prices_lock, shared_prices_events)
    socket_t.daemon = True
    socket_t.start()

    try:
        while True:
            # Check for new price events
            for pair in pairs:
                if shared_prices_events[pair].is_set():
                    shared_prices_events[pair].clear()  # Reset the event
                    process_live_price(pair, shared_prices, shared_prices_lock)

            time.sleep(0.5)  # Adjust sleep time as needed
    except KeyboardInterrupt:
        log_message("KeyboardInterrupt: Stopping the WebSocket connection.")