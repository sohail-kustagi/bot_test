from openfx_api.openfx_api import OpenFxApi
from bot.trade_risk_calculator import get_trade_size
from models.trade_decision import TradeDecision
from models.open_trade import OpenTrade
import constants.defs as defs
from infrastructure.instrument_collection import instrumentCollection as ic


def trade_is_open(pair, api: OpenFxApi, log_message):
    """
    Check if a trade is already open for the given pair.
    Works with OpenTrade objects as returned by OpenFxApi.get_open_trades().
    """
    log_message(f"[DEBUG] Checking if a trade is open for {pair}")
    open_trades = api.get_open_trades()
    if not open_trades:
        log_message(f"[DEBUG] No open trades found.")
        return False
    normalized_pair = str(pair).strip().upper()
    for ot in open_trades:
        ot_symbol = str(getattr(ot, 'instrument', '')).strip().upper()
        log_message(f"[DEBUG] Open trade found: {ot} (symbol={ot_symbol}) vs pair={normalized_pair}")
        if ot_symbol == normalized_pair:
            log_message(f"[MATCH] Open trade for {pair} found: {ot}")
            return True
    log_message(f"[DEBUG] No open trade found for {pair}")
    return False


def place_trade(trade_decision: TradeDecision, api: OpenFxApi, log_message, trade_risk):
    log_message(f"[DEBUG] Attempting to place trade: {trade_decision}")

    # Calculate trade size
    trade_amount = get_trade_size(api, trade_decision.pair, trade_decision.loss, trade_risk, log_message)
    if trade_amount < 1:
        log_message(f"[WARNING] Trade size below minimum for {trade_decision.pair}. Using minimum trade size: 1.")
        trade_amount = 1

    # Place the trade using the API
    try:
        log_message(f"[DEBUG] Trade parameters: amount={trade_amount}, sl={trade_decision.sl}, tp={trade_decision.tp}")
        response = api.place_trade(
            trade_decision.pair,
            trade_amount,
            trade_decision.signal,
            trade_decision.sl,
            trade_decision.tp
        )
        print(f"[DEBUG] Payload sent to API: {trade_decision}")
        print(f"Place Trade Payload: {trade_decision}")
        print(f"API Response: {response}")
        log_message(f"[DEBUG] API Response: {response}")
        if response is None:
            log_message(f"[ERROR] No response received from API for trade placement.")
            return None
        if "Id" not in response:
            log_message(f"[ERROR] Invalid response from API: {response}")
            return None
        log_message(f"[INFO] Trade placed successfully: {response['Id']}")
        return response["Id"]
    except Exception as e:
        log_message(f"[ERROR] Exception while placing trade for {trade_decision.pair}: {e}")
        return None


def close_trade(trade_id, api: OpenFxApi, log_message):
    """
    Close an open trade by its trade ID.
    """
    log_message(f"[DEBUG] Attempting to close trade: {trade_id}")
    try:
        result = api.close_trade(trade_id)
        if result is None:
            log_message(f"[ERROR] No response received from API while closing trade {trade_id}.")
            return False
        if result.get("status") != "success":
            log_message(f"[ERROR] Failed to close trade {trade_id}. Response: {result}")
            return False
        log_message(f"[INFO] Trade closed successfully: {trade_id}")
        return True
    except Exception as e:
        log_message(f"[ERROR] Exception while closing trade {trade_id}: {e}")
        return False