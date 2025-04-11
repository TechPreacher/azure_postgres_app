"""
Streamlit App for Azure PostgreSQL Product Management

This app allows users to:
1. View existing products in the database
2. Create new orders for products
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from typing import Any, Dict, List, Optional

# SQLAlchemy imports
from sqlalchemy import (
    Engine,
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import desc

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    st.error(
        "Warning: .env file not found. "
        "Please create one with your database credentials."
    )
    st.stop()

# Database connection parameters
DB_CONFIG = {
    "host": os.environ.get("AZURE_POSTGRES_HOST"),
    "user": os.environ.get("AZURE_POSTGRES_USER"),
    "password": os.environ.get("AZURE_POSTGRES_PASSWORD"),
    "database": os.environ.get("AZURE_POSTGRES_DB"),
    "sslmode": os.environ.get("AZURE_POSTGRES_SSL_MODE", "require"),
}

# Define SQLAlchemy Base and Models
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float(precision=10, decimal_return_scale=2), nullable=False)
    in_stock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship with Order model
    orders = relationship("Order", back_populates="product")

    def __repr__(self) -> str:
        return (f"<Product(id={self.id}, name='{self.name}', "
                f"category='{self.category}', price={self.price})>")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    order_date = Column(DateTime, server_default=func.now())

    # Relationship with Product model
    product = relationship("Product", back_populates="orders")

    def __repr__(self) -> str:
        return (f"<Order(id={self.id}, product_id={self.product_id}, "
                f"quantity={self.quantity})>")


# Check if all required environment variables are set
def check_env_vars() -> None:
    """Verify all required environment variables are set."""
    required_vars = [
        "AZURE_POSTGRES_HOST",
        "AZURE_POSTGRES_USER",
        "AZURE_POSTGRES_PASSWORD",
        "AZURE_POSTGRES_DB",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        st.error(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        st.error("Please create a .env file with your Azure PostgreSQL credentials.")
        st.stop()


@st.cache_resource
def init_connection() -> Engine:
    """Connect to PostgreSQL database using SQLAlchemy."""
    try:
        # Create the connection string
        user = DB_CONFIG['user']
        pw = DB_CONFIG['password']
        host = DB_CONFIG['host']
        db = DB_CONFIG['database']
        ssl = DB_CONFIG['sslmode']
        conn_str = f"postgresql+psycopg2://{user}:{pw}@{host}/{db}"
        connection_string = f"{conn_str}?sslmode={ssl}"

        # Create the SQLAlchemy engine
        engine = create_engine(connection_string, echo=False)

        # Return the engine that can be used to create sessions
        return engine
    except Exception as e:
        st.error(f"Error connecting to PostgreSQL: {e}")
        st.stop()


@st.cache_data(ttl=5)
def get_products() -> List[Dict[str, Any]]:
    """Fetch all products from the database using SQLAlchemy."""
    engine = init_connection()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query all products and order by id
        products = session.query(Product).order_by(Product.created_at).all()

        # Convert SQLAlchemy objects to dictionaries
        products_list = []
        for product in products:
            products_list.append(
                {
                    "id": str(product.id),
                    "name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "in_stock": product.in_stock,
                }
            )

        session.close()
        return products_list
    except Exception as e:
        session.close()
        st.error(f"Error fetching products: {e}")
        return []


@st.cache_data(ttl=5)
def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific product by ID using SQLAlchemy."""
    engine = init_connection()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query product by id
        product = session.query(Product).filter(Product.id == product_id).first()

        if product:
            # Convert SQLAlchemy object to dictionary
            product_dict = {
                "id": str(product.id),
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "in_stock": product.in_stock,
            }

            session.close()
            return product_dict
        else:
            session.close()
            return None
    except Exception as e:
        session.close()
        st.error(f"Error fetching product: {e}")
        return None


def create_order(product_id: str, quantity: int) -> Optional[Dict[str, Any]]:
    """Create a new order in the database using SQLAlchemy."""
    engine = init_connection()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create a new Order object
        new_order = Order(product_id=product_id, quantity=quantity)

        # Add the new order to the session
        session.add(new_order)

        # Commit the transaction
        session.commit()

        # Refresh the order to get the generated ID and default values
        session.refresh(new_order)

        # Convert to dictionary for consistent return format
        order_dict = {
            "id": str(new_order.id),
            "product_id": str(new_order.product_id),
            "quantity": new_order.quantity,
            "order_date": new_order.order_date,
        }

        session.close()
        return order_dict
    except Exception as e:
        session.rollback()
        session.close()
        st.error(f"Error creating order: {e}")
        return None


@st.cache_data(ttl=5)
def get_orders() -> List[Dict[str, Any]]:
    """Fetch all orders with product details using SQLAlchemy."""
    engine = init_connection()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query orders joined with products
        orders = (
            session.query(
                Order.id,
                Order.quantity,
                Order.order_date,
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.price,
                (Product.price * Order.quantity).label("total_price"),
            )
            .join(Product)
            .order_by(desc(Order.order_date))
            .all()
        )

        # Convert result to list of dictionaries
        orders_list = []
        for order in orders:
            orders_list.append(
                {
                    "id": str(order.id),
                    "quantity": order.quantity,
                    "order_date": order.order_date,
                    "product_id": str(order.product_id),
                    "product_name": order.product_name,
                    "price": order.price,
                    "total_price": order.total_price,
                }
            )

        session.close()
        return orders_list
    except Exception as e:
        session.close()
        st.error(f"Error fetching orders: {e}")
        return []


def product_list_view() -> None:
    """Display the list of products."""
    st.header("Products")

    products = get_products()

    if not products:
        st.info("No products found in the database.")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(products)

    # Format price as currency
    df["price"] = df["price"].apply(lambda x: f"${float(x):.2f}")

    # Rename columns for better display
    df = df.rename(
        columns={
            "id": "ID",
            "name": "Product Name",
            "category": "Category",
            "price": "Price",
            "in_stock": "In Stock",
        }
    )

    st.dataframe(df, use_container_width=True)


def order_creation_view() -> None:
    """Display the order creation form."""
    st.header("Create New Order")

    products = get_products()

    if not products:
        st.info("No products available for ordering.")
        return

    # Create a dropdown to select product
    product_options = {
        f"{p['name']} (${float(p['price']):.2f})": p["id"]
        for p in products
        if p["in_stock"]
    }

    if not product_options:
        st.warning("No products in stock for ordering.")
        return

    selected_product_label = st.selectbox(
        "Select a product:", options=list(product_options.keys())
    )

    selected_product_id = product_options[selected_product_label]

    # Show product details
    product = get_product_by_id(selected_product_id)

    if product:
        st.write(f"Category: {product['category']}")

    # Quantity input
    quantity = st.number_input("Quantity:", min_value=1, max_value=100, value=1)

    # Calculate and show total price
    if product:
        total_price = float(product["price"]) * quantity
        st.write(f"Total Price: ${total_price:.2f}")

    # Submit order button
    if st.button("Place Order"):
        if product and not product["in_stock"]:
            st.error("This product is out of stock!")
        elif product:
            order = create_order(selected_product_id, quantity)
            if order:
                st.success("Order created successfully!")
                # Rerun to refresh the UI
                st.rerun()


def orders_list_view() -> None:
    """Display the list of existing orders."""
    st.header("Order History")

    orders = get_orders()

    if not orders:
        st.info("No orders found in the database.")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(orders)

    # Format dates and prices
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.strftime("%Y-%m-%d %H:%M")
    df["price"] = df["price"].apply(lambda x: f"${float(x):.2f}")
    df["total_price"] = df["total_price"].apply(lambda x: f"${float(x):.2f}")

    # Rename columns for better display
    df = df.rename(
        columns={
            "id": "Order ID",
            "product_id": "Product ID",
            "product_name": "Product",
            "quantity": "Quantity",
            "price": "Unit Price",
            "total_price": "Total Price",
            "order_date": "Order Date",
        }
    )

    # Reorder columns for better display
    columns = [
        "Order ID",
        "Product",
        "Quantity",
        "Unit Price",
        "Total Price",
        "Order Date",
    ]
    df = df[columns]

    st.dataframe(df, use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="Product & Order Management", page_icon="🛒", layout="wide"
    )

    st.title("Azure PostgreSQL Product Management")

    # Check environment variables
    check_env_vars()

    # Create tabs for different sections of the app
    tab1, tab2, tab3 = st.tabs(["Products", "Create Order", "Order History"])

    with tab1:
        product_list_view()

    with tab2:
        order_creation_view()

    with tab3:
        orders_list_view()


if __name__ == "__main__":
    main()
