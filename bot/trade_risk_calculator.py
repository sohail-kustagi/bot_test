from openfx_api.openfx_api import OpenFxApi
from infrastructure.instrument_collection import instrumentCollection as ic

BASE = 10000
MINIMUM = 1  # Corrected typo from MINUMUM to MINIMUM

def get_trade_size(api: OpenFxApi, pair, loss, trade_risk, log_message):
    """
    Calculate the trade size based on risk and loss.
    :param api: OpenFxApi instance for fetching pip values.
    :param pair: The trading pair (e.g., "XAUUSD").
    :param loss: The monetary loss for the trade.
    :param trade_risk: The risk percentage for the trade.
    :param log_message: Logging function.
    :return: Calculated trade size or 0 if an error occurs.
    """
    try:
        log_message(f"[DEBUG] Calculating trade size for {pair} with loss: {loss}, risk: {trade_risk}")
        log_message(f"[DEBUG] Available instruments: {ic.instruments_dict.keys()}")  # Debugging

        # Check if the instrument exists in the instruments dictionary
        if pair not in ic.instruments_dict:
            log_message(f"[ERROR] Instrument {pair} not found in instruments_dict. Available instruments: {list(ic.instruments_dict.keys())}")
            return 0

        # Fetch instrument details
        our_instrument = ic.instruments_dict[pair]
        pip_location = our_instrument.pipLocation
        trade_amount_step = our_instrument.TradeAmountStep

        # Validate pip_location
        if pip_location <= 0:
            log_message(f"[ERROR] Invalid pip location for {pair}: {pip_location}")
            return 0

        # Calculate the number of pips
        num_pips = loss / pip_location
        log_message(f"[DEBUG] loss: {loss}, pip_location: {pip_location}, num_pips: {num_pips}")
        if num_pips <= 0:
            log_message(f"[ERROR] Invalid number of pips calculated: {num_pips}")
            return 0

        # Fetch pip value from the API
        pip_values = api.get_pip_value([pair])
        if not pip_values or pair not in pip_values or pip_values[pair] is None:
            log_message(f"[ERROR] Pip value not available for {pair}.")
            return 0

        our_pip_value = pip_values[pair]
        log_message(f"[DEBUG] Pip value for {pair}: {our_pip_value}")

        # Calculate trade size
        per_pip_loss = trade_risk / num_pips
        ratio = per_pip_loss / our_pip_value
        trade_pure = BASE * ratio
        log_message(f"[DEBUG] num_pips: {num_pips}, per_pip_loss: {per_pip_loss}, ratio: {ratio}, trade_pure: {trade_pure}")
        # Clamp trade size to instrument's min/max and round to nearest step
        min_amount = getattr(our_instrument, 'MinTradeAmount', MINIMUM)
        max_amount = getattr(our_instrument, 'MaxTradeAmount', 100)
        trade_size = int(trade_pure / trade_amount_step) * trade_amount_step
        if trade_size < min_amount:
            log_message(f"[WARNING] Trade size below instrument minimum for {pair}. Using minimum: {min_amount}")
            trade_size = min_amount
        elif trade_size > max_amount:
            log_message(f"[WARNING] Trade size above instrument maximum for {pair}. Using maximum: {max_amount}")
            trade_size = max_amount

        # Validate trade size
        if trade_size < MINIMUM:
            log_message(f"[WARNING] Trade size below minimum for {pair}. Calculated: {trade_size}, Minimum: {MINIMUM}")
            return MINIMUM  # Use the minimum trade size instead of returning 0

        log_message(f"[DEBUG] Trade size calculated: {trade_size}")
        return trade_size

    except Exception as e:
        log_message(f"[ERROR] Exception occurred while calculating trade size for {pair}: {e}")
        return 0