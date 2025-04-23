# B+ Tree Database Management System

## Overview
This project implements a custom database management system using B+ Trees for efficient indexing and data retrieval. The system provides a web-based interface for managing database tables, performing CRUD operations, and visualizing B+ Tree indices.

## Features

- **B+ Tree Indexing**: Efficient O(log n) search, insert, and delete operations
- **Table Management**: Create, view, and delete tables
- **Record Operations**: Insert, update, and delete records
- **Query Capabilities**: 
  - Exact match queries using any indexed column
  - Range queries for efficient data retrieval
- **MySQL Integration**: Import tables directly from MySQL databases
- **Index Management**: Create and visualize indices on any column
- **BLOB Support**: Store and view binary objects like images
- **Visualization**: Interactive visualization of B+ Tree structures
- **Performance Analysis**: Compare B+ Tree performance with brute force approaches

## System Architecture

The system consists of several key components:

1. **Core Database Engine**:
   - B+ Tree implementation for efficient indexing
   - Table structure for organizing records
   - Database manager for high-level operations

2. **Web Interface**:
   - Flask-based web application
   - Bootstrap UI framework for responsive design
   - Interactive visualizations using Graphviz

3. **Persistence Layer**:
   - Disk-based storage for tables and indices
   - Serialization/deserialization of B+ Tree structures

## Setup and Installation

### Prerequisites
- Python 3.7+
- MySQL (optional, for import functionality)
- Graphviz (for B+ Tree visualization)

### Installation Steps

1. Clone the repository

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install Graphviz (for visualization):
   - On macOS: `brew install graphviz`
   - On Ubuntu: `sudo apt-get install graphviz`
   - On Windows: Download from https://graphviz.org/download/

4. Configure MySQL connection (optional):
   - Edit the database connection settings in `app.py` if you plan to import from MySQL

5. Run the application:
   ```
   python app.py
   ```

6. Access the web interface at `http://localhost:5000`

## Usage Guide

### Creating Tables
1. Navigate to "Create New Table" in the sidebar
2. Enter table name and define columns
3. Designate a primary key column
4. Submit the form to create the table

### Importing from MySQL
1. Click "Import from MySQL" in the sidebar
2. Select a table from the dropdown list
3. Click "Import Selected Table" to import the table structure and data
4. Configure your database connection from line 26 of app.py

### Managing Records
1. Navigate to a table from the dashboard
2. Use "Insert Record" to add new records
3. Use table actions to view, edit, or delete records

### Creating Indices
1. Open a table view
2. In the Indices section, click "Create Index"
3. Select the column you want to index
4. Click "Create Index" to build the B+ Tree index

### Visualizing B+ Trees
1. In the table view, locate the Indices section
2. Click "Visualize" next to the index you want to view
3. The system will display a graphical representation of the B+ Tree structure

### Searching Records
1. Open a table view
2. Use the search form at the top
3. Select a column, search type (exact or range), and enter value(s)
4. Click "Search" to execute the query

## Performance Analysis

The system includes a performance analyzer that compares B+ Tree operations with brute force approaches across various dataset sizes. The report in Jupyter Notebook format (`report.ipynb`) provides detailed analysis and visualizations of the performance characteristics.

Key findings from performance testing:
- B+ Trees provide significantly faster search operations, especially for large datasets
- Range queries show even greater performance advantages due to the linked leaf structure
- Insertion and deletion operations scale well with increasing dataset size
