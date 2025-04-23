#!/usr/bin/env python3
"""
Brute Force Database Implementation
This module provides a simple brute force database implementation for comparison with the B+ tree.
"""

class BruteForceDB:
    """A simple brute force database implementation that uses linear search."""
    
    def __init__(self):
        """Initialize an empty brute force database."""
        self.data = []  # List of (key, value) tuples
    
    def insert(self, key, value):
        """Insert a key-value pair into the database.
        
        If the key already exists, its value is updated.
        
        Args:
            key: The key to insert
            value: The value to associate with the key
        
        Returns:
            bool: True if successful
        """
        # Check if key already exists - brute force sequential search
        for i, (k, _) in enumerate(self.data):
            if k == key:
                # Update existing key
                self.data[i] = (key, value)
                return True
        
        # Key doesn't exist, append new entry
        self.data.append((key, value))
        return True
    
    def delete(self, key):
        """Delete a key-value pair from the database.
        
        Args:
            key: The key to delete
        
        Returns:
            bool: True if the key was found and deleted, False otherwise
        """
        for i, (k, _) in enumerate(self.data):
            if k == key:
                del self.data[i]
                return True
        return False
    
    def find(self, key):
        """Find a value associated with a key.
        
        Args:
            key: The key to search for
        
        Returns:
            The value associated with the key, or None if the key is not found
        """
        # Brute force sequential search
        for k, v in self.data:
            if k == key:
                return v
        return None
    
    def range_search(self, start_key, end_key):
        """Find all values with keys in the specified range.
        
        Time complexity: O(n) where n is the total number of keys in the database.
        
        Args:
            start_key: Start of the range (inclusive)
            end_key: End of the range (inclusive)
            
        Returns:
            list: List of (key, value) pairs for keys in the range
        """
        result = []
        
        # Pure brute force approach - scan through all elements
        for key, value in self.data:
            if start_key <= key <= end_key:
                result.append((key, value))
        
        return result

    def display(self):
        """Display the contents of the database.
        
        Returns:
            str: A string representation of the database contents
        """
        if not self.data:
            return "Empty database"
        
        result = "BruteForceDB contents:\n"
        for k, v in sorted(self.data):
            result += f"{k}: {v}\n"
        return result
    
    def save_to_file(self, filename):
        """Save the database to a file.
        
        Args:
            filename: The path to save the database
            
        Returns:
            bool: True if successful
        """
        import pickle
        
        try:
            with open(filename, 'wb') as file:
                pickle.dump(self.data, file)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filename):
        """Load a database from a file.
        
        Args:
            filename: The path to load the database from
            
        Returns:
            BruteForceDB: The loaded database
        """
        import pickle
        import os
        
        # Check if the file exists
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Database file not found: {filename}")
        
        try:
            with open(filename, 'rb') as file:
                db = cls()
                db.data = pickle.load(file)
                return db
        except Exception as e:
            raise RuntimeError(f"Error loading database: {e}")
    
    def serialize(self):
        """Serialize the database to a dictionary for storage.
        
        Returns:
            dict: A serialized representation of the database
        """
        return {'data': self.data}
    
    @classmethod
    def deserialize(cls, data):
        """Deserialize a dictionary back to a database.
        
        Args:
            data: The serialized database data
            
        Returns:
            BruteForceDB: The reconstructed database
        """
        db = cls()
        db.data = data['data']
        return db