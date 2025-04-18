from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    statement_set = t_env.create_statement_set()

    t_env.get_config().get_configuration().set_string(
        "pipeline.jars",
        "file:///opt/flink/lib/flink-sql-connector-kafka-1.17.0.jar;"
        "file:///opt/flink/lib/flink-json-1.17.0.jar;"
        "file:///opt/flink/lib/flink-connector-jdbc-1.16.0.jar;"
        "file:///opt/flink/lib/postgresql-42.2.24.jar"
    )

    print("JARs set for pipeline:", t_env.get_config().get_configuration().get_string("pipeline.jars", "NOT FOUND"))

    t_env.execute_sql("""
    CREATE TABLE f1_race_control (
        session_key BIGINT,
        `date` TIMESTAMP_LTZ(3),
        category STRING,
        flag STRING,
        message STRING,
        WATERMARK FOR `date` AS `date` - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'f1-race_control',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'f1-consumer-group',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true',
        'scan.startup.mode' = 'earliest-offset',
        'json.timestamp-format.standard' = 'ISO-8601'
    )
    """)

    t_env.execute_sql("""
    CREATE TABLE f1_position_raw (
        session_key BIGINT,
        driver_number INT,
        `date` TIMESTAMP_LTZ(3),
        `position` INT,
        WATERMARK FOR `date` AS `date` - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'f1-position',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'f1-consumer-group',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true',
        'scan.startup.mode' = 'earliest-offset',
        'json.timestamp-format.standard' = 'ISO-8601'
    )
    """)

    t_env.execute_sql("""
    CREATE TABLE f1_position_latest (
        session_key BIGINT,
        driver_number INT,
        `date` TIMESTAMP_LTZ(3),
        `position` INT,
        PRIMARY KEY (driver_number, session_key) NOT ENFORCED,
        WATERMARK FOR `date` AS `date` - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'upsert-kafka',
        'topic' = 'f1-position-deduped',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'key.format' = 'json',
        'value.format' = 'json'
    )
    """)

    t_env.execute_sql("""
    INSERT INTO f1_position_latest
    SELECT session_key, driver_number, `date`, `position`
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY driver_number, session_key
                   ORDER BY `date` DESC
               ) AS row_num
        FROM f1_position_raw
    )
    WHERE row_num = 1
    """)

    t_env.execute_sql("""
    CREATE TABLE f1_drivers (
        session_key BIGINT,
        driver_number INT,
        name_acronym STRING,
        team_name STRING,
        team_colour STRING
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'f1-drivers',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'f1-consumer-group',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true',
        'scan.startup.mode' = 'earliest-offset'
    )
    """)

    t_env.execute_sql("""
    CREATE TABLE f1_laps (
        session_key BIGINT,
        date_start TIMESTAMP_LTZ(3),
        driver_number INT,
        lap_duration DOUBLE,
        lap_number INT,
        st_speed INT,
        WATERMARK FOR date_start AS date_start - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'f1-laps',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'f1-consumer-group',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true',
        'scan.startup.mode' = 'earliest-offset',
        'json.timestamp-format.standard' = 'ISO-8601'
    )
    """)

    t_env.execute_sql("""
    CREATE VIEW enriched_laps AS
    SELECT 
        laps.session_key,
        laps.date_start,
        laps.driver_number,
        laps.lap_duration,
        laps.lap_number,
        laps.st_speed,
        pos.`position`,
        drv.name_acronym,
        drv.team_name,
        drv.team_colour
    FROM f1_laps AS laps
    LEFT JOIN f1_position_latest FOR SYSTEM_TIME AS OF laps.date_start AS pos
        ON laps.driver_number = pos.driver_number
        AND laps.session_key = pos.session_key
    LEFT JOIN f1_drivers AS drv 
        ON laps.driver_number = drv.driver_number AND laps.session_key = drv.session_key
    """)

    t_env.execute_sql("""
    CREATE TABLE lap_sink (
        session_key BIGINT,
        date_start TIMESTAMP(3),
        driver_number INT,
        lap_duration DOUBLE,
        lap_number INT,
        st_speed INT,
        `position` INT,
        name_acronym STRING,
        team_name STRING,
        team_colour STRING,
        PRIMARY KEY (session_key, driver_number, lap_number) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = 'jdbc:postgresql://postgres:5432/f1_data',
        'table-name' = 'driver_laps',
        'username' = 'postgres',
        'password' = 'postgres',
        'driver' = 'org.postgresql.Driver',
        'sink.buffer-flush.max-rows' = '1'
    )
    """)

    statement_set.add_insert_sql("""
        INSERT INTO lap_sink 
        SELECT * FROM enriched_laps WHERE `position` IS NOT NULL
    """)

    t_env.execute_sql("""
    CREATE TABLE control_sink (
        session_key BIGINT,
        `date` TIMESTAMP(3),
        category STRING,
        flag STRING,
        message STRING
    ) WITH (
        'connector' = 'jdbc',
        'url' = 'jdbc:postgresql://postgres:5432/f1_data',
        'table-name' = 'race_control',
        'username' = 'postgres',
        'password' = 'postgres',
        'driver' = 'org.postgresql.Driver'
    )
    """)

    statement_set.add_insert_sql("""
        INSERT INTO control_sink 
        SELECT * FROM f1_race_control
    """)

    statement_set.execute().wait()

if __name__ == '__main__':
    main()
