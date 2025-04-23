#!/usr/bin/env python3
"""
Flask web application for B+ Tree Database Management System
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import io
import base64
from database.bplustree import BPlusTree
from database.table import Table
from database.db_manager import DatabaseManager
from database.tree_visualizer import BPlusTreeVisualizer
from mysql_adapter import MySQLAdapter, process_blob_field
import tempfile

app = Flask(__name__)
app.secret_key = 'b+tree-db-management-system'

# Initialize the database manager with a persistent storage location
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DB_DIR, exist_ok=True)
db_manager = DatabaseManager(DB_DIR)

# MySQL connection configuration
mysql_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Harshith@2005',
    'port': 3306,
    'database': 'Dispensary'
}

# Initialize MySQL adapter
mysql_adapter = MySQLAdapter(mysql_config)

# Store visualizations temporarily
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def get_image_mimetype(binary_data):
    if binary_data[:2] == b'\xff\xd8':
        return 'image/jpeg'
    elif binary_data[:8].startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    elif binary_data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    return 'image/jpeg'  # Default to JPEG for medical images

# Make db_manager available to all templates
@app.context_processor
def inject_db_manager():
    return {'db_manager': db_manager}

@app.route('/')
def index():
    """Render the main dashboard page."""
    tables = db_manager.get_tables()
    return render_template('index.html', tables=tables)

@app.route('/import_mysql')
def import_mysql():
    """Render page to import tables from MySQL."""
    mysql_tables = mysql_adapter.get_tables()
    imported_tables = db_manager.get_tables()
    return render_template('import_mysql.html', 
                           mysql_tables=mysql_tables, 
                           imported_tables=imported_tables)

@app.route('/import_table', methods=['POST'])
def import_table():
    """Import a table from MySQL to B+ Tree database."""
    table_name = request.form.get('table_name')
    if not table_name:
        flash('Please select a table to import', 'error')
        return redirect(url_for('import_mysql'))
    
    try:
        # Import the table from MySQL
        success, message = mysql_adapter.import_table_to_bplustree(table_name, db_manager)
        if success:
            flash(f'Successfully imported table {table_name}', 'success')
        else:
            flash(f'Error importing table: {message}', 'error')
    except Exception as e:
        flash(f'Error importing table: {str(e)}', 'error')
    
    return redirect(url_for('import_mysql'))

@app.route('/table/<table_name>')
def view_table(table_name):
    """View the contents of a table."""
    try:
        # Get table information
        table_info = db_manager.get_table_info(table_name)
        columns = table_info['columns']
        primary_key = table_info['primary_key']
        indices = table_info['indices']
        
        # Get records
        records = db_manager.select(table_name)
        
        # Process records for display
        display_records = []
        
        for i, record in enumerate(records):
            display_record = list(record)  # Make a copy for display
            
            for j, value in enumerate(record):
                # Check for binary data (bytes or bytearray)
                if isinstance(value, (bytes, bytearray)) and len(value) > 100:
                    display_record[j] = "BLOB DATA"
                # Check for string that appears to be binary data
                elif isinstance(value, str) and value.startswith('bytearray(b'):
                    display_record[j] = "BLOB DATA" 
            
            display_records.append(display_record)
        
        return render_template('view_table.html', 
                              table_name=table_name, 
                              columns=columns,
                              primary_key=primary_key,
                              indices=indices,
                              records=display_records)
    except Exception as e:
        import traceback
        print(f"Error viewing table: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error viewing table: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/table/<table_name>/view_blob/<int:row>/<column>')
def view_blob(table_name, row, column):
    """View a blob field from a record."""
    try:
        print(f"\n===== DEBUG: view_blob called for {table_name}, row {row}, column {column} =====")
        # Get table information
        table_info = db_manager.get_table_info(table_name)
        columns = table_info['columns']
        primary_key = table_info['primary_key']
        pk_index = columns.index(primary_key)
        
        print(f"Table info: columns={columns}, primary_key={primary_key}, pk_index={pk_index}")
        
        # Get the record's primary key value
        records = db_manager.select(table_name)
        print(f"Found {len(records)} records in table {table_name}")
        
        if row >= len(records):
            print(f"ERROR: Record index {row} out of range (max: {len(records)-1})")
            return "Record not found", 404
        
        record = records[row]
        pk_value = record[pk_index]
        column_index = columns.index(column)
        
        print(f"Accessing record {row} with {primary_key}={pk_value}, column={column}, index={column_index}")
        
        # Get the blob data from B+ Tree storage
        blob_data = record[column_index]
        print(f"Retrieved blob data type: {type(blob_data)}, length: {len(blob_data) if blob_data and hasattr(blob_data, '__len__') else 'N/A'}")
        
        if blob_data is None:
            print("ERROR: Image data is None")
            return "Image not found in database", 404
        
        # Convert to bytes if needed
        if isinstance(blob_data, bytearray):
            print("Converting bytearray to bytes")
            blob_data = bytes(blob_data)
        elif isinstance(blob_data, str):
            print(f"String data detected: {blob_data[:50]}...")
            if blob_data.startswith('bytearray('):
                # If it's stored as a string representation, convert it
                import ast
                try:
                    print("Attempting to convert string representation to bytes")
                    blob_data = bytes(ast.literal_eval(blob_data))
                    print(f"Conversion successful. New length: {len(blob_data)}")
                except Exception as e:
                    print(f"ERROR: Failed to convert string to bytes: {str(e)}")
                    return f"Invalid image data format: {str(e)}", 500
            else:
                print("ERROR: String data doesn't appear to be a bytearray representation")
                return "Invalid image data format", 500
                
        # Determine content type
        content_type = get_image_mimetype(blob_data)
        print(f"Determined content type: {content_type}")
        
        # Generate a unique query ID to prevent any caching
        import random, time
        query_id = f"{random.randint(1000, 9999)}_{int(time.time())}"
        
        # Save a copy of the image for debugging if needed
        debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        os.makedirs(debug_path, exist_ok=True)
        with open(os.path.join(debug_path, f"debug_image_{table_name}_{row}_{column}_{query_id}.jpg"), "wb") as f:
            f.write(blob_data)
        print(f"Debug image saved to debug_image_{table_name}_{row}_{column}_{query_id}.jpg")
        
        # Serve the image with strong anti-caching headers
        print("Serving image with send_file")
        response = send_file(
            io.BytesIO(blob_data),
            mimetype=content_type,
            as_attachment=False
        )
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Query-ID'] = query_id
        
        print("===== DEBUG: view_blob completed successfully =====\n")
        return response
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"ERROR viewing blob: {str(e)}")
        print(traceback_str)
        return f"Error viewing blob: {str(e)}<br><pre>{traceback_str}</pre>", 500

@app.route('/table/<table_name>/image/<int:row>/<column>')
def view_image(table_name, row, column):
    """View an image with a nicer interface and navigation between images."""
    try:
        # Get table information
        table_info = db_manager.get_table_info(table_name)
        columns = table_info['columns']
        primary_key = table_info['primary_key']
        pk_index = columns.index(primary_key)
        
        # Get the records
        records = db_manager.select(table_name)
        if row >= len(records):
            flash("Record not found", "error")
            return redirect(url_for('view_table', table_name=table_name))
        
        # Get the current record and primary key value
        record = records[row]
        pk_value = record[pk_index]
        
        # Prepare record data for display
        record_data = {}
        for i, col in enumerate(columns):
            value = record[i]
            if isinstance(value, (bytes, bytearray)) and len(value) > 100:
                record_data[col] = "BLOB DATA"
            elif isinstance(value, str) and value.startswith('bytearray('):
                record_data[col] = "BLOB DATA"
            else:
                record_data[col] = value
        
        # Find the record title - use first string column or primary key
        name_columns = ['name', 'title', 'firstname', 'lastname', 'fullname', 'doctorname', 'doctor_name']
        record_title = f"Record #{row+1}"
        
        for name_col in name_columns:
            if name_col in columns:
                col_idx = columns.index(name_col)
                if record[col_idx] and isinstance(record[col_idx], str):
                    record_title = record[col_idx]
                    break
        
        # If we didn't find a good title column, use the primary key
        if record_title == f"Record #{row+1}":
            record_title += f" - {primary_key}: {pk_value}"
        
        # Set up navigation (previous/next)
        prev_row = row - 1 if row > 0 else None
        next_row = row + 1 if row < len(records) - 1 else None
        
        # Find all images in the table for this column
        image_count = 0
        titles = []
        
        for i, rec in enumerate(records):
            col_idx = columns.index(column)
            if col_idx >= 0 and col_idx < len(rec):
                val = rec[col_idx]
                if isinstance(val, (bytes, bytearray)) or (isinstance(val, str) and val.startswith('bytearray(')):
                    image_count += 1
                    
                    # Generate title for this image
                    img_title = f"Record #{i+1}"
                    for name_col in name_columns:
                        if name_col in columns:
                            name_idx = columns.index(name_col)
                            if rec[name_idx] and isinstance(rec[name_idx], str):
                                img_title = rec[name_idx]
                                break
                    titles.append(img_title)
        
        return render_template('view_image.html',
                              table_name=table_name,
                              column=column,
                              row=row,
                              record_title=record_title,
                              record_data=record_data,
                              pk_value=pk_value,
                              prev_row=prev_row,
                              next_row=next_row,
                              image_count=image_count,
                              titles=titles)
    except Exception as e:
        import traceback
        print(f"Error viewing image: {str(e)}")
        print(traceback.format_exc())
        flash(f"Error viewing image: {str(e)}", "error")
        return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/search', methods=['POST'])
def search_table(table_name):
    """Search for records in a table."""
    try:
        column = request.form.get('column')
        value = request.form.get('value')
        search_type = request.form.get('search_type', 'exact')
        
        print(f"Searching {table_name} where {column} {'=' if search_type == 'exact' else 'between'} {value}")
        
        if search_type == 'exact':
            records = db_manager.select(table_name, condition_col=column, condition_val=value)
        elif search_type == 'range':
            range_end = request.form.get('range_end', '')
            if not range_end:
                flash('Range end value is required for range search', 'error')
                return redirect(url_for('view_table', table_name=table_name))
            records = db_manager.select(table_name, condition_col=column, 
                                       range_start=value, range_end=range_end)
        
        # Get table information
        table_info = db_manager.get_table_info(table_name)
        columns = table_info['columns']
        primary_key = table_info['primary_key']
        indices = table_info['indices']
        
        # Process records for display - handle BLOB fields properly
        display_records = []
        for i, record in enumerate(records):
            display_record = list(record)  # Make a copy for display
            
            for j, value in enumerate(display_record):
                # Check for binary data (bytes or bytearray)
                if isinstance(value, (bytes, bytearray)) and len(value) > 100:
                    display_record[j] = "BLOB DATA"
                # Check for string that appears to be binary data
                elif isinstance(value, str) and value.startswith('bytearray('):
                    display_record[j] = "BLOB DATA"
            
            display_records.append(display_record)
        
        return render_template('view_table.html', 
                              table_name=table_name, 
                              columns=columns,
                              primary_key=primary_key,
                              indices=indices,
                              records=display_records,
                              search_performed=True,
                              search_column=column,
                              search_value=value,
                              search_type=search_type,
                              range_end=request.form.get('range_end', ''))
    except Exception as e:
        import traceback
        print(f"Error searching table: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error searching table: {str(e)}', 'error')
        return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/create_index', methods=['POST'])
def create_index(table_name):
    """Create a new index on a table."""
    try:
        column = request.form.get('column')
        if not column:
            flash('Please select a column to index', 'error')
            return redirect(url_for('view_table', table_name=table_name))
        
        # Create the index
        db_manager.create_index(table_name, column)
        flash(f'Successfully created index on {column}', 'success')
    except Exception as e:
        flash(f'Error creating index: {str(e)}', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/insert', methods=['GET', 'POST'])
def insert_record(table_name):
    """Insert a new record into a table."""
    # Get table information
    table_info = db_manager.get_table_info(table_name)
    columns = table_info['columns']
    
    if request.method == 'POST':
        try:
            # Get values for each column
            record = []
            for i, column in enumerate(columns):
                # Check if this is a file upload field
                if f'file_{column}' in request.files and request.files[f'file_{column}'].filename:
                    # Handle file upload for image fields
                    uploaded_file = request.files[f'file_{column}']
                    if uploaded_file:
                        # Read the file data as bytes
                        file_data = uploaded_file.read()
                        print(f"Uploaded image for {column}, size: {len(file_data)} bytes")
                        record.append(file_data)
                else:
                    # Regular form field
                    value = request.form.get(column, '')
                    
                    # Try to convert numeric values to proper types
                    if i == 0:  # Assuming first column is primary key and should be numeric
                        try:
                            if value.isdigit():
                                value = int(value)
                            elif value.replace('.', '').isdigit() and value.count('.') <= 1:
                                value = float(value)
                        except (ValueError, AttributeError):
                            pass  # Keep as string if conversion fails
                    
                    record.append(value)
            
            # Insert the record
            db_manager.insert(table_name, record)
            flash('Record inserted successfully', 'success')
            return redirect(url_for('view_table', table_name=table_name))
        except Exception as e:
            import traceback
            print(f"Error inserting record: {str(e)}")
            print(traceback.format_exc())
            flash(f'Error inserting record: {str(e)}', 'error')
    
    return render_template('insert_record.html',
                          table_name=table_name,
                          columns=columns)

@app.route('/table/<table_name>/update/<primary_key_value>', methods=['GET', 'POST'])
def update_record(table_name, primary_key_value):
    """Update a record in a table."""
    # Get table information
    table_info = db_manager.get_table_info(table_name)
    columns = table_info['columns']
    primary_key = table_info['primary_key']
    primary_key_index = columns.index(primary_key)
    
    if request.method == 'POST':
        try:
            # Get updated values for each column
            record = []
            for i, column in enumerate(columns):
                if column == primary_key:
                    # Don't allow changing primary key
                    record.append(primary_key_value)
                else:
                    # Check if this is a file upload field
                    if f'file_{column}' in request.files and request.files[f'file_{column}'].filename:
                        # Handle file upload
                        uploaded_file = request.files[f'file_{column}']
                        if uploaded_file:
                            # Read the file data as bytes
                            file_data = uploaded_file.read()
                            print(f"Uploaded new image for {column}, size: {len(file_data)} bytes")
                            record.append(file_data)
                    else:
                        # Regular form field
                        value = request.form.get(column, '')
                        if value != 'BLOB DATA (use upload)':
                            record.append(value)
                        else:
                            # Keep the existing BLOB value
                            existing_records = db_manager.select(
                                table_name, 
                                condition_col=primary_key, 
                                condition_val=primary_key_value
                            )
                            if existing_records:
                                col_index = columns.index(column)
                                record.append(existing_records[0][col_index])
            
            # Update the record
            condition_col = primary_key
            condition_val = primary_key_value
            
            # For each field, update if necessary
            for i, column in enumerate(columns):
                if column != primary_key:
                    db_manager.update(table_name, 
                                     condition_col=condition_col,
                                     condition_val=condition_val,
                                     update_col=column, 
                                     update_val=record[i])
            
            flash('Record updated successfully', 'success')
            return redirect(url_for('view_table', table_name=table_name))
        except Exception as e:
            import traceback
            print(f"Error updating record: {str(e)}")
            print(traceback.format_exc())
            flash(f'Error updating record: {str(e)}', 'error')
    
    # Get the current record
    record = db_manager.select(table_name, condition_col=primary_key, condition_val=primary_key_value)
    if not record:
        flash('Record not found', 'error')
        return redirect(url_for('view_table', table_name=table_name))
    
    # Process the record for display - handle BLOB data
    display_record = list(record[0])  # Make a copy for display
    has_blob_fields = False
    blob_fields = []
    
    for i, value in enumerate(display_record):
        # Check for binary data (bytes or bytearray)
        if isinstance(value, (bytes, bytearray)) and len(value) > 100:
            display_record[i] = "BLOB DATA (use upload)"
            has_blob_fields = True
            blob_fields.append(columns[i])
        # Check for string that might be a bytearray representation
        elif isinstance(value, str) and value.startswith('bytearray('):
            display_record[i] = "BLOB DATA (use upload)"
            has_blob_fields = True
            blob_fields.append(columns[i])
    
    return render_template('update_record.html',
                          table_name=table_name,
                          columns=columns,
                          record=display_record,
                          primary_key=primary_key,
                          primary_key_value=primary_key_value,
                          has_blob_fields=has_blob_fields,
                          blob_fields=blob_fields)

@app.route('/table/<table_name>/delete/<primary_key_value>', methods=['POST'])
def delete_record(table_name, primary_key_value):
    """Delete a record from a table."""
    try:
        # Get table information
        table_info = db_manager.get_table_info(table_name)
        primary_key = table_info['primary_key']
        
        # Try to convert primary key value to appropriate type if needed
        try:
            if primary_key_value.isdigit():
                primary_key_value = int(primary_key_value)
            elif primary_key_value.replace('.', '').isdigit() and primary_key_value.count('.') <= 1:
                primary_key_value = float(primary_key_value)
        except (ValueError, AttributeError):
            pass  # Keep as string if conversion fails
        
        # Delete the record
        deleted_count = db_manager.delete(table_name, condition_col=primary_key, condition_val=primary_key_value)
        
        if deleted_count > 0:
            flash(f'Record with {primary_key}={primary_key_value} deleted successfully', 'success')
        else:
            flash(f'No record found with {primary_key}={primary_key_value}', 'warning')
    except Exception as e:
        import traceback
        print(f"Error deleting record: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error deleting record: {str(e)}', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/visualize/<column>')
def visualize_index(table_name, column):
    """Visualize a B+ tree index."""
    try:
        # Get the table
        table = db_manager._tables[table_name]
        
        # Make sure the column has an index
        if column not in table.indices:
            flash(f'No index exists for column {column}', 'error')
            return redirect(url_for('view_table', table_name=table_name))
        
        # Get the B+ tree for the index
        tree = table.indices[column]
        
        # Create the visualization
        visualizer = BPlusTreeVisualizer(tree)
        
        # Save with timestamp to avoid caching issues
        import time
        timestamp = int(time.time())
        filename = f"{table_name}_{column}_{timestamp}"
        output_path = os.path.join('static', 'temp', filename)
        
        # Generate the visualization
        full_path = visualizer.visualize(filename=output_path, view=False)
        
        # Extract just the filename for rendering
        image_filename = os.path.basename(full_path)
        
        return render_template('visualize_tree.html',
                              table_name=table_name,
                              column=column,
                              image_path=os.path.join('temp', image_filename))
    except Exception as e:
        flash(f'Error visualizing index: {str(e)}', 'error')
        return redirect(url_for('view_table', table_name=table_name))

@app.route('/visualize_bplustree/<table_name>/<column>')
def visualize_bplustree(table_name, column):
    """Alternative route to visualize B+ tree index."""
    try:
        # Get the table
        table = db_manager._tables[table_name]
        
        # Make sure the column has an index
        if column not in table.indices:
            return jsonify({'error': f'No index exists for column {column}'})
        
        # Get the B+ tree for the index
        tree = table.indices[column]
        
        # Print the B+ tree structure to the console
        print("\n=== B+ Tree Structure for {}.{} ===".format(table_name, column))
        tree.display()  # Display the tree structure in the console
        print("=== End of B+ Tree Structure ===\n")
        
        # Debug info about tree
        print(f"B+ Tree info - Root: {tree.root}")
        print(f"B+ Tree order: {tree.order}")
        if tree.root:
            print(f"Root is leaf: {getattr(tree.root, 'is_leaf', False)}")
            print(f"Root keys: {tree.root.keys}")
            if hasattr(tree.root, 'children'):
                print(f"Root has {len([c for c in tree.root.children if c is not None])} children")
        
        # Create the visualization
        visualizer = BPlusTreeVisualizer(tree)
        
        # Generate visualization in a safe manner
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
            temp_path = temp.name
            
        try:
            # Generate the visualization to our temporary file
            print(f"Generating visualization to {temp_path}")
            result_path = visualizer.visualize(filename=temp_path, view=False)
            print(f"Visualization generated at {result_path}")
            
            if not os.path.exists(result_path):
                print(f"Error: Generated file {result_path} doesn't exist!")
                return jsonify({'error': f'Generated file not found: {result_path}'})
                
            # Read the generated image file
            with open(result_path, 'rb') as f:
                image_data = f.read()
                print(f"Read {len(image_data)} bytes from generated image")
            
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if result_path != temp_path and os.path.exists(result_path):
                    os.remove(result_path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp files: {e}")
                
            # Return image directly
            response = send_file(
                io.BytesIO(image_data),
                mimetype='image/png',
                as_attachment=False,
                download_name=f'{table_name}_{column}_bplustree.png'
            )
            
            # Add cache-busting headers
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error in visualization generation: {str(e)}")
            print(traceback.format_exc())
            
            # Create a simple error image with PIL
            try:
                from PIL import Image, ImageDraw
                
                # Create a basic error image
                img = Image.new('RGB', (800, 200), color=(255, 255, 255))
                d = ImageDraw.Draw(img)
                d.text((10, 10), f"Error generating B+ tree visualization:\n{str(e)}", fill=(255, 0, 0))
                d.text((10, 50), f"Tree info: Root is {'empty' if tree.root is None else 'not empty'}", fill=(0, 0, 0))
                
                if tree.root:
                    keys_str = ", ".join(str(k) for k in tree.root.keys if k is not None)
                    d.text((10, 70), f"Root keys: [{keys_str}]", fill=(0, 0, 0))
                    d.text((10, 90), f"Root is leaf: {getattr(tree.root, 'is_leaf', False)}", fill=(0, 0, 0))
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                return send_file(
                    img_byte_arr,
                    mimetype='image/png',
                    as_attachment=False,
                    download_name=f'{table_name}_{column}_error.png'
                )
            except ImportError:
                # If PIL is not available, return JSON error
                return jsonify({
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            
    except Exception as e:
        import traceback
        print(f"Error in visualize_bplustree: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)})

@app.route('/delete_table/<table_name>', methods=['POST'])
def delete_table(table_name):
    """Delete a table from the database."""
    try:
        # Delete the table
        db_manager.drop_table(table_name)
        flash(f'Table {table_name} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting table: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/create_table', methods=['GET', 'POST'])
def create_table():
    """Create a new table in the B+ Tree database."""
    if request.method == 'POST':
        try:
            table_name = request.form.get('table_name')
            primary_key = request.form.get('primary_key')
            
            # Check if table name already exists
            if table_name in db_manager.get_tables():
                flash(f'Table "{table_name}" already exists', 'error')
                return redirect(url_for('create_table'))
            
            # Get columns information
            columns = []
            column_count = int(request.form.get('column_count', 0))
            
            for i in range(column_count):
                column_name = request.form.get(f'column_name_{i}')
                if column_name and column_name not in columns:
                    columns.append(column_name)
            
            # Validate inputs
            if not table_name:
                flash('Table name is required', 'error')
                return redirect(url_for('create_table'))
            
            if not primary_key:
                flash('Primary key column is required', 'error')
                return redirect(url_for('create_table'))
            
            if primary_key not in columns:
                flash('Primary key must be one of the columns', 'error')
                return redirect(url_for('create_table'))
            
            if len(columns) < 1:
                flash('At least one column is required', 'error')
                return redirect(url_for('create_table'))
            
            # Create the table
            db_manager.create_table(table_name, columns, primary_key)
            flash(f'Table "{table_name}" created successfully', 'success')
            return redirect(url_for('view_table', table_name=table_name))
            
        except Exception as e:
            flash(f'Error creating table: {str(e)}', 'error')
            return redirect(url_for('create_table'))
    
    return render_template('create_table.html')

@app.route('/create_table/preview', methods=['POST'])
def create_table_preview():
    """Preview table structure before creation."""
    try:
        table_name = request.form.get('table_name')
        primary_key = request.form.get('primary_key')
        
        # Get columns information
        columns = []
        column_count = int(request.form.get('column_count', 0))
        
        for i in range(column_count):
            column_name = request.form.get(f'column_name_{i}')
            if column_name and column_name not in columns:
                columns.append(column_name)
        
        # Return the preview data
        return jsonify({
            'success': True,
            'table_name': table_name,
            'primary_key': primary_key,
            'columns': columns
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)