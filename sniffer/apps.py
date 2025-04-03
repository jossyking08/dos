from django.apps import AppConfig
import threading
from .sniffer import start_sniffer  # Ensure you import your sniffer function

class SnifferConfig(AppConfig):
    name = 'sniffer'

    def ready(self):
        """Start the sniffer when Django starts"""
        if not hasattr(self, 'sniffer_thread'):  # Prevent duplicate threads
            print("Django App Started! Running Sniffer in the background...")
            self.sniffer_thread = threading.Thread(target=start_sniffer, daemon=True)
            self.sniffer_thread.start()
