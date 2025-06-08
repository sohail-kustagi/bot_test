import datetime as dt

class CandleTiming:
    """
    A class to track the timing of the last complete candle for a trading pair.
    """

    def __init__(self, last_time):
        """
        Initialize the CandleTiming object.
        :param last_time: The timestamp of the last complete candle (datetime or None).
        """
        self.last_time = last_time if isinstance(last_time, dt.datetime) else None
        self.is_ready = False

    def update(self, new_time):
        """
        Update the last_time and mark the candle as ready if the new_time is valid.
        :param new_time: The new timestamp to update (datetime).
        """
        if isinstance(new_time, dt.datetime) and (self.last_time is None or new_time > self.last_time):
            self.last_time = new_time
            self.is_ready = True
        else:
            self.is_ready = False

    def __repr__(self):
        """
        String representation of the CandleTiming object.
        :return: A formatted string showing the last candle time and readiness status.
        """
        last_time_str = self.last_time.strftime('%y-%m-%d %H:%M') if self.last_time else "None"
        return f"last_candle:{last_time_str} is_ready:{self.is_ready}" 