import requests
import json
import time
from datetime import datetime
from confluent_kafka import Producer
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redpanda configuration
redpanda_config = {
    'bootstrap.servers': 'redpanda:9092',
    'client.id': 'f1-data-producer'
}

# API endpoints
API_ENDPOINTS = {
    'position': 'https://api.openf1.org/v1/position',
    'drivers': 'https://api.openf1.org/v1/drivers',
    'race_control': 'https://api.openf1.org/v1/race_control',
    'laps': 'https://api.openf1.org/v1/laps'
}

# Fields to extract
FIELDS_TO_EXTRACT = {
    'position': ['session_key', 'driver_number', 'date', 'position'],
    'drivers': ['session_key', 'driver_number', 'name_acronym', 'team_name', 'team_colour'],
    'race_control': ['session_key', 'date', 'category', 'flag', 'message'],
    'laps': ['session_key', 'date_start', 'driver_number', 'lap_duration', 'lap_number', 'st_speed']
}

class F1DataExtractor:
    def __init__(self):
        self.producer = Producer(redpanda_config)
        self.current_session_key = None
        self.last_data_counts = {'position': 0, 'drivers': 0, 'race_control': 0, 'laps': 0}
        self.session_active = False
        self.seen_laps = {}  # Store (driver_number, lap_number): latest_record


    def simplify_date_string(self, record):
        for key in ['date', 'date_start']:
            if key in record and isinstance(record[key], str):
                try:
                    # Ensure 'Z' becomes '+00:00' to be ISO compliant
                    iso_str = record[key].replace('Z', '+00:00')
                    dt = datetime.fromisoformat(iso_str)
                    # Convert to 'Z' format with milliseconds
                    record[key] = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                except Exception as e:
                    # Optional: log or handle bad format
                    print(f"Failed to convert timestamp for key '{key}': {e}")
        return record


    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def fetch_data(self, endpoint_name):
        url = f"{API_ENDPOINTS[endpoint_name]}?session_key=latest"
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {endpoint_name}: {e}")
            return []

    def send_to_redpanda(self, topic, data):
        try:
            self.producer.produce(
                topic,
                json.dumps(data).encode('utf-8'),
                callback=self.delivery_report
            )
            self.producer.flush()
        except Exception as e:
            logger.error(f"Error sending data to Redpanda: {e}")

    def check_for_new_session(self, race_control_data):
        if not race_control_data:
            return False

        latest_session_key = race_control_data[0].get('session_key') if race_control_data else None

        if self.current_session_key is None or latest_session_key != self.current_session_key:
            logger.info(f"New session detected: {latest_session_key}")
            self.current_session_key = latest_session_key
            self.last_data_counts = {'position': 0, 'drivers': 0, 'race_control': 0, 'laps': 0}
            self.seen_laps = {}  # Clear previous laps
            self.session_active = True
            #self.send_to_redpanda("f1-control", {"actn": "new_session", "session_key": self.current_session_key})
            return True
        return False

    def check_for_session_end(self, race_control_data):
        if not race_control_data or not self.session_active:
            return False

        for entry in race_control_data:
            if entry.get('message') == "CHEQUERED FLAG":
                logger.info("CHEQUERED FLAG detected - session has ended.")
                return False
        return False

    def process_endpoint(self, endpoint_name):
        data = self.fetch_data(endpoint_name)
        if not data:
            return

        current_count = len(data)
        if current_count > self.last_data_counts[endpoint_name]:
            new_records = data[self.last_data_counts[endpoint_name]:]

            for record in new_records:
                filtered_record = {field: record.get(field) for field in FIELDS_TO_EXTRACT[endpoint_name]}
                filtered_record = self.simplify_date_string(filtered_record)

                if endpoint_name == "laps":
                    key = (filtered_record.get("driver_number"), filtered_record.get("lap_number"))

                    # Update cache
                    if key not in self.seen_laps or self.seen_laps[key] != filtered_record:
                        self.seen_laps[key] = filtered_record

                        # Only send if now complete
                        if all(value is not None for value in filtered_record.values()):
                            self.send_to_redpanda(f"f1-{endpoint_name}", filtered_record)
                            logger.info(f"Sent updated lap record for driver {key[0]}, lap {key[1]}")
                else:
                    self.send_to_redpanda(f"f1-{endpoint_name}", filtered_record)

            logger.info(f"Processed {len(new_records)} new {endpoint_name} records")
            self.last_data_counts[endpoint_name] = current_count

    def run(self):
        while True:
            try:
                race_control_data = self.fetch_data('race_control')
                if self.check_for_new_session(race_control_data):
                    logger.info("New session started - resetting data")
                    self.send_to_redpanda("f1-control", {"action": "new_session", "session_key": self.current_session_key})

                self.process_endpoint('race_control')
                self.process_endpoint('position')
                self.process_endpoint('drivers')
                self.process_endpoint('laps')
                self.check_for_session_end(race_control_data)

                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    logger.info("Starting F1 Data Extractor")
    extractor = F1DataExtractor()
    extractor.run()