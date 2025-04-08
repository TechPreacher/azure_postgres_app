# Azure PostgreSQL Python Application

This Python application initializes and populates an Azure Database for PostgreSQL instance with sample data using SQLAlchemy ORM.

## Features

- Connects to Azure Database for PostgreSQL using SQLAlchemy
- Defines data models with SQLAlchemy ORM
- Creates database schema with tables
- Populates tables with sample data
- Demonstrates basic database queries
- Handles environment variables for secure connection

## Prerequisites

- Python 3.8+
- Poetry dependency manager
- Azure Database for PostgreSQL instance
- Database user with appropriate permissions

## Setup

1. Clone this repository
2. Install dependencies with Poetry:
   ```
   # Install Poetry if you haven't already
   # curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   ```
3. Create a `.env` file with your Azure PostgreSQL credentials (use `.env.example` as a template):
   ```
   cp .env.example .env
   ```
4. Edit the `.env` file with your actual database credentials:
   ```
   AZURE_POSTGRES_HOST=your-server.postgres.database.azure.com
   AZURE_POSTGRES_USER=your-username
   AZURE_POSTGRES_PASSWORD=your-password
   AZURE_POSTGRES_DB=your-database
   AZURE_POSTGRES_SSL_MODE=require
   ```

## Running the Application

### CLI Application
Run the CLI application with Poetry:
```
poetry run python app.py
```

The CLI application will:
1. Connect to your Azure PostgreSQL database
2. Create tables (products and orders)
3. Import sample product data
4. Run sample queries to demonstrate functionality

### Streamlit Web Application
Run the Streamlit web application with Poetry:
```
poetry run streamlit run streamlit_app.py
```

The Streamlit web application provides an interactive interface to:
1. View all products in the database
2. Create new orders for in-stock products
3. View order history and details

## Database Schema

### Products Table
- id: Serial Primary Key
- name: VARCHAR(100)
- category: VARCHAR(50)
- price: DECIMAL(10,2)
- in_stock: BOOLEAN
- created_at: TIMESTAMP

### Orders Table
- id: Serial Primary Key
- product_id: Foreign Key to products.id
- quantity: INTEGER
- order_date: TIMESTAMP

## Customizing Sample Data

You can modify the sample data in `data/sample_data.json` to include your own product data.

## Azure PostgreSQL Configuration

To create an Azure Database for PostgreSQL instance, you can use the Azure Portal or Azure CLI:

```bash
# Using Azure CLI
az postgres server create \
  --resource-group myResourceGroup \
  --name mypostgresserver \
  --location westus \
  --admin-user mylogin \
  --admin-password <server_admin_password> \
  --sku-name GP_Gen5_2
```

Then create a database:
```bash
az postgres db create \
  --resource-group myResourceGroup \
  --server-name mypostgresserver \
  --name mydatabase
```