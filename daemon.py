import os
import threading
import time
from datetime import datetime, timedelta

from asset_classes.fetcher import fetch_from_google

DIRECTORY_PATH = "./cache"


def is_file_older_than_one_day(filepath):
    """
    Checks if a given file is older than one day based on its modification time.

    Args:
        filepath (str): The path to the file.

    Returns:
        bool: True if the file is older than one day, False otherwise.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return False

    # Get the modification time of the file in seconds since the epoch
    modification_timestamp = os.path.getmtime(filepath)

    # Convert the timestamp to a datetime object
    modification_datetime = datetime.fromtimestamp(modification_timestamp)

    # Get the current time
    current_datetime = datetime.now()

    # Calculate the time difference
    time_difference = current_datetime - modification_datetime

    # Define one day as a timedelta object
    one_day = timedelta(days=1)

    # Compare the time difference with one day
    return time_difference > one_day


def background_task():
    while True:
        entries = os.listdir(DIRECTORY_PATH)
        touched = False
        for entry in entries:
            if ".pkl" in entry:
                if is_file_older_than_one_day(os.path.join(DIRECTORY_PATH, entry)):
                    sheet = entry.split(".pkl")[0]
                    print(f"{sheet} is older than one day.")
                    path = "./cache/" + sheet + ".pkl"
                    fetch_from_google(sheet, path)
                    touched = True
        if not touched:
            print("Refreshed old files, sleeping for an hour...")
            time.sleep(3600)


background_task()
