#!/usr/bin/env python3
"""
Database initialization helper for AIAC 2.0 Alpha-GPT
Creates the database if it doesn't exist.
Note: Tables are auto-created by SQLAlchemy when the app starts.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("[ERROR] psycopg2 is not installed. Please run: pip install psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_config():
    """Get database configuration from environment variables."""
    return {
        "host": os.getenv("POSTGRES_SERVER", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "database": os.getenv("POSTGRES_DB", "alpha_gpt"),
    }


def create_database_if_not_exists(config):
    """Create the database if it doesn't exist."""
    db_name = config["database"]
    
    # Connect to postgres database to create the target database
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            print(f"[INFO] Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"[SUCCESS] Database '{db_name}' created successfully!")
        else:
            print(f"[INFO] Database '{db_name}' already exists.")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Could not connect to PostgreSQL: {e}")
        return False


def main():
    print("=" * 50)
    print("    AIAC 2.0 Database Setup")
    print("=" * 50)
    
    config = get_db_config()
    
    print(f"\n[CONFIG] Database: {config['database']}")
    print(f"[CONFIG] Host: {config['host']}:{config['port']}")
    print(f"[CONFIG] User: {config['user']}")
    
    if not config["password"]:
        print("\n[WARNING] No password set. Please ensure POSTGRES_PASSWORD is set in .env")
    
    # Create database if not exists
    print("\n[STEP] Creating database if not exists...")
    success = create_database_if_not_exists(config)
    
    if success:
        print("\n" + "=" * 50)
        print("    Database setup complete!")
        print("=" * 50)
        print("\n[NOTE] Tables will be auto-created by SQLAlchemy when the app starts.")
    else:
        print("\n[ERROR] Database setup failed.")
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running")
        print("  2. POSTGRES_PASSWORD is set in .env file")
        print("  3. The user has permission to create databases")
        sys.exit(1)


if __name__ == "__main__":
    main()
