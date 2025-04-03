"""
WSGI config for ecommerce project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""
import threading

from sniffer.sniffer import start_sniffer
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

# Start background task (not recommended for production WSGI servers)
if os.environ.get('RUN_MAIN') == 'true':  
    print("Running Sniffer in the background from WSGI...")
    threading.Thread(target=start_sniffer, daemon=True).start()

application = get_wsgi_application()
