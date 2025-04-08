"""
Azure PostgreSQL Python Application

This script initializes and populates an Azure Database for PostgreSQL Flexible Server instance.
It creates tables, loads sample data, and demonstrates basic database operations.
Uses the Azure SDK for PostgreSQL management capabilities.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# SQLAlchemy imports
from sqlalchemy import Engine, create_engine, inspect, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print("Warning: .env file not found. Using environment variables.")

# Database connection parameters
DB_CONFIG = {
    'host': os.environ.get('AZURE_POSTGRES_HOST'),
    'user': os.environ.get('AZURE_POSTGRES_USER'),
    'password': os.environ.get('AZURE_POSTGRES_PASSWORD'),
    'database': os.environ.get('AZURE_POSTGRES_DB'),
    'sslmode': os.environ.get('AZURE_POSTGRES_SSL_MODE', 'require')
}

# Define SQLAlchemy Base and Models
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float(precision=10, decimal_return_scale=2), nullable=False)
    in_stock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationship with Order model
    orders = relationship("Order", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', category='{self.category}', price={self.price})>"

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    order_date = Column(DateTime, server_default=func.now())
    
    # Relationship with Product model
    product = relationship("Product", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

# Azure resource information
AZURE_CONFIG = {
    'subscription_id': os.environ.get('AZURE_SUBSCRIPTION_ID'),
    'resource_group': os.environ.get('AZURE_RESOURCE_GROUP'),
    'server_name': os.environ.get('AZURE_POSTGRES_SERVER_NAME')
}

def check_env_vars() -> bool:
    """Verify all required environment variables are set."""
    # Basic connection variables
    required_vars = ['AZURE_POSTGRES_HOST', 'AZURE_POSTGRES_USER', 
                     'AZURE_POSTGRES_PASSWORD', 'AZURE_POSTGRES_DB', 'AZURE_POSTGRES_SERVER_NAME']
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file based on .env.example with your Azure PostgreSQL credentials.")
        sys.exit(1)
    
    return True

def connect_to_database() -> Engine:
    """Connect to the Azure PostgreSQL database using SQLAlchemy."""
    try:
        # Create the connection string
        connection_string = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?sslmode={DB_CONFIG['sslmode']}"
        
        print(f"Connecting to {DB_CONFIG['host']}...")
        
        # Create engine with echo=False to avoid logging SQL statements
        engine = create_engine(connection_string, echo=False)
        
        # Test connection by making a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("Connected successfully!")
        return engine
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sys.exit(1)

def check_tables_exist(engine) -> bool:
    """Check if tables already exist in the database using SQLAlchemy."""
    try:
        inspector = inspect(engine)
        products_exist = 'products' in inspector.get_table_names()
        orders_exist = 'orders' in inspector.get_table_names()
        
        return products_exist or orders_exist
    except Exception as e:
        print(f"Error checking tables: {e}")
        sys.exit(1)

def drop_tables(engine) -> None:
    """Drop existing tables from the database using SQLAlchemy."""
    try:
        # Drop tables using the metadata
        # Order matters due to foreign key constraints
        Base.metadata.drop_all(engine)
        print("Tables dropped successfully!")
    except Exception as e:
        print(f"Error dropping tables: {e}")
        sys.exit(1)

def create_tables(engine) -> None:
    """Create necessary tables in the database using SQLAlchemy."""
    try:
        # Check if tables already exist
        tables_exist = check_tables_exist(engine)
        
        if tables_exist:
            print("Tables already exist in the database.")
            response = input("Do you want to delete and re-create the tables? (y/n): ").strip().lower()
            
            if response == 'y':
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

def load_sample_data(engine) -> None:
    """Load sample data from JSON file into the database using SQLAlchemy."""
    try:
        # Create a session to interact with the database
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Load sample data from JSON file
        data_path = Path(__file__).parent / 'data' / 'sample_data.json'
        with open(data_path, 'r') as file:
            products_data = json.load(file)
        
        # Check if products table already has data
        product_count = session.query(Product).count()
        
        if product_count > 0:
            print(f"Products table already contains {product_count} records. Skipping data import.")
            session.close()
            return
        
        # Insert products
        for product_data in products_data:
            product = Product(
                id=product_data['id'],
                name=product_data['name'],
                category=product_data['category'],
                price=product_data['price'],
                in_stock=product_data['in_stock']
            )
            session.add(product)
        
        # Commit the changes
        session.commit()
        print(f"Imported {len(products_data)} products successfully!")
        session.close()
    except FileNotFoundError:
        print(f"Error: Sample data file not found at {data_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading sample data: {e}")
        sys.exit(1)

def query_data(engine) -> None:
    """Run and display some sample queries using SQLAlchemy."""
    try:
        # Create a session to interact with the database
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("\n----- Database Query Results -----")
        
        # Query 1: All products
        print("\nAll Products:")
        products = session.query(Product).order_by(Product.id).all()
        for product in products:
            print(f"ID: {product.id}, Name: {product.name}, Category: {product.category}, Price: ${product.price}, In Stock: {product.in_stock}")
        
        # Query 2: Group by category
        print("\nProducts by Category:")
        # SQLAlchemy way to group by category and calculate avg price
        category_stats = session.query(
            Product.category,
            func.count(Product.id).label('count'),
            func.round(func.avg(Product.price), 2).label('avg_price')
        ).group_by(Product.category).order_by(func.count(Product.id).desc()).all()
        
        for category, count, avg_price in category_stats:
            print(f"Category: {category}, Count: {count}, Avg Price: ${avg_price}")
        
        # Query 3: In-stock products
        print("\nIn-Stock Products:")
        in_stock_count = session.query(Product).filter(Product.in_stock == True).count()
        print(f"Total in-stock products: {in_stock_count}")
        
        session.close()
    except Exception as e:
        print(f"Error querying data: {e}")
        sys.exit(1)

def main() -> None:
    """Main function to run the application."""
    print("Azure PostgreSQL Python Application")
    print("===================================")
    
    # Check environment variables
    check_env_vars()
    
    # Connect to PostgreSQL with SQLAlchemy
    engine = connect_to_database()
    
    # Create database schema
    create_tables(engine)
    
    # Load sample data
    load_sample_data(engine)
    
    # Query and display data
    query_data(engine)
    
    # No need to close the engine explicitly as SQLAlchemy handles connection pooling
    print("\nApplication completed successfully!")

if __name__ == "__main__":
    main()
