#!/usr/bin/env python3
"""
Visualizer for B+ Tree structures
"""

import os
import uuid
import tempfile
from graphviz import Digraph

class BPlusTreeVisualizer:
    """Visualizer for B+ Tree structures using Graphviz."""
    
    def __init__(self, tree):
        """Initialize the visualizer with a B+ Tree.
        
        Args:
            tree: The B+ Tree to visualize
        """
        self.tree = tree
        
    def visualize(self, filename=None, view=True):
        """Create a visualization of the B+ Tree.
        
        Args:
            filename: Optional name for the output file (without extension)
            view: Whether to open the rendered image
            
        Returns:
            str: Path to the output file
        """
        # Create a new directed graph
        dot = Digraph(comment='B+ Tree Visualization', format='png')
        
        # Set graph attributes for better rendering
        dot.attr('graph', rankdir='TB', splines='true', nodesep='0.5', ranksep='0.5')
        
        # Use HTML-like labels instead of record shape to avoid Graphviz errors
        dot.attr('node', shape='plaintext', fontname='Arial')
        
        # Add nodes and edges
        self._visualize_node(dot, self.tree.root)
        
        # Add connections between leaf nodes
        self._connect_leaves(dot)
        
        # Set the filename or use a random name
        if filename is None:
            # Use a temporary file to avoid collisions
            temp_dir = tempfile.gettempdir()
            unique_id = str(uuid.uuid4())[:8]
            filename = os.path.join(temp_dir, f"bplustree_{unique_id}")
        
        # Render the graph (creates a PNG and optionally opens it)
        try:
            output_path = dot.render(filename=filename, view=view, cleanup=True)
            return output_path
        except Exception as e:
            # If rendering fails, try a simpler visualization approach
            return self._create_simple_visualization(filename, view)
        
    def _visualize_node(self, dot, node, node_id=None, rank=None):
        """Add a node to the visualization graph using HTML-like labels.
        
        Args:
            dot: The Graphviz graph
            node: The B+ Tree node to visualize
            node_id: Optional ID for the node (generated if not provided)
            rank: The rank of this node in the tree (for level-based positioning)
            
        Returns:
            str: The ID of the node in the graph
        """
        if node_id is None:
            node_id = f"node_{id(node)}"
            
        # Create HTML-like label
        if node.is_leaf():
            # Format leaf node with keys and values
            label = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            # Table header
            label += '<TR><TD COLSPAN="{}" BGCOLOR="lightblue">LEAF NODE</TD></TR>'.format(max(1, len(node.keys)))
            if node.keys:
                # Keys row
                label += '<TR>'
                for key in node.keys:
                    label += f'<TD>{key}</TD>'
                label += '</TR>'
                # Values row
                label += '<TR>'
                for val in node.values:
                    label += f'<TD>{val}</TD>'
                label += '</TR>'
            else:
                label += '<TR><TD>Empty</TD></TR>'
            label += '</TABLE>>'
            
            # Add the node to the graph
            dot.node(node_id, label=label)
        else:
            # Format internal node with keys
            label = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            if node == self.tree.root:
                label += '<TR><TD COLSPAN="{}" BGCOLOR="gold">ROOT NODE</TD></TR>'.format(max(1, len(node.keys) + 1))
            else:
                label += '<TR><TD COLSPAN="{}" BGCOLOR="lightcoral">INTERNAL NODE</TD></TR>'.format(max(1, len(node.keys) + 1))
                
            if node.keys:
                # For internal nodes, show pointers and keys alternating
                label += '<TR>'
                label += '<TD PORT="p0">&nbsp;</TD>'  # First pointer
                for i, key in enumerate(node.keys):
                    label += f'<TD>{key}</TD>'
                    label += f'<TD PORT="p{i+1}">&nbsp;</TD>'  # Next pointer
                label += '</TR>'
            else:
                label += '<TR><TD>Empty</TD></TR>'
            label += '</TABLE>>'
            
            # Add the node to the graph
            dot.node(node_id, label=label)
            
            # Add edges to children with HTML port references
            if node.children:
                for i, child in enumerate(node.children):
                    child_id = f"node_{id(child)}"
                    self._visualize_node(dot, child, child_id)
                    
                    # Connect from port to child
                    dot.edge(f'{node_id}:p{i}', child_id)
                
        return node_id
    
    def _connect_leaves(self, dot):
        """Add edges between leaf nodes for sequential access.
        
        Args:
            dot: The Graphviz graph
        """
        # Find the leftmost leaf
        node = self.tree.root
        while not node.is_leaf():
            if not node.children:
                break
            node = node.children[0]
            
        # Connect leaf nodes with dashed edges
        while node and node.next_leaf:
            dot.edge(f"node_{id(node)}", f"node_{id(node.next_leaf)}", 
                    style='dashed', color='blue', constraint='false')
            node = node.next_leaf
            
    def _create_simple_visualization(self, filename, view):
        """Create a simpler visualization if the main one fails.
        
        Args:
            filename: Name for the output file
            view: Whether to open the rendered image
            
        Returns:
            str: Path to the output file
        """
        dot = Digraph(comment='Simple B+ Tree', format='png')
        dot.attr('graph', rankdir='LR')  # Left-to-right layout for simplicity
        dot.attr('node', shape='box')  # Simple box nodes
        
        # Use a simpler approach without HTML labels
        self._add_simple_nodes(dot, self.tree.root)
        
        # Render the simple graph
        try:
            return dot.render(filename=filename + "_simple", view=view, cleanup=True)
        except:
            # If all else fails, create a text file with tree info
            text_filename = filename + ".txt"
            with open(text_filename, 'w') as f:
                f.write(f"B+ Tree with order {self.tree.order}\n")
                f.write("Unable to generate graphical visualization")
            return text_filename
            
    def _add_simple_nodes(self, dot, node, prefix=""):
        """Add simple nodes to the graph without HTML labels.
        
        Args:
            dot: The Graphviz graph
            node: The B+ Tree node to visualize
            prefix: Prefix for node labels to show hierarchy
        """
        node_id = f"simple_{id(node)}"
        
        if node.is_leaf():
            label = f"{prefix} Leaf: {' | '.join(str(k) for k in node.keys)}"
            dot.node(node_id, label, style='filled', fillcolor='lightblue')
        else:
            if node == self.tree.root:
                label = f"{prefix} Root: {' | '.join(str(k) for k in node.keys)}"
                dot.node(node_id, label, style='filled', fillcolor='gold')
            else:
                label = f"{prefix} Internal: {' | '.join(str(k) for k in node.keys)}"
                dot.node(node_id, label, style='filled', fillcolor='lightcoral')
                
            # Add children
            for i, child in enumerate(node.children):
                child_id = f"simple_{id(child)}"
                self._add_simple_nodes(dot, child, f"{prefix}.{i}")
                dot.edge(node_id, child_id)