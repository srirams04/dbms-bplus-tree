#!/usr/bin/env python3
"""
Table class for B+ Tree-based database tables
"""

from database.bplustree import BPlusTree

class Table:
    """Class representing a database table with B+ Tree indices."""
    
    def __init__(self, name, columns, primary_key):
        """Initialize a new table.
        
        Args:
            name: Name of the table
            columns: List of column names
            primary_key: Name of the primary key column
        """
        self.name = name
        self.columns = columns
        self.primary_key = primary_key
        self.records = []
        self.indices = {}  # Maps column name to BPlusTree
        self.record_ids = []  # List that maps record IDs to positions
        self.next_record_id = 0  # Counter for assigning unique record IDs
    
    def create_index(self, column):
        """Create an index on a column.
        
        Args:
            column: Column name to index
            
        Returns:
            bool: True if index was created, False if already exists
        """
        if column not in self.columns:
            raise ValueError(f"Column {column} does not exist")
            
        if column in self.indices:
            return False  # Index already exists
        
        # Create a new B+ Tree for this column
        tree = BPlusTree()
        self.indices[column] = tree
        
        # Add existing records to the index
        for i, record in enumerate(self.records):
            col_index = self.columns.index(column)
            key = record[col_index]
            tree.insert(key, self.record_ids[i])  # Store the record ID
            
        return True
    
    def insert(self, record):
        """Insert a record into the table.
        
        Args:
            record: List of values for each column
            
        Returns:
            bool: True if successful, False otherwise
        """
        if len(record) != len(self.columns):
            raise ValueError(f"Record has {len(record)} fields, but table has {len(self.columns)} columns")
        
        # Ensure primary key is unique
        pk_index = self.columns.index(self.primary_key)
        pk_value = record[pk_index]
        
        # Check if primary key already exists (using primary key index)
        if self.primary_key in self.indices:
            pk_tree = self.indices[self.primary_key]
            if pk_tree.find(pk_value) is not None:
                raise ValueError(f"Record with primary key {pk_value} already exists")
        else:
            # Linear search if no index exists (shouldn't happen as primary key index is created by default)
            for existing_record in self.records:
                if existing_record[pk_index] == pk_value:
                    raise ValueError(f"Record with primary key {pk_value} already exists")
        
        # Add the record
        record_id = self.next_record_id
        self.next_record_id += 1
        record_index = len(self.records)
        self.records.append(record)
        self.record_ids.append(record_id)
        
        # Update all indices - store record_id instead of position
        for column, tree in self.indices.items():
            col_index = self.columns.index(column)
            key = record[col_index]
            tree.insert(key, record_id)
            
        return True
    
    def _get_record_by_id(self, record_id):
        """Get a record by its ID."""
        try:
            index = self.record_ids.index(record_id)
            return self.records[index]
        except ValueError:
            return None
    
    def _get_index_by_id(self, record_id):
        """Get a record's index by its ID."""
        try:
            return self.record_ids.index(record_id)
        except ValueError:
            return -1
    
    def select_all(self):
        """Select all records from the table.
        
        Returns:
            list: List of all records
        """
        return list(self.records)  # Return a copy to prevent modification
    
    def select(self, column, value):
        """Select records where column equals value."""
        if column not in self.columns:
            raise ValueError(f"Column {column} does not exist")
        
        col_index = self.columns.index(column)
        
        # Try to normalize the search value type if it's a string
        normalized_value = value
        if isinstance(value, str):
            if value.isdigit():
                normalized_value = int(value)
            
        # Use index if available
        if column in self.indices:
            tree = self.indices[column]
            # Try with original value
            record_ids = tree.find(value)
            
            # If not found, try with normalized value (if different)
            if record_ids is None and normalized_value != value:
                record_ids = tree.find(normalized_value)
                
            # If still no matches found
            if record_ids is None:
                return []
                
            # Handle both single index and list of indices
            if not isinstance(record_ids, list):
                record_ids = [record_ids]
            
            # Convert record IDs to records
            return [self._get_record_by_id(rid) for rid in record_ids if self._get_record_by_id(rid) is not None]
        else:
            # Linear search if no index
            result = []
            for record in self.records:
                record_value = record[col_index]
                
                # Try direct comparison
                if record_value == value or record_value == normalized_value:
                    result.append(record)
                    continue
                
                # Try string comparison as last resort
                if str(record_value) == str(value):
                    result.append(record)
                    
            return result
    
    def range_select(self, column, start_value, end_value):
        """Select records where column is in the given range."""
        if column not in self.columns:
            raise ValueError(f"Column {column} does not exist")
        
        # Try to convert string values to numbers if possible
        if isinstance(start_value, str) and start_value.isdigit():
            start_value = int(start_value)
        if isinstance(end_value, str) and end_value.isdigit():
            end_value = int(end_value)
            
        # If types still don't match, convert everything to strings for comparison
        col_index = self.columns.index(column)
        
        # Use index if available
        if column in self.indices:
            tree = self.indices[column]
            record_ids = tree.range_search(start_value, end_value)
            
            # If no matches found
            if not record_ids:
                return []
                
            return [self._get_record_by_id(rid) for rid in record_ids if self._get_record_by_id(rid) is not None]
        else:
            # Linear search if no index
            result = []
            for record in self.records:
                record_value = record[col_index]
                
                # Convert record value to match start/end value types
                if isinstance(start_value, int) and isinstance(record_value, str) and record_value.isdigit():
                    record_value = int(record_value)
                elif isinstance(record_value, int) and isinstance(start_value, str):
                    # Convert everything to strings for comparison
                    record_value = str(record_value)
                    if isinstance(start_value, str):
                        start_value = start_value
                    if isinstance(end_value, str):  
                        end_value = end_value
                
                # Do the comparison
                try:
                    if start_value <= record_value <= end_value:
                        result.append(record)
                except TypeError:
                    # If comparison fails, convert everything to strings as a last resort
                    if str(start_value) <= str(record_value) <= str(end_value):
                        result.append(record)
                
            return result
    
    def _convert_value_for_comparison(self, value):
        """Convert a value to appropriate type for comparison.
        
        Args:
            value: The value to convert
            
        Returns:
            The converted value
        """
        if isinstance(value, str):
            # Try to convert to int or float if it looks like a number
            try:
                if value.isdigit():
                    return int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') < 2:
                    return float(value)
            except (ValueError, AttributeError):
                pass
        return value
    
    def update(self, condition_col, condition_val, update_col, update_val):
        """Update records where condition_col equals condition_val.
        
        Args:
            condition_col: Column name for the condition
            condition_val: Value to match in condition
            update_col: Column name to update
            update_val: New value for the column
            
        Returns:
            int: Number of records updated
        """
        if condition_col not in self.columns:
            raise ValueError(f"Column {condition_col} does not exist")
        
        if update_col not in self.columns:
            raise ValueError(f"Column {update_col} does not exist")
        
        # Prevent changing the primary key
        if update_col == self.primary_key:
            raise ValueError("Cannot update primary key")
        
        # Find records to update
        condition_col_index = self.columns.index(condition_col)
        update_col_index = self.columns.index(update_col)
        
        # Use index for finding records if available
        if condition_col in self.indices:
            tree = self.indices[condition_col]
            record_ids = tree.find(condition_val)
            
            # If no matches found
            if record_ids is None:
                return 0
                
            # Handle both single index and list of indices
            if not isinstance(record_ids, list):
                record_ids = [record_ids]
        else:
            # Linear search if no index
            record_ids = []
            for i, record in enumerate(self.records):
                if record[condition_col_index] == condition_val:
                    record_ids.append(self.record_ids[i])
        
        # Update the records
        count = 0
        for record_id in record_ids:
            record_index = self._get_index_by_id(record_id)
            if record_index == -1:
                continue  # Record not found
            
            old_value = self.records[record_index][update_col_index]
            self.records[record_index][update_col_index] = update_val
            
            # Update the index if it exists for the updated column
            if update_col in self.indices:
                tree = self.indices[update_col]
                tree.delete(old_value)  # Remove old value
                tree.insert(update_val, record_id)  # Insert new value
                
            count += 1
            
        return count
    
    def delete(self, condition_col, condition_val):
        """Delete records where condition_col equals condition_val.
        
        Args:
            condition_col: Column name for the condition
            condition_val: Value to match
            
        Returns:
            int: Number of records deleted
        """
        if condition_col not in self.columns:
            raise ValueError(f"Column {condition_col} does not exist")
        
        condition_col_index = self.columns.index(condition_col)
        
        # Find records to delete (either by index or linear search)
        record_ids_to_delete = []
        
        # Use index if available
        if condition_col in self.indices:
            tree = self.indices[condition_col]
            found_ids = tree.find(condition_val)
            
            # If no matches found
            if found_ids is None:
                return 0
                
            # Handle both single ID and list of IDs
            if not isinstance(found_ids, list):
                found_ids = [found_ids]
                
            record_ids_to_delete = found_ids
        else:
            # Linear search if no index
            for i, record in enumerate(self.records):
                if record[condition_col_index] == condition_val:
                    record_ids_to_delete.append(self.record_ids[i])
        
        # Delete the records
        count = 0
        for record_id in record_ids_to_delete:
            record_index = self._get_index_by_id(record_id)
            if record_index == -1:
                continue  # Record not found
            
            record = self.records[record_index]
            
            # Remove from all indices
            for column, tree in self.indices.items():
                col_index = self.columns.index(column)
                key = record[col_index]
                tree.delete(key)  # This will remove the record_id, not position
            
            # Remove from records list and record_ids list
            del self.records[record_index]
            del self.record_ids[record_index]
            
            count += 1
        
        return count
    
    def delete_all(self):
        """Delete all records from the table.
        
        Returns:
            int: Number of records deleted
        """
        count = len(self.records)
        self.records = []
        self.record_ids = []
        self.next_record_id = 0
        
        # Clear all indices (easiest to rebuild them)
        for column in self.indices:
            self.indices[column] = BPlusTree()
            
        return count