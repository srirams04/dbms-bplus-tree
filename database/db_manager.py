#!/usr/bin/env python3
"""
DatabaseManager for B+ Tree database management system
"""

import os
import pickle
from database.table import Table
from database.bplustree import BPlusTree

class DatabaseManager:
    """Manager class for B+ Tree database operations."""
    
    def __init__(self, db_dir):
        """Initialize the database manager.
        
        Args:
            db_dir: Directory to store database files
        """
        self.db_dir = db_dir
        self._tables = {}
        self.load_all()
    
    def get_tables(self):
        """Get a list of all tables in the database.
        
        Returns:
            list: List of table names
        """
        return list(self._tables.keys())
    
    def create_table(self, table_name, columns, primary_key):
        """Create a new table.
        
        Args:
            table_name: Name of the table
            columns: List of column names
            primary_key: Name of the primary key column
            
        Returns:
            Table: The created table
        """
        if table_name in self._tables:
            raise ValueError(f"Table {table_name} already exists")
        
        if primary_key not in columns:
            raise ValueError(f"Primary key {primary_key} not in columns")
        
        table = Table(table_name, columns, primary_key)
        self._tables[table_name] = table
        
        # Create an index on the primary key
        table.create_index(primary_key)
        
        # Save the table to disk
        self._save_table(table)
        
        return table
    
    def drop_table(self, table_name):
        """Drop a table.
        
        Args:
            table_name: Name of the table to drop
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        # Remove from memory
        del self._tables[table_name]
        
        # Remove from disk
        table_path = os.path.join(self.db_dir, f"{table_name}.table")
        if os.path.exists(table_path):
            os.remove(table_path)
    
    def insert(self, table_name, record):
        """
        Insert a record into a table.
        
        Args:
            table_name: Name of the table
            record: List of values for the record
            
        Returns:
            Boolean: True if successful
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        columns = table.columns
        primary_key_idx = columns.index(table.primary_key)
        
        # Convert the primary key value to correct type before insertion
        pk_value = record[primary_key_idx]
        
        # Handle type conversion for primary key comparisons
        if isinstance(pk_value, str) and pk_value.isdigit():
            try:
                record[primary_key_idx] = int(pk_value)
            except ValueError:
                pass  # Keep as string if conversion fails
        
        # Insert record into table and update indices
        return table.insert(record)
    
    def select(self, table_name, condition_col=None, condition_val=None, range_start=None, range_end=None):
        """Select records from a table.
        
        Args:
            table_name: Name of the table
            condition_col: Column name for condition (optional)
            condition_val: Value to match in condition (optional)
            range_start: Start value for range queries (optional)
            range_end: End value for range queries (optional)
            
        Returns:
            list: List of records matching the condition
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        
        # If no condition, return all records
        if not condition_col:
            return table.select_all()
        
        # If range query
        if range_start is not None and range_end is not None:
            return table.range_select(condition_col, range_start, range_end)
            
        # If exact match
        return table.select(condition_col, condition_val)
    
    def update(self, table_name, condition_col, condition_val, update_col, update_val):
        """Update records in a table.
        
        Args:
            table_name: Name of the table
            condition_col: Column name for condition
            condition_val: Value to match in condition
            update_col: Column name to update
            update_val: New value for the column
            
        Returns:
            int: Number of records updated
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        count = table.update(condition_col, condition_val, update_col, update_val)
        self._save_table(table)
        return count
    
    def delete(self, table_name, condition_col=None, condition_val=None):
        """Delete records from a table.
        
        Args:
            table_name: Name of the table
            condition_col: Column name for condition (optional)
            condition_val: Value to match in condition (optional)
            
        Returns:
            int: Number of records deleted
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        
        # If no condition, delete all records
        if not condition_col:
            count = table.delete_all()
        else:
            count = table.delete(condition_col, condition_val)
            
        self._save_table(table)
        return count
    
    def create_index(self, table_name, column):
        """Create an index on a column.
        
        Args:
            table_name: Name of the table
            column: Column name to index
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        table.create_index(column)
        self._save_table(table)
    
    def get_table_info(self, table_name):
        """Get information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Dictionary containing table information
        """
        if table_name not in self._tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self._tables[table_name]
        return {
            'name': table.name,
            'columns': table.columns,
            'primary_key': table.primary_key,
            'indices': list(table.indices.keys()),
            'record_count': len(table.records)
        }
    
    def _save_table(self, table):
        """Save a table to disk.
        
        Args:
            table: The table to save
        """
        os.makedirs(self.db_dir, exist_ok=True)
        table_path = os.path.join(self.db_dir, f"{table.name}.table")
        with open(table_path, 'wb') as f:
            pickle.dump(table, f)
    
    def _load_table(self, table_name):
        """Load a table from disk.
        
        Args:
            table_name: Name of the table to load
            
        Returns:
            Table: The loaded table, or None if not found
        """
        table_path = os.path.join(self.db_dir, f"{table_name}.table")
        if not os.path.exists(table_path):
            return None
        
        with open(table_path, 'rb') as f:
            return pickle.load(f)
    
    def load_all(self):
        """Load all tables from disk."""
        # Reset tables
        self._tables = {}
        
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
            return
        
        # Find all table files
        for filename in os.listdir(self.db_dir):
            if filename.endswith('.table'):
                table_name = filename[:-6]  # Remove .table extension
                table = self._load_table(table_name)
                if table:
                    self._tables[table_name] = table
    
    def save_all(self):
        """Save all tables to disk."""
        for table in self._tables.values():
            self._save_table(table)