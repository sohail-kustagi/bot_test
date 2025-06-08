class TradeDecision:

    def __init__(self, row):
        """
        Initialize the TradeDecision object.
        :param row: A dictionary or object containing trade decision details.
        """
        try:
            if isinstance(row, dict):  # Handle dictionary input
                self.gain = row.get("GAIN", 0.0)
                self.loss = row.get("LOSS", 0.0)
                self.signal = row.get("SIGNAL", 0)
                self.sl = row.get("SL", 0.0)
                self.tp = row.get("TP", 0.0)
                self.pair = row.get("PAIR", "Unknown")
            else:  # Handle object input
                self.gain = getattr(row, "GAIN", 0.0)
                self.loss = getattr(row, "LOSS", 0.0)
                self.signal = getattr(row, "SIGNAL", 0)
                self.sl = getattr(row, "SL", 0.0)
                self.tp = getattr(row, "TP", 0.0)
                self.pair = getattr(row, "PAIR", "Unknown")
        except Exception as e:
            raise ValueError(f"Error initializing TradeDecision: {e}")

    def __repr__(self):
        return f"TradeDecision(): {self.pair} dir:{self.signal} gain:{self.gain:.4f} sl:{self.sl:.4f} tp:{self.tp:.4f}"
