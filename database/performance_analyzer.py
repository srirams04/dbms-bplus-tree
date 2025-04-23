#!/usr/bin/env python3
"""
Performance Analyzer for DB Management System
This module provides tools for comparing the performance of different database implementations,
specifically the B+ tree implementation and a brute force approach.
"""

import time
import gc
import sys
import resource
import matplotlib.pyplot as plt
import numpy as np
from .bplustree import BPlusTree
from .bruteforce import BruteForceDB

class PerformanceAnalyzer:
    """Class to analyze and compare the performance of different database implementations."""
    
    def __init__(self):
        """Initialize the performance analyzer."""
        self.results = {
            'bplustree': {'insert': {}, 'search': {}, 'range_search': {}, 'delete': {}, 'memory': {}},
            'bruteforce': {'insert': {}, 'search': {}, 'range_search': {}, 'delete': {}, 'memory': {}}
        }
    
    @property
    def elements(self):
        """Get the sorted list of elements used in testing."""
        all_elements = set()
        for implementation in ['bplustree', 'bruteforce']:
            for operation in self.results[implementation]:
                all_elements.update(self.results[implementation][operation].keys())
        return sorted(all_elements)

    @property
    def bplus_insert_times(self):
        """Get the average insertion times for B+ Tree."""
        return [self._get_avg_time('bplustree', 'insert', n) for n in self.elements]

    @property
    def brute_insert_times(self):
        """Get the average insertion times for Brute Force."""
        return [self._get_avg_time('bruteforce', 'insert', n) for n in self.elements]

    @property
    def bplus_search_times(self):
        """Get the average search times for B+ Tree."""
        return [self._get_avg_time('bplustree', 'search', n) for n in self.elements]

    @property
    def brute_search_times(self):
        """Get the average search times for Brute Force."""
        return [self._get_avg_time('bruteforce', 'search', n) for n in self.elements]

    @property
    def bplus_range_times(self):
        """Get the average range search times for B+ Tree."""
        return [self._get_avg_time('bplustree', 'range_search', n) for n in self.elements]

    @property
    def brute_range_times(self):
        """Get the average range search times for Brute Force."""
        return [self._get_avg_time('bruteforce', 'range_search', n) for n in self.elements]

    @property
    def bplus_delete_times(self):
        """Get the average delete times for B+ Tree."""
        return [self._get_avg_time('bplustree', 'delete', n) for n in self.elements]

    @property
    def brute_delete_times(self):
        """Get the average delete times for Brute Force."""
        return [self._get_avg_time('bruteforce', 'delete', n) for n in self.elements]

    def _get_avg_time(self, implementation, operation, n):
        """Calculate average execution time for a specific implementation, operation, and element count."""
        if n not in self.results[implementation][operation] or not self.results[implementation][operation][n]:
            return 0
        return sum(self.results[implementation][operation][n]) / len(self.results[implementation][operation][n])
    
    def measure_execution_time(self, operation, implementation, **kwargs):
        """Measure execution time of a database operation.
        
        Args:
            operation (str): The operation to measure ('insert', 'search', etc.)
            implementation (str): The implementation to test ('bplustree' or 'bruteforce')
            **kwargs: Arguments specific to the operation
        
        Returns:
            float: The execution time in seconds
        """
        if implementation == 'bplustree':
            db = kwargs.get('db', BPlusTree())
        elif implementation == 'bruteforce':
            db = kwargs.get('db', BruteForceDB())
        else:
            raise ValueError(f"Unknown implementation: {implementation}")
        
        # Get operation parameters
        key = kwargs.get('key')
        value = kwargs.get('value')
        n = kwargs.get('n', 0)  # Number of elements in the database
        
        # Start timing
        start_time = time.time()
        
        # Perform the operation
        if operation == 'insert':
            db.insert(key, value)
        elif operation == 'search':
            db.find(key)
        elif operation == 'range_search':
            # Use multiple random search ranges instead of a fixed range
            import random
            num_ranges = kwargs.get('num_ranges', 100)  # Number of random ranges to test
            
            # Generate random ranges within the database size
            total_time = 0
            for _ in range(num_ranges):
                # Generate random start and end keys
                if n > 1:
                    start_key = random.randint(0, n-2)
                    end_key = random.randint(start_key+1, n-1)
                else:
                    start_key = 0
                    end_key = 0
                
                # Perform the range search
                if implementation == 'bplustree':
                    db.range_search(start_key, end_key)
                else:  # bruteforce
                    db.range_search(start_key, end_key)
                    
        elif operation == 'delete':
            db.delete(key)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # End timing
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Store the result
        if n not in self.results[implementation][operation]:
            self.results[implementation][operation][n] = []
        self.results[implementation][operation][n].append(execution_time)
        
        return execution_time
    
    def measure_memory_usage(self, implementation, n):
        """Measure memory usage of a database implementation with n elements.
        
        Args:
            implementation (str): The implementation to test ('bplustree' or 'bruteforce')
            n (int): Number of elements to insert
        
        Returns:
            float: The memory usage in MB
        """
        import sys
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Create empty database instance
        if implementation == 'bplustree':
            db = BPlusTree(order=5)  # Use consistent order parameter
        elif implementation == 'bruteforce':
            db = BruteForceDB()
        else:
            raise ValueError(f"Unknown implementation: {implementation}")
        
        # Use a fixed-length value to ensure consistent measurements
        value_str = "x" * 20  # 20-byte value for each key
        
        # Insert n elements
        for i in range(n):
            db.insert(i, value_str)
        
        # Get accurate memory measurement using sys.getsizeof and recursively for complex objects
        memory_usage = self._get_size(db) / (1024 * 1024)  # Convert bytes to MB
        
        # Store the result
        if n not in self.results[implementation]['memory']:
            self.results[implementation]['memory'][n] = []
        self.results[implementation]['memory'][n].append(memory_usage)
        
        return memory_usage

    def _get_size(self, obj, seen=None):
        """Recursively find the size of objects in memory.
        
        Args:
            obj: The object to measure
            seen: Set of already seen objects to handle circular references
            
        Returns:
            int: Size in bytes
        """
        import sys
        
        # Handle initial call
        if seen is None:
            seen = set()
        
        # Get object id to detect cycles
        obj_id = id(obj)
        
        # If we've seen this object before, don't count it again
        if obj_id in seen:
            return 0
        
        # Add this object to seen
        seen.add(obj_id)
        
        # Get base size of object
        size = sys.getsizeof(obj)
        
        # Add size of contents for container objects
        if isinstance(obj, dict):
            size += sum(self._get_size(k, seen) + self._get_size(v, seen) for k, v in obj.items())
        elif hasattr(obj, '__dict__'):
            size += self._get_size(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            try:
                size += sum(self._get_size(item, seen) for item in obj)
            except (TypeError, RuntimeError):
                pass  # Some objects may not be iterable
                
        return size
    
    def run_performance_test(self, max_elements=10000, step=1000, iterations=3):
        """Run comprehensive performance tests comparing both implementations.
        
        Args:
            max_elements (int): Maximum number of elements to test
            step (int): Step size for increasing number of elements
            iterations (int): Number of iterations for each test to average results
        """
        print("Running performance tests...")
        
        for n in range(step, max_elements + 1, step):
            print(f"Testing with {n} elements")
            
            # Test both implementations
            for implementation in ['bplustree', 'bruteforce']:
                # Create and populate database
                if implementation == 'bplustree':
                    db = BPlusTree()
                else:  # bruteforce
                    db = BruteForceDB()
                
                # Insert n elements
                for i in range(n):
                    db.insert(i, f"Value_{i}")
                
                # Measure memory usage
                for _ in range(iterations):
                    self.measure_memory_usage(implementation, n)
                
                # Measure operation times
                for _ in range(iterations):
                    # Insert operation with a new key
                    self.measure_execution_time('insert', implementation, db=db, key=n+1, value=f"Value_{n+1}", n=n)
                    
                    # Search operation (existing key)
                    self.measure_execution_time('search', implementation, db=db, key=n//2, n=n)
                    
                    # Range search operation
                    self.measure_execution_time('range_search', implementation, db=db, 
                                               start_key=n//4, end_key=3*n//4, n=n)
                    
                    # Delete operation
                    self.measure_execution_time('delete', implementation, db=db, key=n//2, n=n)
    
    def plot_results(self):
        """Plot the performance results."""
        fig, axs = plt.subplots(2, 2, figsize=(16, 10))
        
        # Plot insertion time
        axs[0, 0].plot(self.elements, self.bplus_insert_times, 'b-', label='bplustree')
        axs[0, 0].plot(self.elements, self.brute_insert_times, 'r-', label='bruteforce')
        axs[0, 0].set_title('Insertion Performance Comparison')
        axs[0, 0].set_xlabel('Number of Elements')
        axs[0, 0].set_ylabel('Time (s)')
        axs[0, 0].legend()
        axs[0, 0].grid(True)
        
        # Plot search time
        axs[0, 1].plot(self.elements, self.bplus_search_times, 'b-', label='bplustree')
        axs[0, 1].plot(self.elements, self.brute_search_times, 'r-', label='bruteforce')
        axs[0, 1].set_title('Search Performance Comparison')
        axs[0, 1].set_xlabel('Number of Elements')
        axs[0, 1].set_ylabel('Time (s)')
        axs[0, 1].legend()
        axs[0, 1].grid(True)
        
        # Plot range search time - Fix labels here to ensure correct data representation
        axs[1, 0].plot(self.elements, self.bplus_range_times, 'b-', label='bplustree')
        axs[1, 0].plot(self.elements, self.brute_range_times, 'r-', label='bruteforce')
        axs[1, 0].set_title('Range Search Performance Comparison')
        axs[1, 0].set_xlabel('Number of Elements')
        axs[1, 0].set_ylabel('Time (s)')
        axs[1, 0].legend()
        axs[1, 0].grid(True)
        
        # Debug information to verify data
        print("\nRange search timing data for plotting:")
        print(f"B+ Tree range times: {self.bplus_range_times}")
        print(f"Brute Force range times: {self.brute_range_times}")
        print(f"Elements: {self.elements}")
        
        # Create standalone range search plot for better visibility
        plt.figure(figsize=(10, 6))
        plt.plot(self.elements, self.bplus_range_times, 'b-o', label='bplustree')
        plt.plot(self.elements, self.brute_range_times, 'r-o', label='bruteforce')
        plt.title('Range Search Performance Comparison')
        plt.xlabel('Number of Elements')
        plt.ylabel('Time (s)')
        plt.legend()
        plt.grid(True)
        plt.savefig('range_search_comparison.png')
        
        # Plot delete time
        axs[1, 1].plot(self.elements, self.bplus_delete_times, 'b-', label='bplustree')
        axs[1, 1].plot(self.elements, self.brute_delete_times, 'r-', label='bruteforce')
        axs[1, 1].set_title('Delete Performance Comparison')
        axs[1, 1].set_xlabel('Number of Elements')
        axs[1, 1].set_ylabel('Time (s)')
        axs[1, 1].legend()
        axs[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig('performance_comparison.png')
        plt.show()
    
    def print_summary(self):
        """Print a summary of the performance comparison."""
        print("\nPerformance Summary:")
        
        operations = ['insert', 'search', 'range_search', 'delete', 'memory']
        
        for operation in operations:
            print(f"\n{operation.replace('_', ' ').title()}:")
            
            # Calculate the average for each implementation at max data size
            for implementation in ['bplustree', 'bruteforce']:
                sizes = sorted(self.results[implementation][operation].keys())
                
                if not sizes:
                    continue
                
                max_size = sizes[-1]
                avg_time = sum(self.results[implementation][operation][max_size]) / \
                           len(self.results[implementation][operation][max_size])
                
                if operation == 'memory':
                    print(f"  {implementation}: {avg_time:.2f} MB")
                else:
                    print(f"  {implementation}: {avg_time*1000:.2f} ms")
            
            # Determine the winner
            if len(self.results['bplustree'][operation]) > 0 and len(self.results['bruteforce'][operation]) > 0:
                bplus_avg = sum(self.results['bplustree'][operation][max_size]) / \
                           len(self.results['bplustree'][operation][max_size])
                brute_avg = sum(self.results['bruteforce'][operation][max_size]) / \
                           len(self.results['bruteforce'][operation][max_size])
                
                # Avoid division by zero
                if bplus_avg == 0 and brute_avg == 0:
                    print(f"  Both implementations have similar performance")
                elif bplus_avg == 0:
                    print(f"  Winner: B+ Tree (significantly faster)")
                elif brute_avg == 0:
                    print(f"  Winner: Brute Force (significantly faster)")
                elif bplus_avg < brute_avg:
                    winner = 'B+ Tree'
                    improvement = (brute_avg - bplus_avg) / brute_avg * 100
                    print(f"  Winner: {winner} (faster by {improvement:.2f}%)")
                else:
                    winner = 'Brute Force'
                    improvement = (bplus_avg - brute_avg) / bplus_avg * 100
                    print(f"  Winner: {winner} (faster by {improvement:.2f}%)")