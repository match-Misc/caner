#!/usr/bin/env python3
"""
Database migration script to add mps_score column to existing tables.
Run this script once to update the database schema.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".secrets")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Database configuration
db_user = os.environ.get("CANER_DB_USER")
db_password = os.environ.get("CANER_DB_PASSWORD")
db_host = os.environ.get("CANER_DB_HOST")
db_name = os.environ.get("CANER_DB_NAME")

if not all([db_user, db_password, db_host, db_name]):
    print(
        "Database configuration missing. Please ensure all database-related environment variables are set."
    )
    sys.exit(1)

# Create database URL
database_url = (
    f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}?sslmode=require"
)


def add_mps_columns():
    """Add mps_score column to existing tables"""
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if columns already exist and add them if they don't
            tables_to_update = [
                ("meals", "mps_score"),
                ("xxxlutz_changing_meals", "mps_score"),
                ("xxxlutz_fixed_meals", "mps_score"),
            ]

            for table_name, column_name in tables_to_update:
                # Check if column exists
                result = conn.execute(
                    text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    AND column_name = '{column_name}'
                """)
                )

                if not result.fetchone():
                    print(f"Adding column {column_name} to table {table_name}...")
                    # Add the column
                    conn.execute(
                        text(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN {column_name} FLOAT
                    """)
                    )
                    print(f"✅ Successfully added {column_name} to {table_name}")
                else:
                    print(f"✅ Column {column_name} already exists in {table_name}")

            conn.commit()
            print("\n🎉 Database migration completed successfully!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Starting database migration...")
    add_mps_columns()
