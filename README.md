# Azure PostgreSQL Application with Replication

A Python application that demonstrates working with Azure Database for PostgreSQL, including setting up logical replication between two PostgreSQL instances for high availability and read scaling.

## Features

- Connects to Azure Database for PostgreSQL using SQLAlchemy
- Defines data models with SQLAlchemy ORM
- Creates database schema with tables
- Sets up logical replication between two PostgreSQL instances:
  - Primary database (products) - source for writes
  - Replica database (sales) - for read operations
- Populates tables with sample data
- Demonstrates database queries
- Interactive web interface with Streamlit
- Environment variable handling for secure connections

## Prerequisites

- Python 3.8+
- Poetry dependency manager
- Two Azure Database for PostgreSQL instances (primary and replica)
- Database users with appropriate permissions (including REPLICATION attribute)
- PostgreSQL logical replication enabled (wal_level = logical)

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
4. Edit the `.env` file with your actual database credentials for both primary and replica:
   ```
   # Primary database configuration
   AZURE_POSTGRES_PRIMARY_HOST=primary-server.postgres.database.azure.com
   AZURE_POSTGRES_PRIMARY_USER=admin-user
   AZURE_POSTGRES_PRIMARY_PASSWORD=your-password
   AZURE_POSTGRES_PRIMARY_DB=products
   AZURE_POSTGRES_PRIMARY_SERVER_NAME=primary-server
   
   # Replica database configuration
   AZURE_POSTGRES_REPLICA_HOST=replica-server.postgres.database.azure.com
   AZURE_POSTGRES_REPLICA_USER=admin-user
   AZURE_POSTGRES_REPLICA_PASSWORD=your-password
   AZURE_POSTGRES_REPLICA_DB=sales
   AZURE_POSTGRES_REPLICA_SERVER_NAME=replica-server
   
   # SSL configuration
   AZURE_POSTGRES_SSL_MODE=require
   ```

## Running the Application

### Database Setup
Set up both database instances with the required schema:

```bash
# Run the setup script, which will ask which database(s) to set up
poetry run python database_setup.py
```

You'll be prompted to choose:
1. PRIMARY database only
2. REPLICA database only
3. BOTH databases

Alternatively, you can specify the database type directly:
```bash
# Set up primary database only
DB_TYPE=PRIMARY poetry run python database_setup.py

# Set up replica database only
DB_TYPE=REPLICA poetry run python database_setup.py

# Set up both databases
DB_TYPE=BOTH poetry run python database_setup.py
```

### PostgreSQL Replication Setup
After setting up both databases, configure logical replication between them:

```bash
poetry run python replication_setup.py
```

This will:
1. Check replication prerequisites on both servers
2. Create a publication on the primary server
3. Create a subscription on the replica server
4. Verify the replication status

**Note:** Ensure your database user has the REPLICATION attribute. You may need to run:
```sql
ALTER ROLE username WITH REPLICATION;
```

### Streamlit Web Application
Run the Streamlit web application:
```
poetry run streamlit run streamlit_app.py
```

The Streamlit web app provides an interactive interface to:
1. View all products in the database
2. Create new orders for in-stock products
3. View order history and details

## Database Schema

### Products Table
- id: Integer Primary Key
- name: String(100)
- category: String(50)
- price: Float
- in_stock: Boolean
- created_at: DateTime

### Orders Table
- id: Integer Primary Key
- product_id: Foreign Key to products.id
- quantity: Integer
- order_date: DateTime

## PostgreSQL Logical Replication

This application demonstrates PostgreSQL's built-in logical replication which:

- Replicates changes at the transaction level
- Allows selective replication of specific tables
- Requires the same table structure on both sides
- Doesn't require the same indexes or constraints

For logical replication to work, ensure:
1. Primary server has wal_level = logical
2. Sufficient max_replication_slots and max_wal_senders
3. Database user has REPLICATION privilege
4. Table structure exists on both primary and replica

## Customizing Sample Data

You can modify the sample data in `data/sample_data.json` to include your own product data.

## Azure PostgreSQL Configuration

For detailed instructions on setting up Azure Database for PostgreSQL instances with logical replication, refer to the [official Azure documentation](https://docs.microsoft.com/en-us/azure/postgresql/concepts-logical).