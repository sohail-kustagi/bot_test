from queue import Queue
import threading
import time
from infrastructure.log_wrapper import LogWrapper
from models.live_api_price import LiveApiPrice


class WorkProcessor(threading.Thread):
    """
    A class to process tasks from the work queue.
    """

    def __init__(self, work_queue: Queue):
        """
        Initialize the WorkProcessor.
        :param work_queue: Queue containing tasks to process.
        """
        super().__init__()
        self.work_queue = work_queue
        self.log = LogWrapper("WorkProcessor")

    def process_task(self, task: LiveApiPrice):
        """
        Process a single task from the work queue.
        :param task: A LiveApiPrice object containing live price data.
        """
        try:
            # Log the task being processed
            self.log.logger.debug(f"Processing task: {task}")

            # Simulate task processing (e.g., updating rolling data, triggering strategies)
            time.sleep(0.5)  # Simulate processing time

            # Example: Log the processed task
            self.log.logger.info(f"Processed task for {task.instrument} at {task.time}")
        except Exception as e:
            self.log.logger.error(f"Error processing task: {e}")

    def run(self):
        """
        Continuously process tasks from the work queue.
        """
        self.log.logger.info("WorkProcessor started.")
        while True:
            try:
                # Get the next task from the queue
                task: LiveApiPrice = self.work_queue.get()

                # Process the task
                self.process_task(task)

                # Mark the task as done
                self.work_queue.task_done()
            except Exception as e:
                self.log.logger.error(f"Error in WorkProcessor: {e}")


