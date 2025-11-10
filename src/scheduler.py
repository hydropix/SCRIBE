"""Scheduler for daily intelligence gathering execution"""

import schedule
import time
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging


class VeilleScheduler:
    """Scheduler for automatic intelligence gathering execution"""

    def __init__(
        self,
        veille_function,
        settings_path: str = "config/settings.yaml"
    ):
        """
        Initialize the scheduler

        Args:
            veille_function: Function to execute for intelligence gathering
            settings_path: Path to configuration file
        """
        self.logger = logging.getLogger("SCRIBE.Scheduler")
        self.config = load_config(settings_path)
        self.scheduler_config = self.config.get('scheduler', {})

        self.veille_function = veille_function
        self.run_time = self.scheduler_config.get('run_time', '08:00')

        self.logger.info(f"Scheduler initialized - will run daily at {self.run_time}")

    def schedule_daily(self):
        """Configure daily execution"""

        schedule.every().day.at(self.run_time).do(self._run_veille_safe)

        self.logger.info(f"Scheduled daily run at {self.run_time}")

    def _run_veille_safe(self):
        """Execute intelligence gathering with error handling"""

        self.logger.info("=" * 60)
        self.logger.info(f"Starting scheduled intelligence gathering at {datetime.now()}")
        self.logger.info("=" * 60)

        try:
            self.veille_function()
            self.logger.info("Intelligence gathering completed successfully")

        except Exception as e:
            self.logger.error(f"Error during scheduled intelligence gathering: {e}", exc_info=True)

        self.logger.info("=" * 60)

    def run_now(self):
        """Execute intelligence gathering immediately (for testing)"""

        self.logger.info("Running intelligence gathering immediately...")
        self._run_veille_safe()

    def start(self, run_immediately: bool = False):
        """
        Start the scheduler

        Args:
            run_immediately: If True, execute once immediately before scheduling
        """
        self.logger.info("Starting scheduler...")

        if run_immediately:
            self.run_now()

        self.schedule_daily()

        # Main loop
        self.logger.info("Scheduler is running. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")

    def get_next_run(self) -> str:
        """Return the next execution date"""

        next_run = schedule.next_run()

        if next_run:
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return "No scheduled runs"


if __name__ == "__main__":
    # Test the scheduler
    setup_logging()

    def test_veille():
        print(f"Intelligence gathering executed at {datetime.now()}")

    scheduler = VeilleScheduler(test_veille)

    print(f"Next run: {scheduler.get_next_run()}")

    # Test immédiat
    scheduler.run_now()
