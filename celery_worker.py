#!/usr/bin/env python3
"""
Celery Worker Entry Point
Phase 11: Asynchronous Task Processing

This script initializes and starts the Celery worker with Flask
application context integration.

Usage:
    # Start worker
    celery -A celery_worker.celery_app worker --loglevel=INFO

    # Start worker with specific queues
    celery -A celery_worker.celery_app worker -Q email,notifications --loglevel=INFO

    # Start beat scheduler (for periodic tasks)
    celery -A celery_worker.celery_app beat --loglevel=INFO

    # Start worker and beat together (development)
    celery -A celery_worker.celery_app worker -B --loglevel=INFO

    # Start Flower monitoring (port 5555)
    celery -A celery_worker.celery_app flower --port=5555
"""
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.tasks import init_celery, register_tasks

# Create Flask application
flask_app = create_app()

# Initialize Celery with Flask app context
celery_app = init_celery(flask_app)

# Register all tasks
with flask_app.app_context():
    register_tasks()

# Celery configuration logging
if __name__ == "__main__":
    print("=" * 60)
    print("Backup Management System - Celery Worker")
    print("=" * 60)
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Broker: {celery_app.conf.broker_url}")
    print(f"Backend: {celery_app.conf.result_backend}")
    print("=" * 60)
    print("\nAvailable queues:")
    for queue in celery_app.conf.task_queues:
        print(f"  - {queue.name}")
    print("\nStarting worker...")
    print("=" * 60)
