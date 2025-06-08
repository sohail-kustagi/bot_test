from bot.trade_manager import place_trade, trade_is_open
from models.trade_decision import TradeDecision
from infrastructure.instrument_collection import instrumentCollection as ic
import constants.defs as defs

class Bot:
    def __init__(self, trade_settings, log_message, api, trade_signal_logger=None, trade_risk=0.05):
        """
        Initialize the Bot.
        :param trade_settings: Dictionary of TradeSettings objects for each pair.
        :param log_message: Logging function.
        :param api: OpenFxApi instance for placing trades.
        :param trade_signal_logger: Optional logging function for trade signals.
        :param trade_risk: Risk percentage for trade size calculation.
        """
        self.trade_settings = trade_settings
        self.log_message = log_message
        self.api = api
        self.trade_risk = trade_risk
        self.trade_signal_logger = trade_signal_logger

    def run(self, pair, row):
        """
        Run the bot's strategy for a given pair and processed row.
        :param pair: Trading pair (e.g., "XAUUSD")
        :param row: The latest processed row with all indicators and signals
        """
        settings = self.trade_settings[pair]
        instrument = ic.instruments_dict[pair]
        precision = instrument.displayPrecision

        signal = row['SIGNAL']

        # Only place a new trade if there is no open trade for XAUUSD
        if pair == "XAUUSD":
            open_trade = trade_is_open(pair, self.api, self.log_message)
            if open_trade:
                self.log_message(f"[INFO] Trade already open for {pair}, skipping new order until it is closed.")
                return

        if signal == defs.BUY:
            if self.trade_signal_logger:
                self.trade_signal_logger(f"[SIGNAL] BUY signal detected for {pair}.")
            else:
                self.log_message(f"[SIGNAL] BUY signal detected for {pair}.")
            sl = row['SL']
            tp = row['TP']

            trade_decision = TradeDecision({
                "PAIR": pair,
                "SIGNAL": defs.BUY,
                "SL": round(sl, precision),
                "TP": round(tp, precision),
                "GAIN": round(row['GAIN'], precision),
                "LOSS": round(row['LOSS'], precision)
            })
            self.log_message(f"[DEBUG] TradeDecision created: {trade_decision}")
            place_trade(trade_decision, self.api, self.log_message, self.trade_risk)

        elif signal == defs.SELL:
            if self.trade_signal_logger:
                self.trade_signal_logger(f"[SIGNAL] SELL signal detected for {pair}.")
            else:
                self.log_message(f"[SIGNAL] SELL signal detected for {pair}.")
            sl = row['SL']
            tp = row['TP']

            trade_decision = TradeDecision({
                "PAIR": pair,
                "SIGNAL": defs.SELL,
                "SL": round(sl, precision),
                "TP": round(tp, precision),
                "GAIN": round(row['GAIN'], precision),
                "LOSS": round(row['LOSS'], precision)
            })
            self.log_message(f"[DEBUG] TradeDecision created: {trade_decision}")
            place_trade(trade_decision, self.api, self.log_message, self.trade_risk)

        else:
            self.log_message(f"[INFO] No trading signal for {pair}.")