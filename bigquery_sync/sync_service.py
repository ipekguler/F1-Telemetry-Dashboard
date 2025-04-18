import os
import time
import logging
import psycopg2
from google.cloud import bigquery
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PostgreSQL connection parameters
PG_PARAMS = {
    'host': 'postgres',
    'database': 'f1_data',
    'user': 'postgres',
    'password': 'postgres',
    'port': 5432
}

# BigQuery client
bq_client = bigquery.Client()

# BigQuery dataset and table names
BQ_DATASET = 'f1_data'
BQ_TABLES = {
    'driver_laps': 'driver_laps',
    'race_control': 'race_control'
}

last_synced_ids = {
    'driver_laps': 0,
    'race_control': 0
}

def get_pg_connection():
    """Get a PostgreSQL connection"""
    try:
        return psycopg2.connect(**PG_PARAMS)
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        raise

def get_current_session_key():
    """Get the current session key from PostgreSQL"""
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        # Try to get session key from session_control table first (changed action to actn)
        try:
            cursor.execute(
                "SELECT session_key FROM race_control ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                session_key = row[0]
                cursor.close()
                conn.close()
                return session_key
        except Exception as e:
            logger.warning(f"Could not get session key from race_control: {e}")
            # Make sure to rollback the transaction if it failed
            conn.rollback()
        
        # If that fails, try race_control table (changed date to event_date)
        try:
            cursor.execute(
                "SELECT session_key FROM driver_laps ORDER BY date_start DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                session_key = row[0]
                cursor.close()
                conn.close()
                return session_key
        except Exception as e:
            logger.warning(f"Could not get session key from driver_laps: {e}")
            # Make sure to rollback the transaction if it failed
            conn.rollback()
        
        cursor.close()
        conn.close()
        return None
    except Exception as e:
        logger.error(f"Error in get_current_session_key: {e}")
        return None

def clear_bigquery_tables():
    """Clear BigQuery tables for a new session"""
    logger.info("Clearing BigQuery tables for new session")
    
    # Define queries to truncate tables
    queries = [
        f"TRUNCATE TABLE `{BQ_DATASET}.{BQ_TABLES['driver_laps']}`",
        f"TRUNCATE TABLE `{BQ_DATASET}.{BQ_TABLES['race_control']}`"
    ]
    
    # Execute queries
    for query in queries:
        try:
            query_job = bq_client.query(query)
            query_job.result()  # Wait for query to complete
            logger.info(f"Successfully executed: {query}")
        except Exception as e:
            logger.error(f"Error clearing BigQuery table: {e}")

def sync_table(table_name, session_key):
    """Sync all data for a specific table and session"""
    logger.info(f"Syncing {table_name} for session {session_key}")
    
    try:
        # Connect to PostgreSQL
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        # Get all records for this session
        if table_name == 'driver_laps':
            cursor.execute(
                "SELECT id, session_key, date_start, driver_number, lap_duration, "
                "lap_number, st_speed, position, "
                "name_acronym, team_name, team_colour "
                "FROM driver_laps WHERE session_key = %s AND id > %s ",
                (session_key,last_synced_ids[table_name])
            )
            columns = ['id', 'session_key', 'date_start', 'driver_number', 'lap_duration',
                        'lap_number', 'st_speed', 'position',
                        'name_acronym', 'team_name', 'team_colour']
        else:  # race_control (changed date to event_date and message to msg)
            cursor.execute(
                "SELECT id, session_key, date, category, flag, message "
                "FROM race_control WHERE session_key = %s AND id > %s ",
                (session_key,last_synced_ids[table_name])
            )
            columns = ['id', 'session_key', 'date', 'category', 'flag', 'message']
        
        # Fetch all rows
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            logger.info(f"No data found for {table_name} session {session_key}")
            return
        
        # Convert to list of dicts for BigQuery
        records = []
        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                # Handle datetime objects
                if isinstance(row[i], datetime):
                    record[col] = row[i].isoformat()
                else:
                    record[col] = row[i]
            records.append(record)
        
        # Insert into BigQuery in batches
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            table_ref = bq_client.dataset(BQ_DATASET).table(BQ_TABLES[table_name])
            errors = bq_client.insert_rows_json(table_ref, batch, row_ids=[str(record["id"]) for record in batch])
            
            if errors:
                logger.error(f"Errors inserting into BigQuery: {errors}")
            else:
                logger.info(f"Successfully synced batch of {len(batch)} records to {table_name}")

                if records:
                    max_id = max(record['id'] for record in records)
                    last_synced_ids[table_name] = max_id

        
        logger.info(f"Completed sync of {len(records)} records for {table_name} session {session_key}")
    except Exception as e:
        logger.error(f"Error in sync_table for {table_name}: {e}")

def check_for_new_session(current_session_key):
    """Check if a new session has started"""
    new_session_key = get_current_session_key()
    
    if new_session_key and new_session_key != current_session_key:
        logger.info(f"New session detected: {new_session_key}")
        clear_bigquery_tables()
        sync_table('driver_laps', new_session_key)
        sync_table('race_control', new_session_key)
        return new_session_key
    
    return current_session_key

def main():
    """Main sync loop"""
    logger.info("Starting BigQuery sync service")
    
    # Wait for PostgreSQL to be ready
    time.sleep(30)
    
    # Clear BigQuery tables before syncing new data
    clear_bigquery_tables()  # Clear BigQuery tables every time the sync runs

    # Get current session key
    current_session_key = get_current_session_key()
    if current_session_key:
        logger.info(f"Current session key: {current_session_key}")
        
        # Perform full sync of current session on startup
        sync_table('driver_laps', current_session_key)
        sync_table('race_control', current_session_key)
    else:
        logger.info("No current session found")
    
    while True:
        try:
            # Check for new session
            current_session_key = check_for_new_session(current_session_key)
            
            # If we have a current session, sync the data
            if current_session_key:
                sync_table('driver_laps', current_session_key)
                sync_table('race_control', current_session_key)
            
            # Wait before next sync
            time.sleep(10)  # Sync every 10 seconds
            
        except Exception as e:
            logger.error(f"Error in sync loop: {e}")
            time.sleep(30)  # Wait longer on error

if __name__ == "__main__":
    main()