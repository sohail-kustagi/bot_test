class TradeSettings:
    def __init__(self, ob: dict, pair: str):
        """
        Initialize trade settings for a specific trading pair.
        :param ob: Dictionary containing the trade settings.
        :param pair: The trading pair (e.g., "XAUUSD").
        """
        # Define required keys for trade settings
        required_keys = ['n_ma', 'n_std', 'ema_period', 'rsi_period', 'maxspread', 'mingain', 'riskreward']
        for key in required_keys:
            if key not in ob:
                raise ValueError(f"Missing required setting '{key}' for pair '{pair}'")

        # Assign settings to instance variables
        self.pair = pair
        self.n_ma = ob['n_ma']
        self.n_std = ob['n_std']
        self.ema_period = ob['ema_period']
        self.rsi_period = ob['rsi_period']
        self.maxspread = ob['maxspread']
        self.mingain = ob['mingain']
        self.riskreward = ob['riskreward']

    def __repr__(self):
        """
        String representation of the TradeSettings object.
        :return: A string containing the pair and its settings.
        """
        return f"{self.pair}: {vars(self)}"

    def to_dict(self):
        """
        Convert the TradeSettings object to a dictionary.
        :return: A dictionary representation of the trade settings.
        """
        return vars(self)

    @classmethod
    def settings_to_str(cls, settings):
        """
        Convert multiple TradeSettings objects to a formatted string.
        :param settings: Dictionary of TradeSettings objects.
        :return: A formatted string representation of all settings.
        """
        ret_str = "Trade Settings:\n"
        for _, v in settings.items():
            ret_str += f"{v}\n"
        return ret_str

    @classmethod
    def from_dict(cls, settings_dict: dict, pair: str):
        """
        Create a TradeSettings object from a dictionary.
        :param settings_dict: Dictionary containing the trade settings.
        :param pair: The trading pair (e.g., "XAUUSD").
        :return: A TradeSettings object.
        """
        return cls(settings_dict, pair) 