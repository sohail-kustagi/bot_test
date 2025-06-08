import logging
import os

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DEFAULT_LEVEL = logging.DEBUG

class LogWrapper:
    """
    A wrapper class for logging with file and console output.
    Implements a singleton pattern to avoid multiple initializations.
    """

    PATH = './logs'
    _instances = {}  # Dictionary to store instances of LogWrapper

    def __new__(cls, name, *args, **kwargs):
        """
        Ensure only one instance of LogWrapper exists for each unique name.
        """
        if name not in cls._instances:
            instance = super(LogWrapper, cls).__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name, mode="a", console_output=True):
        """
        Initialize the LogWrapper.
        :param name: Name of the log file (without extension).
        :param mode: File mode for the log file ('a' for append, 'w' for overwrite).
        :param console_output: Whether to enable console logging.
        """
        # Check if the logger is already initialized
        if hasattr(self, "logger"):
            return

        self.create_directory()
        self.filename = f"{LogWrapper.PATH}/{name}.log"
        self.logger = logging.getLogger(name)

        # Avoid adding duplicate handlers
        if not self.logger.hasHandlers():
            self.logger.setLevel(DEFAULT_LEVEL)

            # File handler for logging to a file
            file_handler = logging.FileHandler(self.filename, mode=mode)
            file_formatter = logging.Formatter(LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # Console handler for logging to the console
            if console_output:
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)

            self.logger.info(f"LogWrapper initialized. Logging to file: {self.filename}")

    def create_directory(self):
        """
        Create the logs directory if it doesn't exist.
        """
        if not os.path.exists(LogWrapper.PATH):
            os.makedirs(LogWrapper.PATH)
            print(f"[INFO] Created log directory: {LogWrapper.PATH}")

    def log_debug(self, message):
        """
        Log a debug-level message.
        :param message: The message to log.
        """
        self.logger.debug(message)

    def log_info(self, message):
        """
        Log an info-level message.
        :param message: The message to log.
        """
        self.logger.info(message)

    def log_warning(self, message):
        """
        Log a warning-level message.
        :param message: The message to log.
        """
        self.logger.warning(message)

    def log_error(self, message):
        """
        Log an error-level message.
        :param message: The message to log.
        """
        self.logger.error(message)

    def log_critical(self, message):
        """
        Log a critical-level message.
        :param message: The message to log.
        """
        self.logger.critical(message)










