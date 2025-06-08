import threading
import websocket
import json
import uuid
import datetime as dt
import time
from infrastructure.log_wrapper import LogWrapper
from models.api_price import ApiPrice
from stream_example.signature import get_signature, WEB_ID, WEB_KEY


def get_login(id):
    """
    Generate the login payload for WebSocket authentication.
    """
    ts = int(dt.datetime.now().timestamp() * 1000)
    sig = get_signature(str(ts))

    login = {
        "Id": id,
        "Request": "Login",
        "Params": {
            "AuthType": "HMAC",
            "WebApiId": WEB_ID,
            "WebApiKey": WEB_KEY,
            "Timestamp": ts,
            "Signature": sig,
            "DeviceId": "WebBrowser",
            "AppSessionId": "1234"
        }
    }

    return login


def login_was_ok(msg_data):
    """
    Check if the login response indicates a successful login.
    """
    print(f"login_was_ok: {msg_data}")
    if "Result" in msg_data and "Info" in msg_data["Result"]:
        if msg_data["Result"]["Info"] == "ok":
            return True
    return False


def sub_to_price_feed(ws, symbols, id):
    """
    Subscribe to the price feed for the given symbols.
    """
    params = []
    for s in symbols:
        params.append({
            "Symbol": s,
            "BookDepth": 1
        })

    data = {
        "Id": id,
        "Request": "FeedSubscribe",
        "Params": {
            "Subscribe": params
        }
    }

    ws.send(json.dumps(data))


class SocketConnection(threading.Thread):
    """
    WebSocket connection handler for live price updates.
    """

    def __init__(self, shared_prices, price_lock: threading.Lock, price_events):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.log = LogWrapper("SocketConnection")
        self.price_lock = price_lock
        self.shared_prices = shared_prices
        self.price_events = price_events
        self.pairs_list = list(shared_prices.keys())

    def log_message(self, msg, error=False):
        """
        Log messages for debugging or error tracking.
        """
        if error:
            self.log.logger.error(msg)
        else:
            self.log.logger.debug(msg)

    def fire_new_price_event(self, instrument):
        """
        Trigger an event when a new price is received for an instrument.
        """
        if not self.price_events[instrument].is_set():
            self.price_events[instrument].set()

    def update_live_price(self, live_price: ApiPrice):
        """
        Update the shared prices with the latest live price.
        """
        print(live_price)
        try:
            self.price_lock.acquire()
            self.shared_prices[live_price.instrument] = live_price
            self.fire_new_price_event(live_price.instrument)
        except Exception as error:
            self.log_message(f"Exception: {error}", error=True)
        finally:
            self.price_lock.release()

    def run(self):
        """
        Main WebSocket connection loop.
        """
        ws_url = "wss://marginalttdemowebapi.fxopen.net/feed"

        def on_open(ws):
            self.log_message("WebSocket connection established")
            login_payload = get_login(self.id)
            self.log_message(f"Login with: {login_payload}")
            ws.send(json.dumps(login_payload))

        def on_message(ws, message):
            msg_data = json.loads(message)
            print("on_message():", msg_data)
            if msg_data['Response'] == "Login" and login_was_ok(msg_data):
                sub_to_price_feed(ws, self.pairs_list, self.id)
            elif msg_data['Response'] == "FeedTick":
                self.update_live_price(ApiPrice(msg_data['Result']))

        def on_error(ws, error):
            self.log_message(f"WebSocket error occurred: {error}", error=True)

        def on_close(ws, close_status_code, close_msg):
            self.log_message(f"WebSocket connection closed: {close_status_code} - {close_msg}")

        while True:
            try:
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever()
            except Exception as e:
                self.log_message(f"Exception in WebSocket connection: {e}", error=True)
                time.sleep(5)  # Wait before attempting to reconnect








