-- Driver laps table
CREATE TABLE IF NOT EXISTS driver_laps (
    id SERIAL PRIMARY KEY,
    session_key BIGINT NOT NULL,
    date_start TIMESTAMPTZ,
    driver_number INTEGER,
    lap_duration DOUBLE PRECISION,
    lap_number INTEGER,
    st_speed INTEGER,
    position INTEGER,
    name_acronym VARCHAR(255),
    team_name VARCHAR(255),
    team_colour VARCHAR(255),
    UNIQUE (session_key, driver_number, lap_number)

);

-- Race control table
CREATE TABLE IF NOT EXISTS race_control (
    id SERIAL PRIMARY KEY,
    session_key BIGINT NOT NULL,
    date TIMESTAMPTZ,
    category VARCHAR(50),
    flag VARCHAR(50),
    message TEXT
);