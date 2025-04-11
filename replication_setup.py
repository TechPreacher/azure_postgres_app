"""
Azure PostgreSQL Replication Setup

This script sets up replication between two Azure Database for PostgreSQL instances,
with one serving as a primary (products) and the other as a replica (sales).
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# SQLAlchemy imports
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
# For potential future use with UUID fields
# from sqlalchemy.dialects.postgresql import UUID
# import uuid

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("Warning: .env file not found. Using environment variables.")

# Primary (Products) Database connection parameters
PRIMARY_DB_CONFIG = {
    "host": os.environ.get("AZURE_POSTGRES_PRIMARY_HOST"),
    "user": os.environ.get("AZURE_POSTGRES_PRIMARY_USER"),
    "password": os.environ.get("AZURE_POSTGRES_PRIMARY_PASSWORD"),
    "database": os.environ.get("AZURE_POSTGRES_PRIMARY_DB", "products"),
    "sslmode": os.environ.get("AZURE_POSTGRES_SSL_MODE", "require"),
}

# Replica (Sales) Database connection parameters
REPLICA_DB_CONFIG = {
    "host": os.environ.get("AZURE_POSTGRES_REPLICA_HOST"),
    "user": os.environ.get("AZURE_POSTGRES_REPLICA_USER"),
    "password": os.environ.get("AZURE_POSTGRES_REPLICA_PASSWORD"),
    "database": os.environ.get("AZURE_POSTGRES_REPLICA_DB", "sales"),
    "sslmode": os.environ.get("AZURE_POSTGRES_SSL_MODE", "require"),
}

# Azure resource information
AZURE_CONFIG = {
    "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID"),
    "resource_group": os.environ.get("AZURE_RESOURCE_GROUP"),
    "primary_server_name": os.environ.get("AZURE_POSTGRES_PRIMARY_SERVER_NAME"),
    "replica_server_name": os.environ.get("AZURE_POSTGRES_REPLICA_SERVER_NAME"),
}


def check_env_vars() -> bool:
    """Verify all required environment variables are set."""
    # Basic connection variables for primary and replica
    required_vars = [
        "AZURE_POSTGRES_PRIMARY_HOST",
        "AZURE_POSTGRES_PRIMARY_USER",
        "AZURE_POSTGRES_PRIMARY_PASSWORD",
        "AZURE_POSTGRES_PRIMARY_SERVER_NAME",
        "AZURE_POSTGRES_REPLICA_HOST",
        "AZURE_POSTGRES_REPLICA_USER",
        "AZURE_POSTGRES_REPLICA_PASSWORD",
        "AZURE_POSTGRES_REPLICA_SERVER_NAME",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Please create a .env file with your Azure PostgreSQL credentials.")
        sys.exit(1)

    return True


def connect_to_database(config: Dict[str, Any], description: str) -> Engine:
    """Connect to an Azure PostgreSQL database using SQLAlchemy."""
    try:
        # Create the connection string
        connection_string = (
            f"postgresql+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}/{config['database']}?sslmode={config['sslmode']}"
        )

        print(f"Connecting to {description} database at {config['host']}...")

        # Create engine with echo=False to avoid logging SQL statements
        engine = create_engine(connection_string, echo=False)

        # Test connection by making a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print(f"Connected successfully to {description} database!")
        return engine
    except Exception as e:
        print(f"Error connecting to {description} PostgreSQL: {e}")
        sys.exit(1)


def check_logical_replication_settings(engine: Engine) -> bool:
    """Check if logical replication is enabled on the server."""
    try:
        with engine.connect() as conn:
            # Check wal_level parameter
            result = conn.execute(text("SHOW wal_level")).scalar()

            if result != "logical":
                print(f"WARNING: wal_level is set to '{result}' instead of 'logical'")
                print("Logical replication requires wal_level to be set to 'logical'")
                print("This needs to be configured at the server level in Azure Portal")
                return False

            # Check max_replication_slots
            replication_slots = conn.execute(
                text("SHOW max_replication_slots")
            ).scalar()
            if int(replication_slots) < 5:
                print(f"WARNING: max_replication_slots is set to {replication_slots}")
                print("Consider increasing max_replication_slots in server parameters")

            # Check max_wal_senders
            wal_senders = conn.execute(text("SHOW max_wal_senders")).scalar()
            if int(wal_senders) < 10:
                print(f"WARNING: max_wal_senders is set to {wal_senders}")
                print("Consider increasing max_wal_senders in server parameters")

            print("Logical replication is properly configured.")
            return True

    except Exception as e:
        print(f"Error checking replication settings: {e}")
        return False


def create_publication(primary_engine: Engine) -> Optional[str]:
    """Create a publication on the primary server."""
    publication_name = "products_publication"

    try:
        with primary_engine.connect() as conn:
            # Check if publication already exists
            result = conn.execute(
                text("SELECT COUNT(*) FROM pg_publication WHERE pubname = :name"),
                {"name": publication_name},
            ).scalar()

            if result > 0:
                print(f"Publication '{publication_name}' already exists.")
                return publication_name

            # Create publication for all tables
            conn.execute(text(f"CREATE PUBLICATION {publication_name} FOR ALL TABLES"))
            conn.commit()

            print(f"Successfully created publication '{publication_name}'")
            return publication_name

    except Exception as e:
        print(f"Error creating publication: {e}")
        return None


def create_subscription(replica_engine: Engine, publication_name: str) -> bool:
    """Create a subscription on the replica server."""
    subscription_name = "sales_subscription"

    try:
        # Use AUTOCOMMIT mode since CREATE SUBSCRIPTION cannot run in a transaction
        with replica_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            # Check if subscription already exists
            result = conn.execute(
                text("SELECT COUNT(*) FROM pg_subscription WHERE subname = :name"),
                {"name": subscription_name},
            ).scalar()

            if result > 0:
                print(f"Subscription '{subscription_name}' already exists.")
                return True

            # Create connection string for subscription
            connection_string = (
                f"host={PRIMARY_DB_CONFIG['host']} "
                f"dbname={PRIMARY_DB_CONFIG['database']} "
                f"user={PRIMARY_DB_CONFIG['user']} "
                f"password={PRIMARY_DB_CONFIG['password']} "
                f"sslmode={PRIMARY_DB_CONFIG['sslmode']}"
            )

            # Create subscription
            conn.execute(
                text(
                    f"""
                CREATE SUBSCRIPTION {subscription_name}
                CONNECTION '{connection_string}'
                PUBLICATION {publication_name}
            """
                )
            )

            print(f"Successfully created subscription '{subscription_name}'")
            return True

    except Exception as e:
        print(f"Error creating subscription: {e}")
        return False


def check_replication_status(replica_engine: Engine) -> None:
    """Check the status of the replication subscription."""
    try:
        with replica_engine.connect() as conn:
            # Query subscription status
            result = conn.execute(
                text(
                    """
                SELECT subname, subenabled, subconninfo
                FROM pg_subscription
            """
                )
            ).fetchall()

            if not result:
                print("No subscriptions found.")
                return

            print("\nSubscription Status:")
            for row in result:
                print(f"Name: {row[0]}")
                print(f"Enabled: {row[1]}")
                print(f"Connection: {row[2]}")

            # Check subscription statistics
            stats = conn.execute(
                text(
                    """
                SELECT s.subname, r.srsubstate, r.srrelid::regclass AS relation_name,
                       r.srsublsn, r.srsubskiplsn
                FROM pg_subscription_rel r
                JOIN pg_subscription s ON s.oid = r.srsubid
                LIMIT 10
            """
                )
            ).fetchall()

            if stats:
                print("\nReplication Details (top 10 relations):")
                for row in stats:
                    print(
                        f"Subscription: {row[0]}, State: {row[1]}, Relation: {row[2]}"
                    )

    except Exception as e:
        print(f"Error checking replication status: {e}")


def setup_replication() -> None:
    """Main function to set up replication between products and sales databases."""
    # Connect to primary database
    primary_engine = connect_to_database(PRIMARY_DB_CONFIG, "PRIMARY")

    # Check if logical replication is enabled on primary
    if not check_logical_replication_settings(primary_engine):
        print("\nLogical replication is not properly configured on the primary server.")
        print("Please update server parameters in Azure Portal:")
        print("1. Set wal_level to 'logical'")
        print("2. Increase max_replication_slots (recommended: 10)")
        print("3. Increase max_wal_senders (recommended: 10)")
        print("Note: These changes require a server restart")
        sys.exit(1)

    # Create publication on primary
    publication_name = create_publication(primary_engine)
    if not publication_name:
        sys.exit(1)

    # Connect to replica database
    replica_engine = connect_to_database(REPLICA_DB_CONFIG, "REPLICA")

    # Create subscription on replica
    if not create_subscription(replica_engine, publication_name):
        sys.exit(1)

    # Check replication status
    check_replication_status(replica_engine)

    print("\nReplication setup completed successfully!")
    print("\nNotes:")
    print("1. Initial data synchronization may take some time depending on data volume")
    print("2. To monitor replication lag, query: pg_stat_replication on primary")
    print("3. To check replication status, query: pg_stat_subscription on replica")


def main() -> None:
    """Main function to run the application."""
    print("Azure PostgreSQL Replication Setup")
    print("=================================")

    # Check environment variables
    check_env_vars()

    # Set up replication between products and sales databases
    setup_replication()


if __name__ == "__main__":
    main()
