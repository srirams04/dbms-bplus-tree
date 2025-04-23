#!/usr/bin/env python3
"""
MySQL adapter for importing data into B+ Tree database
"""

import mysql.connector
import re
from database.table import Table
from database.bplustree import BPlusTree

def process_blob_field(value):
    """Process a blob field to make it displayable or storable."""
    if value is None:
        return None
        
    # If it's already bytes or bytearray, return as is
    if isinstance(value, (bytes, bytearray)):
        return value
        
    # For binary data stored as a string representation, try to convert
    if isinstance(value, str) and value.startswith('bytearray('):
        try:
            import ast
            return bytes(ast.literal_eval(value))
        except Exception as e:
            print(f"Error converting string to bytes: {e}")
            return value
        
    # Return as is for other types
    return value

class MySQLAdapter:
    """Adapter class for MySQL database interaction."""
    
    def __init__(self, config):
        """Initialize with MySQL connection details.
        
        Args:
            config: A dictionary with MySQL connection parameters
        """
        self.config = config
        self._connection = None
    
    @property
    def connection(self):
        """Get a MySQL connection, creating it if necessary."""
        if self._connection is None or not self._connection.is_connected():
            self._connection = mysql.connector.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                port=self.config['port'],
                database=self.config['database']
            )
        return self._connection
    
    def close(self):
        """Close the MySQL connection."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None
    
    def get_tables(self):
        """Get a list of tables in the MySQL database.
        
        Returns:
            list: List of table names
        """
        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        cursor.close()
        return tables
    
    def get_table_structure(self, table_name):
        """Get the structure of a MySQL table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            tuple: (columns, primary_key) where columns is a list of column
                  names and primary_key is the name of the primary key column
        """
        cursor = self.connection.cursor()
        
        # Get columns
        cursor.execute(f"DESCRIBE {table_name}")
        columns = []
        primary_key = None
        
        for column in cursor:
            column_name = column[0]
            columns.append(column_name)
            if column[3] == 'PRI':  # Primary key
                primary_key = column_name
        
        cursor.close()
        
        # Check if there's a primary key
        if not primary_key and columns:
            # If no primary key found, check if there's an AUTO_INCREMENT column
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            for column in cursor:
                column_name = column[0]
                extra_info = column[5]  # Contains 'auto_increment' if that's set
                if 'auto_increment' in str(extra_info).lower():
                    primary_key = column_name
                    break
            cursor.close()
        
        return columns, primary_key
    
    def import_table_to_bplustree(self, table_name, db_manager):
        """Import a MySQL table into a B+ Tree table."""
        try:
            # Get table structure
            columns, primary_key = self.get_table_structure(table_name)
            
            if not primary_key:
                return False, "Table must have a primary key. Tables without a primary key cannot be imported."
            
            # Check if table already exists
            if table_name in db_manager.get_tables():
                return False, f"Table {table_name} already exists in B+ Tree database"
            
            print(f"Importing table {table_name} with primary key: {primary_key}")
            
            # Use a prepared cursor with buffered=False for handling large binary data
            cursor = self.connection.cursor(prepared=True, buffered=False)
            
            # Create table in B+ Tree database
            db_manager.create_table(table_name, columns, primary_key)
            
            # Get column types to identify BLOB fields
            column_types = self._get_column_types(table_name)
            print(f"Column types for {table_name}: {column_types}")
            
            # Get data from MySQL table - use column names explicitly for reliable ordering
            columns_str = ", ".join(columns)
            cursor.execute(f"SELECT {columns_str} FROM {table_name}")
            
            # Process the rows one by one to avoid memory issues with large BLOBs
            row_count = 0
            
            while True:
                record = cursor.fetchone()
                if record is None:
                    break
                
                processed_record = []
                for i, value in enumerate(record):
                    if value is None:
                        processed_record.append(None)
                    elif isinstance(value, (bytes, bytearray)):
                        # Store the binary data directly - don't convert to string representation
                        processed_record.append(value)
                        print(f"Processed BLOB in column {columns[i]} - size: {len(value)} bytes")
                    else:
                        processed_record.append(value)
                
                # Make sure primary key is not None
                pk_index = columns.index(primary_key)
                if processed_record[pk_index] is None:
                    print(f"Skipping row {row_count} with NULL primary key in column {primary_key}")
                    continue
                
                # For debug, print the record types
                record_types = [f"{columns[i]}: {type(val)}" for i, val in enumerate(processed_record)]
                print(f"Record {row_count} types: {record_types}")
                
                db_manager.insert(table_name, processed_record)
                row_count += 1
                
                # Log progress for large imports
                if row_count % 100 == 0:
                    print(f"Imported {row_count} records so far...")
            
            # Save the table to persist changes
            db_manager.save_all()
            
            cursor.close()
            return True, f"Successfully imported {row_count} records"
        except Exception as e:
            import traceback
            print(f"Error importing table: {str(e)}")
            print(traceback.format_exc())
            return False, str(e)

    def _get_column_types(self, table_name):
        """Get column types for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Dictionary mapping column names to their MySQL data types
        """
        cursor = self.connection.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        column_types = {}
        
        for column in cursor:
            column_name = column[0]
            column_type = column[1]
            column_types[column_name] = column_type
        
        cursor.close()
        return column_types
    
    def __del__(self):
        """Ensure connection is closed when object is destroyed."""
        self.close()