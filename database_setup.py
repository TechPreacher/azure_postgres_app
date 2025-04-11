"""
Azure PostgreSQL Python Application

This script initializes and populates Azure Database for PostgreSQL instances.
It creates tables, loads sample data, and demonstrates basic database operations.
"""

import json
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# SQLAlchemy imports
from sqlalchemy import (
    Engine,
    create_engine,
    inspect,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


class DatabaseType(str, Enum):
    """Enum for database types"""

    PRIMARY = "PRIMARY"
    REPLICA = "REPLICA"
    BOTH = "BOTH"


# Load environment variables from .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("Warning: .env file not found. Using environment variables.")

# Define config values for both database types
PRIMARY_DB_CONFIG = {
    "host": os.environ.get("AZURE_POSTGRES_PRIMARY_HOST"),
    "user": os.environ.get("AZURE_POSTGRES_PRIMARY_USER"),
    "password": os.environ.get("AZURE_POSTGRES_PRIMARY_PASSWORD"),
    "database": os.environ.get("AZURE_POSTGRES_PRIMARY_DB"),
    "sslmode": os.environ.get("AZURE_POSTGRES_SSL_MODE", "require"),
}

REPLICA_DB_CONFIG = {
    "host": os.environ.get("AZURE_POSTGRES_REPLICA_HOST"),
    "user": os.environ.get("AZURE_POSTGRES_REPLICA_USER"),
    "password": os.environ.get("AZURE_POSTGRES_REPLICA_PASSWORD"),
    "database": os.environ.get("AZURE_POSTGRES_REPLICA_DB"),
    "sslmode": os.environ.get("AZURE_POSTGRES_SSL_MODE", "require"),
}

# Define SQLAlchemy Base and Models
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float(precision=10, decimal_return_scale=2), nullable=False)
    in_stock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship with Order model
    orders = relationship("Order", back_populates="product")

    def __repr__(self):
        return (f"<Product(id={self.id}, name='{self.name}', "
                f"category='{self.category}', price={self.price})>")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    order_date = Column(DateTime, server_default=func.now())

    # Relationship with Product model
    product = relationship("Product", back_populates="orders")

    def __repr__(self):
        return f"<Order(id={self.id}, product_id={self.product_id}, \
quantity={self.quantity})>"


def check_env_vars(db_type: DatabaseType) -> bool:
    """Verify all required environment variables are set."""
    # Basic connection variables - different vars needed based on db_type
    if db_type in (DatabaseType.PRIMARY, DatabaseType.BOTH):
        primary_vars = [
            "AZURE_POSTGRES_PRIMARY_HOST",
            "AZURE_POSTGRES_PRIMARY_USER",
            "AZURE_POSTGRES_PRIMARY_PASSWORD",
            "AZURE_POSTGRES_PRIMARY_DB",
        ]

        primary_missing = [var for var in primary_vars if not os.environ.get(var)]
        if primary_missing:
            print(
                f"Error: Missing PRIMARY database environment variables: "
                f"{', '.join(primary_missing)}"
            )
            print(
                "Please create a .env file based on .env.example "
                "with your Azure PostgreSQL credentials."
            )
            sys.exit(1)

    if db_type in (DatabaseType.REPLICA, DatabaseType.BOTH):
        replica_vars = [
            "AZURE_POSTGRES_REPLICA_HOST",
            "AZURE_POSTGRES_REPLICA_USER",
            "AZURE_POSTGRES_REPLICA_PASSWORD",
            "AZURE_POSTGRES_REPLICA_DB",
        ]

        replica_missing = [var for var in replica_vars if not os.environ.get(var)]
        if replica_missing:
            print(
                f"Error: Missing REPLICA database environment variables: "
                f"{', '.join(replica_missing)}"
            )
            print(
                "Please create a .env file based on .env.example "
                "with your Azure PostgreSQL credentials."
            )
            sys.exit(1)

    return True


def connect_to_database(config: Dict[str, str], db_type_desc: str) -> Engine:
    """Connect to the Azure PostgreSQL database using SQLAlchemy."""
    try:
        # Create the connection string
        connection_string = (
            f"postgresql+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}/{config['database']}?sslmode={config['sslmode']}"
        )

        print(f"Connecting to {db_type_desc} database at {config['host']}...")

        # Create engine with echo=False to avoid logging SQL statements
        engine = create_engine(connection_string, echo=False)

        # Test connection by making a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print(f"Connected successfully to {db_type_desc} database!")
        return engine
    except Exception as e:
        print(f"Error connecting to {db_type_desc} PostgreSQL: {e}")
        sys.exit(1)


def check_tables_exist(engine: Engine) -> bool:
    """Check if tables already exist in the database using SQLAlchemy."""
    try:
        inspector = inspect(engine)
        products_exist = "products" in inspector.get_table_names()
        orders_exist = "orders" in inspector.get_table_names()

        return products_exist or orders_exist
    except Exception as e:
        print(f"Error checking tables: {e}")
        sys.exit(1)


def drop_tables(engine: Engine) -> None:
    """Drop existing tables from the database using SQLAlchemy."""
    try:
        # Drop tables using the metadata
        # Order matters due to foreign key constraints
        Base.metadata.drop_all(engine)
        print("Tables dropped successfully!")
    except Exception as e:
        print(f"Error dropping tables: {e}")
        sys.exit(1)


def create_tables(engine: Engine) -> None:
    """Create necessary tables in the database using SQLAlchemy."""
    try:
        # Check if tables already exist
        tables_exist = check_tables_exist(engine)

        if tables_exist:
            print("Tables already exist in the database.")
            response = (
                input("Do you want to delete and re-create the tables? (y/n): ")
                .strip()
                .lower()
            )

            if response == "y":
                drop_tables(engine)
            else:
                print("Using existing tables.")
                return

        # Create all tables defined in Base metadata
        Base.metadata.create_all(engine)
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)


def load_sample_data(engine: Engine, is_primary: bool) -> None:
    """Load sample data from JSON file into the database using SQLAlchemy."""
    try:
        # Create a session to interact with the database
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if products table already has data
        product_count = session.query(Product).count()

        if product_count > 0:
            print(
                f"Products table already contains {product_count} records. "
                "Skipping data import."
            )
            session.close()
            return

        # Only insert sample data for the primary database
        if not is_primary:
            print(
                "Skipping data import for replica database - "
                "data will come from replication"
            )
            session.close()
            return

        # Load sample data from JSON file
        data_path = Path(__file__).parent / "data" / "sample_data.json"
        with open(data_path, "r") as file:
            products_data = json.load(file)

        # Insert products
        for product_data in products_data:
            product = Product(
                id=product_data["id"],
                name=product_data["name"],
                category=product_data["category"],
                price=product_data["price"],
                in_stock=product_data["in_stock"],
            )
            session.add(product)

        # Commit the changes
        session.commit()
        print(f"Imported {len(products_data)} products successfully!")
        session.close()
    except FileNotFoundError:
        print("Error: Sample data file not found at data/sample_data.json")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading sample data: {e}")
        sys.exit(1)


def query_data(engine: Engine) -> None:
    """Run and display some sample queries using SQLAlchemy."""
    try:
        # Create a session to interact with the database
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if products table has data before querying
        product_count = session.query(Product).count()
        if product_count == 0:
            print("\nNo products found to query.")
            session.close()
            return

        print("\n----- Database Query Results -----")

        # Query 1: All products
        print("\nAll Products:")
        products = session.query(Product).order_by(Product.id).all()
        for product in products:
            print(
                f"ID: {product.id}, Name: {product.name}, "
                f"Category: {product.category}, Price: ${product.price}, "
                f"In Stock: {product.in_stock}"
            )

        try:
            # Query 2: Group by category
            print("\nProducts by Category:")
            # Use a simpler query to avoid potential database function differences
            categories = session.query(Product.category).distinct().all()
            for (category,) in categories:
                count = (
                    session.query(func.count(Product.id))
                    .filter(Product.category == category)
                    .scalar()
                )
                avg_price = (
                    session.query(func.avg(Product.price))
                    .filter(Product.category == category)
                    .scalar()
                )
                print(
                    f"Category: {category}, Count: {count}, Avg Price: ${avg_price:.2f}"
                )

            # Query 3: In-stock products
            print("\nIn-Stock Products:")
            in_stock_count = (
                session.query(Product).filter(Product.in_stock.is_(True)).count()
            )
            print(f"Total in-stock products: {in_stock_count}")
        except Exception as e:
            print(f"Warning: Some advanced queries failed: {e}")
            print(
                "This is expected for the replica database until replication is set up."
            )

        session.close()
    except Exception as e:
        print(f"Error querying data: {e}")
        sys.exit(1)


def setup_primary_database() -> None:
    """Set up the primary database with schema and sample data."""
    print(f"\nSetting up {DatabaseType.PRIMARY} database...")

    # Connect to PostgreSQL with SQLAlchemy
    engine = connect_to_database(PRIMARY_DB_CONFIG, DatabaseType.PRIMARY)

    # Create database schema
    create_tables(engine)

    # Load sample data
    load_sample_data(engine, is_primary=True)

    # Query and display data
    query_data(engine)

    print(f"{DatabaseType.PRIMARY} database setup completed successfully!")


def setup_replica_database() -> None:
    """Set up the replica database with schema only (no data)."""
    print(f"\nSetting up {DatabaseType.REPLICA} database...")

    # Connect to PostgreSQL with SQLAlchemy
    engine = connect_to_database(REPLICA_DB_CONFIG, DatabaseType.REPLICA)

    # Create database schema
    create_tables(engine)

    # Don't load sample data - will come from replication
    load_sample_data(engine, is_primary=False)

    print(f"{DatabaseType.REPLICA} database setup completed successfully!")


def main() -> None:
    """Main function to run the application."""
    print("Azure PostgreSQL Python Application")
    print("===================================")

    # Determine which database(s) to set up
    db_type_str = os.environ.get("DB_TYPE")
    db_type = None

    if db_type_str:
        try:
            db_type = DatabaseType(db_type_str)
        except ValueError:
            print(f"Invalid DB_TYPE: {db_type_str}")
            print(f"Valid values are: {', '.join([t.value for t in DatabaseType])}")
            sys.exit(1)
    else:
        print("\nWhich database(s) would you like to set up?")
        print(f"1. {DatabaseType.PRIMARY.value.lower()} database only")
        print(f"2. {DatabaseType.REPLICA.value.lower()} database only")
        print(f"3. {DatabaseType.BOTH.value.lower()} databases")

        choice = ""
        while choice not in ["1", "2", "3"]:
            choice = input("\nEnter your choice (1, 2, or 3): ").strip()

        if choice == "1":
            db_type = DatabaseType.PRIMARY
        elif choice == "2":
            db_type = DatabaseType.REPLICA
        else:
            db_type = DatabaseType.BOTH

    print(f"\nSetting up {db_type} database(s)...")

    # Check environment variables
    check_env_vars(db_type)

    # Set up the requested database(s)
    if db_type in (DatabaseType.PRIMARY, DatabaseType.BOTH):
        setup_primary_database()

    if db_type in (DatabaseType.REPLICA, DatabaseType.BOTH):
        setup_replica_database()

    if db_type == DatabaseType.BOTH:
        print("\nBoth databases have been successfully set up.")
        print(
            "You can now run 'python replication_setup.py' to configure "
            "replication between them."
        )

    print("\nApplication completed successfully!")


if __name__ == "__main__":
    main()
