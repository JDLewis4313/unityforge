import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connection parameters
sqlite_path = 'app.db'  # Path to your SQLite database
pg_conn_string = os.environ.get('DEV_DATABASE_URL')

print(f"Migrating data from {sqlite_path} to Supabase PostgreSQL")

# Connect to SQLite
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL
pg_conn = psycopg2.connect(pg_conn_string)
pg_cursor = pg_conn.cursor()

# Get tables from SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = sqlite_cursor.fetchall()

print(f"Found {len(tables)} tables in SQLite database")

# Process each table
for table in tables:
    table_name = table[0]
    print(f"\nProcessing table: {table_name}")
    
    # Skip alembic_version table
    if table_name == 'alembic_version':
        print("Skipping alembic_version table")
        continue
    
    # Get column names
    sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
    columns = sqlite_cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Get data from SQLite
    try:
        sqlite_cursor.execute(f"SELECT {', '.join(column_names)} FROM {table_name};")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"Error reading from {table_name}: {e}")
        continue
    
    if not rows:
        print(f"No data in table {table_name}")
        continue
    
    print(f"Found {len(rows)} rows in {table_name}")
    
    # Format column names for PostgreSQL
    pg_column_names = [f'"{col}"' for col in column_names]
    columns_str = ", ".join(pg_column_names)
    
    # Insert data in batches
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        
        # Create placeholders for VALUES clause
        placeholders = ", ".join(["%s"] * len(column_names))
        
        # Build the INSERT statement
        insert_query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
        
        try:
            pg_cursor.executemany(insert_query, batch)
            pg_conn.commit()
            print(f"Inserted batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1} into {table_name}")
        except Exception as e:
            pg_conn.rollback()
            print(f"Error inserting into {table_name}: {e}")
            print(f"First row in batch: {batch[0]}")
            
# Reset sequence numbers for all tables with an ID column
print("\nResetting sequence numbers...")
pg_cursor.execute("""
SELECT c.relname
FROM pg_class c
WHERE c.relkind = 'S'
  AND c.relname LIKE '%_id_seq'
""")
sequences = pg_cursor.fetchall()

for seq in sequences:
    seq_name = seq[0]
    table_name = seq_name.replace('_id_seq', '')
    
    try:
        # Get the maximum ID from the table
        pg_cursor.execute(f'SELECT MAX(id) FROM "{table_name}";')
        max_id = pg_cursor.fetchone()[0]
        
        if max_id:
            # Set the sequence to the next value after max_id
            pg_cursor.execute(f"SELECT setval('{seq_name}', {max_id}, true);")
            pg_conn.commit()
            print(f"Reset sequence for {table_name} to {max_id}")
        else:
            print(f"No data in {table_name}, skipping sequence reset")
    except Exception as e:
        pg_conn.rollback()
        print(f"Error resetting sequence for {table_name}: {e}")

# Close connections
sqlite_conn.close()
pg_conn.close()

print("\nMigration completed!")
