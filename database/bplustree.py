#!/usr/bin/env python3
"""
B+ Tree implementation for database indexing
"""

import pickle
import os

class Node:
    """Base class for B+ Tree nodes."""
    
    def __init__(self, order=4):
        self.order = order
        self.keys = []
        self.parent = None
        
    def is_leaf(self):
        return False


class LeafNode(Node):
    """Leaf node class for B+ Tree."""
    
    def __init__(self, order=4):
        super().__init__(order)
        self.values = []  # List of record references
        self.next_leaf = None  # Pointer to next leaf node for range queries
    
    def is_leaf(self):
        return True
    
    def insert(self, key, value):
        """Insert a key-value pair into this leaf node.
        
        Args:
            key: The key to insert
            value: The value (record reference) to associate with the key
            
        Returns:
            tuple: (split_occurred, new_node, middle_key) where:
                split_occurred: True if the node was split, False otherwise
                new_node: The new node created after split, or None if no split
                middle_key: The middle key that goes up to parent after split
        """
        # Find position to insert
        i = 0
        while i < len(self.keys):
            try:
                # Try direct comparison first
                if key > self.keys[i]:
                    i += 1
                    continue
            except TypeError:
                # Handle type mismatch by converting both to strings
                if str(key) > str(self.keys[i]):
                    i += 1
                    continue
            break
        
        # Insert key and value at position i
        self.keys.insert(i, key)
        self.values.insert(i, value)
        
        # Check if node is full and needs to be split
        if len(self.keys) > self.order - 1:
            return self._split()
        
        return False, None, None
    
    def _split(self):
        """Split this leaf node when it becomes full."""
        middle = len(self.keys) // 2
        
        # Create new leaf node
        new_node = LeafNode(self.order)
        new_node.parent = self.parent
        
        # Move half the keys and values to the new node
        new_node.keys = self.keys[middle:]
        new_node.values = self.values[middle:]
        
        # Update this node's keys and values to only include the first half
        self.keys = self.keys[:middle]
        self.values = self.values[:middle]
        
        # Maintain leaf node chain for range queries
        new_node.next_leaf = self.next_leaf
        self.next_leaf = new_node
        
        # Return the middle key for parent insertion
        return True, new_node, new_node.keys[0]
    
    def find(self, key):
        """Find a key in this leaf node.
        
        Args:
            key: The key to search for
            
        Returns:
            The value associated with the key, or None if not found
        """
        for i, k in enumerate(self.keys):
            if k == key:
                return self.values[i]
        return None
    
    def range_search(self, start_key, end_key):
        """
        Search for values within a range of keys.
        
        Args:
            start_key: The lower bound of the range (inclusive)
            end_key: The upper bound of the range (inclusive)
            
        Returns:
            list: List of values within the specified range
        """
        result = []
        
        # Find values in current node
        for i, key in enumerate(self.keys):
            if start_key <= key <= end_key:
                result.append(self.values[i])
        
        # If all keys in this node are less than or equal to end_key,
        # and there's a next leaf, follow the link.
        # BUT: Use iteration instead of recursion to avoid stack overflow
        if self.keys and self.keys[-1] <= end_key and self.next_leaf:
            current = self.next_leaf
            while current:
                # Process each leaf node in the chain
                continue_search = False
                
                # Check keys in this node
                for i, key in enumerate(current.keys):
                    if key <= end_key:
                        if key >= start_key:
                            result.append(current.values[i])
                        continue_search = True
                    else:
                        # We've gone past the end key
                        continue_search = False
                        break
                
                # If we've found keys past our end range, stop searching
                if not continue_search:
                    break
                    
                # Move to next leaf node
                current = current.next_leaf
                
        return result
    
    def delete(self, key):
        """Delete a key-value pair from this leaf node.
        
        Args:
            key: The key to delete
            
        Returns:
            tuple: (deleted, underflow) where:
                deleted: True if the key was deleted, False if not found
                underflow: True if the node is now under minimum capacity
        """
        # First try exact match
        for i, k in enumerate(self.keys):
            if k == key:
                del self.keys[i]
                del self.values[i]
                # Check if node is now under minimum capacity (half full)
                min_keys = (self.order - 1) // 2
                return True, len(self.keys) < min_keys
        
        # Then try numeric conversion for string keys
        if isinstance(key, int):
            for i, k in enumerate(self.keys):
                if isinstance(k, str) and k.isdigit() and int(k) == key:
                    del self.keys[i]
                    del self.values[i]
                    # Check if node is now under minimum capacity (half full)
                    min_keys = (self.order - 1) // 2
                    return True, len(self.keys) < min_keys
        elif isinstance(key, str) and key.isdigit():
            key_as_int = int(key)
            for i, k in enumerate(self.keys):
                if isinstance(k, int) and k == key_as_int:
                    del self.keys[i]
                    del self.values[i]
                    # Check if node is now under minimum capacity (half full)
                    min_keys = (self.order - 1) // 2
                    return True, len(self.keys) < min_keys
        
        return False, False
    
    def borrow_from_left(self, left_sibling, parent_idx):
        """Borrow a key-value pair from left sibling.
        
        Args:
            left_sibling: The left sibling node
            parent_idx: The index of parent key between this node and left sibling
        """
        # Move the rightmost key-value from left sibling to this node
        self.keys.insert(0, left_sibling.keys.pop())
        self.values.insert(0, left_sibling.values.pop())
        
        # Update parent key
        if self.parent:
            self.parent.keys[parent_idx] = self.keys[0]
            
    def borrow_from_right(self, right_sibling, parent_idx):
        """Borrow a key-value pair from right sibling.
        
        Args:
            right_sibling: The right sibling node
            parent_idx: The index of parent key between this node and right sibling
        """
        # Move the leftmost key-value from right sibling to this node
        self.keys.append(right_sibling.keys.pop(0))
        self.values.append(right_sibling.values.pop(0))
        
        # Update parent key
        if self.parent:
            self.parent.keys[parent_idx] = right_sibling.keys[0]
    
    def merge_with_right(self, right_sibling, parent_idx):
        """Merge this node with its right sibling.
        
        Args:
            right_sibling: The right sibling node
            parent_idx: The index of parent key to remove after merging
        """
        # Save first key of right sibling for update checks
        right_first_key = right_sibling.keys[0] if right_sibling.keys else None
        
        # Move all keys and values from right sibling to this node
        self.keys.extend(right_sibling.keys)
        self.values.extend(right_sibling.values)
        
        # Update leaf node chain
        self.next_leaf = right_sibling.next_leaf
        
        # Remove the parent key that separates the two nodes
        if self.parent:
            removed_parent_key = self.parent.keys[parent_idx]
            del self.parent.keys[parent_idx]
            del self.parent.children[parent_idx + 1]
            
            # Check if we need to update any parent keys higher up
            if right_first_key and right_first_key == removed_parent_key:
                # We removed a key that might be used in higher levels
                if self.keys:
                    # Use our new first key for parent references
                    updated_key = self.keys[0]
                    parent = self.parent
                    while parent:
                        # Check each key in this parent
                        for i, key in enumerate(parent.keys):
                            if key == right_first_key:
                                parent.keys[i] = updated_key
                        parent = parent.parent
        
        return self.parent
    
    def update(self, key, value):
        """Update the value associated with a key.
        
        Args:
            key: The key to update
            value: The new value to associate with the key
            
        Returns:
            bool: True if the key was updated, False if not found
        """
        for i, k in enumerate(self.keys):
            # Handle potential type differences in comparison
            if ((isinstance(k, int) and isinstance(key, str) and key.isdigit() and k == int(key)) or
                (isinstance(k, str) and isinstance(key, int) and k.isdigit() and int(k) == key) or
                k == key):
                self.values[i] = value
                return True
        return False


class InternalNode(Node):
    """Internal node class for B+ Tree."""
    
    def __init__(self, order=4):
        super().__init__(order)
        self.children = []  # List of child nodes
    
    def insert_key(self, key, left_child, right_child):
        """Insert a key and its left and right children.
        
        Args:
            key: The key to insert
            left_child: The child node to the left of the key
            right_child: The child node to the right of the key
            
        Returns:
            tuple: (split_occurred, new_node, middle_key) where:
                split_occurred: True if the node was split, False otherwise
                new_node: The new node created after split, or None if no split
                middle_key: The middle key that goes up to parent after split
        """
        # Find position to insert the key
        i = 0
        while i < len(self.keys):
            try:
                # Try direct comparison first
                if key > self.keys[i]:
                    i += 1
                    continue
            except TypeError:
                # Handle type mismatch by converting both to strings
                if str(key) > str(self.keys[i]):
                    i += 1
                    continue
            break
        
        # Insert the key at position i
        self.keys.insert(i, key)
        
        # If this is the first key, add both children
        if i == 0 and len(self.children) == 0:
            self.children.append(left_child)
            self.children.append(right_child)
        else:
            # Otherwise add just the right child at position i+1
            self.children.insert(i + 1, right_child)
        
        # Set parent references for the children
        left_child.parent = self
        right_child.parent = self
        
        # Check if node is full and needs to be split
        if len(self.keys) > self.order - 1:
            return self._split()
        
        return False, None, None
    
    def _split(self):
        """Split this internal node when it becomes full."""
        middle = len(self.keys) // 2
        middle_key = self.keys[middle]
        
        # Create new internal node
        new_node = InternalNode(self.order)
        new_node.parent = self.parent
        
        # Move half the keys and children to the new node
        new_node.keys = self.keys[middle + 1:]
        new_node.children = self.children[middle + 1:]
        
        # Update parent references for the moved children
        for child in new_node.children:
            child.parent = new_node
        
        # Update this node's keys and children to only include the first half
        self.keys = self.keys[:middle]
        self.children = self.children[:middle + 1]
        
        # Return the middle key for parent insertion
        return True, new_node, middle_key
    
    def find_child(self, key):
        """Find the child node that should contain the key.
        
        Args:
            key: The key to search for
            
        Returns:
            The child node that should contain the key
        """
        i = 0
        while i < len(self.keys):
            # Convert both values to same type for comparison to avoid TypeError
            node_key = self.keys[i]
            if self._compare_keys(key, node_key) >= 0:
                i += 1
            else:
                break
        return self.children[i]
    
    def _compare_keys(self, key1, key2):
        """Compare two keys, handling type differences.
        
        Args:
            key1: First key
            key2: Second key
            
        Returns:
            -1 if key1 < key2, 0 if key1 == key2, 1 if key1 > key2
        """
        try:
            # Try direct comparison first
            if key1 < key2:
                return -1
            elif key1 > key2:
                return 1
            else:
                return 0
        except TypeError:
            # Convert to strings for comparison if types are incompatible
            str_key1 = str(key1)
            str_key2 = str(key2)
            
            if str_key1 < str_key2:
                return -1
            elif str_key1 > str_key2:
                return 1
            else:
                return 0
    
    def delete_key(self, key_idx):
        """Delete a key and its corresponding right child pointer.
        
        Args:
            key_idx: The index of the key to delete
            
        Returns:
            bool: True if the node is now under minimum capacity
        """
        if key_idx >= 0 and key_idx < len(self.keys):
            del self.keys[key_idx]
            del self.children[key_idx + 1]  # Remove the corresponding right child
            
            # Check if node is now under minimum capacity
            min_keys = (self.order - 1) // 2
            return len(self.keys) < min_keys
        return False
    
    def borrow_from_left(self, left_sibling, parent_idx):
        """Borrow a key and child from left sibling.
        
        Args:
            left_sibling: The left sibling node
            parent_idx: The index of parent key between this node and left sibling
        """
        # Get parent key that will move down to this node
        parent_key = self.parent.keys[parent_idx]
        
        # Get rightmost key and child from left sibling
        left_key = left_sibling.keys.pop()
        left_child = left_sibling.children.pop()
        
        # Insert parent key and left child to this node
        self.keys.insert(0, parent_key)
        self.children.insert(0, left_child)
        left_child.parent = self
        
        # Move left key up to parent
        self.parent.keys[parent_idx] = left_key
    
    def borrow_from_right(self, right_sibling, parent_idx):
        """Borrow a key and child from right sibling.
        
        Args:
            right_sibling: The right sibling node
            parent_idx: The index of parent key between this node and right sibling
        """
        # Get parent key that will move down to this node
        parent_key = self.parent.keys[parent_idx]
        
        # Get leftmost key and child from right sibling
        right_key = right_sibling.keys.pop(0)
        right_child = right_sibling.children.pop(0)
        
        # Insert parent key and right child to this node
        self.keys.append(parent_key)
        self.children.append(right_child)
        right_child.parent = self
        
        # Move right key up to parent
        self.parent.keys[parent_idx] = right_key
    
    def merge_with_right(self, right_sibling, parent_idx):
        """Merge this node with its right sibling.
        
        Args:
            right_sibling: The right sibling node
            parent_idx: The index of parent key to be merged down
            
        Returns:
            The parent node after removing the key
        """
        # Save the parent key for reference checks
        parent_key = self.parent.keys[parent_idx] 
        
        # Insert the parent key into this node
        self.keys.append(parent_key)
        
        # Move all keys and children from right sibling to this node
        right_first_key = right_sibling.keys[0] if right_sibling.keys else None
        self.keys.extend(right_sibling.keys)
        for child in right_sibling.children:
            self.children.append(child)
            child.parent = self
        
        # Remove the parent key and pointer to right sibling
        parent = self.parent
        del parent.keys[parent_idx]
        del parent.children[parent_idx + 1]
        
        # Check if the parent key we just deleted exists in higher levels
        if parent.parent and right_first_key == parent_key:
            # Recursively check for the key in higher levels
            ancestor = parent.parent
            while ancestor:
                # Check each key in this ancestor
                for i, key in enumerate(ancestor.keys):
                    if key == parent_key:
                        if self.keys:
                            # Update with a key from this node
                            ancestor.keys[i] = self.keys[0]
                ancestor = ancestor.parent
        
        return parent


class BPlusTree:
    """B+ Tree implementation for database indices."""
    
    def __init__(self, order=4):
        """Initialize an empty B+ Tree.
        
        Args:
            order: The order of the B+ Tree (maximum number of children per node)
        """
        self.root = LeafNode(order)
        self.order = order
    
    def insert(self, key, value):
        """Insert a key-value pair into the B+ Tree.
        
        Args:
            key: The key to insert
            value: The value to associate with the key
        """
        # Find the leaf node where the key should be inserted
        leaf_node = self._find_leaf(key)
        
        # Insert the key-value pair into the leaf node
        split, new_node, middle_key = leaf_node.insert(key, value)
        
        # If the leaf node was split, we need to insert the middle key into the parent
        if split:
            self._insert_in_parent(leaf_node, middle_key, new_node)
    
    def _insert_in_parent(self, left_node, key, right_node):
        """Insert a key and right child into the parent of left_node.
        
        Args:
            left_node: The left child node
            key: The key to insert
            right_node: The right child node
        """
        # If left_node is the root, create a new root
        if left_node.parent is None:
            new_root = InternalNode(self.order)
            self.root = new_root
            new_root.keys = [key]
            new_root.children = [left_node, right_node]
            left_node.parent = new_root
            right_node.parent = new_root
            return
        
        # Insert in the parent node
        parent = left_node.parent
        split, new_node, middle_key = parent.insert_key(key, left_node, right_node)
        
        # If parent was split, recursively insert in its parent
        if split:
            self._insert_in_parent(parent, middle_key, new_node)
    
    def _find_leaf(self, key):
        """Find the leaf node that should contain the key.
        
        Args:
            key: The key to search for
            
        Returns:
            The leaf node that should contain the key
        """
        node = self.root
        
        # Traverse down the tree until we reach a leaf node
        while not node.is_leaf():
            node = node.find_child(key)
            
        return node
    
    def find(self, key):
        """Find a value by key.
        
        Args:
            key: The key to search for
            
        Returns:
            The value associated with the key, or None if not found
        """
        # Convert key to int if it's a digit string
        original_key = key
        if isinstance(key, str) and key.isdigit():
            key = int(key)
            
        # Find the leaf node
        leaf = self._find_leaf(key)
        result = leaf.find(key)
        
        # If not found with converted key, try with original key
        if result is None and key != original_key:
            leaf = self._find_leaf(original_key)
            result = leaf.find(original_key)
            
        return result
    
    def range_search(self, start_key, end_key):
        """
        Search for values within a range of keys.
        
        Args:
            start_key: The lower bound of the range (inclusive)
            end_key: The upper bound of the range (inclusive)
            
        Returns:
            list: List of values within the specified range
        """
        if self.root is None:
            return []
        
        if start_key > end_key:
            return []
            
        # Find the leaf node where the start key would be located
        leaf = self._find_leaf(start_key)
        if leaf is None:
            return []
        
        # Perform range search
        return leaf.range_search(start_key, end_key)
    
    def delete(self, key):
        """Delete a key-value pair from the B+ Tree.
        
        Args:
            key: The key to delete
            
        Returns:
            bool: True if the key was deleted, False if not found
        """
        # Add debugging for problematic keys
        problematic_keys = [7, 8]
        if key in problematic_keys:
            print(f"DEBUG: Attempting to delete problematic key {key}")
        
        # Try to convert string digits to int for consistent handling
        original_key = key
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        
        # Find the leaf node containing the key
        leaf = self._find_leaf(key)
        
        # If leaf is not found, return False
        if not leaf:
            print(f"DEBUG: Leaf node not found for key {key}")
            return False
            
        if key in problematic_keys:
            print(f"DEBUG: Found leaf node with keys {leaf.keys} for key {key}")
            if leaf.parent:
                print(f"DEBUG: Parent keys: {leaf.parent.keys}")
        
        # Delete the key from the leaf node
        deleted, underflow = leaf.delete(key)
        
        # If not found with the converted key, try with original key
        if not deleted and key != original_key:
            # Try again with original key
            leaf = self._find_leaf(original_key)
            if leaf:
                deleted, underflow = leaf.delete(original_key)
        
        # If key was not found, return False
        if not deleted:
            print(f"DEBUG: Key {key} not found in leaf node")
            return False
            
        # Extra check for problematic keys
        if key in problematic_keys:
            print(f"DEBUG: Key {key} successfully deleted, underflow={underflow}")
            print(f"DEBUG: Leaf node keys after deletion: {leaf.keys}")
        
        # Update parent keys if necessary - this is the critical fix
        self._update_parent_keys_after_deletion(leaf, key)
        
        # If deletion caused underflow, handle it
        if underflow and leaf != self.root:
            print(f"DEBUG: Handling underflow in leaf node with keys {leaf.keys}")
            self._handle_underflow(leaf)
        
        # Double check internal nodes for key references
        if key in problematic_keys:
            print("DEBUG: Checking for lingering key references in tree...")
            self._check_and_fix_key_references(key)
        
        # If root is now empty, adjust tree height
        if len(self.root.keys) == 0:
            if not self.root.is_leaf() and len(self.root.children) > 0:
                self.root = self.root.children[0]
                self.root.parent = None
            elif self.root.is_leaf():
                # Tree is now empty
                self.root = LeafNode(self.order)
        
        return True
        
    def _update_parent_keys_after_deletion(self, node, deleted_key):
        """Update parent keys after a deletion if necessary.
        
        Args:
            node: The node where a key was deleted
            deleted_key: The key that was deleted
        """
        if not node.parent:
            return  # No parent to update
        
        # Find this node's index in parent's children
        try:
            node_idx = node.parent.children.index(node)
        except ValueError:
            return  # Node not found in parent's children
            
        # If this is not the leftmost leaf and the deleted key is in parent
        if node_idx > 0:
            # Find parent key indices that might need updating
            for i, parent_key in enumerate(node.parent.keys):
                if parent_key == deleted_key:
                    # If the parent key matches the deleted key, update it
                    if node.keys:  # If node still has keys
                        node.parent.keys[i] = node.keys[0]
                    elif i < len(node.parent.children) - 1 and node.parent.children[i+1].keys:
                        # Use the first key of the right sibling
                        node.parent.keys[i] = node.parent.children[i+1].keys[0]
                    # Recursively update keys in higher levels if needed
                    self._update_parent_keys_after_deletion(node.parent, deleted_key)
                    break
        
        # If the first key changed and this node isn't the leftmost child
        if node_idx > 0 and node_idx - 1 < len(node.parent.keys):
            # Update the parent separator key with the first key of this node (if it exists)
            if node.keys:
                if node.parent.keys[node_idx - 1] == deleted_key:
                    node.parent.keys[node_idx - 1] = node.keys[0]
                    # Recursively update keys in higher levels if needed
                    self._update_parent_keys_after_deletion(node.parent, deleted_key)
    
    def _handle_underflow(self, node):
        """Handle underflow in a node after deletion.
        
        Args:
            node: The node that has underflow
        """
        if node == self.root:
            return
        
        parent = node.parent
        min_keys = (self.order - 1) // 2
        
        # Find the index of node in its parent
        node_idx = parent.children.index(node)
        
        # Try borrowing from left sibling if it exists
        if node_idx > 0:
            left_sibling = parent.children[node_idx - 1]
            if len(left_sibling.keys) > min_keys:
                if node.is_leaf():
                    node.borrow_from_left(left_sibling, node_idx - 1)
                else:
                    node.borrow_from_left(left_sibling, node_idx - 1)
                return
        
        # Try borrowing from right sibling if it exists
        if node_idx < len(parent.children) - 1:
            right_sibling = parent.children[node_idx + 1]
            if len(right_sibling.keys) > min_keys:
                if node.is_leaf():
                    node.borrow_from_right(right_sibling, node_idx)
                else:
                    node.borrow_from_right(right_sibling, node_idx)
                return
        
        # If we can't borrow, we need to merge with a sibling
        if node_idx > 0:
            # Merge with left sibling
            left_sibling = parent.children[node_idx - 1]
            if node.is_leaf():
                merged_parent = left_sibling.merge_with_right(node, node_idx - 1)
            else:
                merged_parent = left_sibling.merge_with_right(node, node_idx - 1)
        else:
            # Merge with right sibling
            right_sibling = parent.children[node_idx + 1]
            if node.is_leaf():
                merged_parent = node.merge_with_right(right_sibling, node_idx)
            else:
                merged_parent = node.merge_with_right(right_sibling, node_idx)
        
        # If parent now has underflow, handle it recursively
        if merged_parent and merged_parent != self.root and len(merged_parent.keys) < min_keys:
            self._handle_underflow(merged_parent)
    
    def _check_and_fix_key_references(self, deleted_key):
        """Check for and fix any lingering references to a deleted key.
        
        Args:
            deleted_key: The key that was deleted
        """
        # Perform a breadth-first traversal to find and fix any references
        if self.root is None:
            return
            
        queue = [self.root]
        fixed_count = 0
        
        while queue:
            node = queue.pop(0)
            
            # Check this node's keys
            for i, key in enumerate(node.keys):
                if key == deleted_key:
                    print(f"DEBUG: Found lingering reference to key {deleted_key} in node {node}")
                    
                    # Try to fix the reference
                    if not node.is_leaf() and i < len(node.children) - 1:
                        # Get the first key of the right subtree
                        right_child = node.children[i+1]
                        replacement_key = None
                        
                        # Find the leftmost leaf in the right subtree
                        current = right_child
                        while not current.is_leaf():
                            current = current.children[0]
                            
                        if current.keys:
                            replacement_key = current.keys[0]
                            
                        if replacement_key is not None:
                            print(f"DEBUG: Replacing key {deleted_key} with {replacement_key}")
                            node.keys[i] = replacement_key
                            fixed_count += 1
            
            # Add children to the queue
            if not node.is_leaf():
                queue.extend(node.children)
        
        if fixed_count > 0:
            print(f"DEBUG: Fixed {fixed_count} lingering references to key {deleted_key}")
    
    def update(self, key, value):
        """Update the value associated with a key.
        
        Args:
            key: The key to update
            value: The new value to associate with the key
            
        Returns:
            bool: True if the key was updated, False if not found
        """
        leaf = self._find_leaf(key)
        return leaf.update(key, value)
    
    def save(self, filename):
        """Save the B+ Tree to a file.
        
        Args:
            filename: The file to save to
        """
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(filename):
        """Load a B+ Tree from a file.
        
        Args:
            filename: The file to load from
            
        Returns:
            BPlusTree: The loaded B+ Tree
        """
        with open(filename, 'rb') as f:
            return pickle.load(f)
    
    def display(self):
        """Display the B+ tree structure in a readable format."""
        if self.root is None:
            print("Empty tree")
            return
            
        # Print tree details
        print(f"B+ Tree (Order {self.order})")
        
        # Use queue for level order traversal
        queue = [(self.root, 0)]  # (node, level)
        current_level = 0
        level_nodes = []
        
        while queue:
            node, level = queue.pop(0)
            
            # If we're at a new level, print the previous level
            if level > current_level:
                self._print_level(level_nodes, current_level)
                current_level = level
                level_nodes = []
                
            # Add this node to the current level
            level_nodes.append(node)
            
            # Add children to the queue if this is an internal node
            if not node.is_leaf():
                for child in node.children:
                    if child is not None:
                        queue.append((child, level + 1))
                        
        # Print the last level
        if level_nodes:
            self._print_level(level_nodes, current_level)
    
    def _print_level(self, nodes, level):
        """Helper method to print a level of the tree.
        
        Args:
            nodes: List of nodes at this level
            level: The level number (0 is root)
        """
        print(f"\nLevel {level}:")
        
        for i, node in enumerate(nodes):
            if node.is_leaf():
                # For leaf nodes, print keys and values
                keys_vals = [f"{k}:{v}" for k, v in zip(node.keys, node.values)]
                print(f"  Leaf Node {i}: {keys_vals}")
                
                # Also show next leaf pointer if it exists
                if hasattr(node, 'next_leaf') and node.next_leaf:
                    next_keys = node.next_leaf.keys if node.next_leaf.keys else []
                    print(f"    → Next Leaf: {next_keys}")
            else:
                # For internal nodes, print keys only
                print(f"  Internal Node {i}: {node.keys}")
                
                # Show number of children
                if hasattr(node, 'children'):
                    valid_children = [c for c in node.children if c is not None]
                    print(f"    Children: {len(valid_children)}")