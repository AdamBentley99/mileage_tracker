STORES
id INTEGER PRIMARY KEY
name TEXT NOT NULL
is_business INTEGER DEFAULT 0
last_visited DATE

STORE_DISTANCES
id INTEGER PRIMARY KEY
store_a_id INTEGER
store_b_id INTEGER
miles REAL

VISITS
id INTEGER PRIMARY KEY
visit_date DATE
store_id INTEGER
sequence_number INTEGER
miles_from_previous REAL