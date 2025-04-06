import os
import sys
import json
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import logging

# Add the parent directory to the path so we can import from the magic_folder module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from magic_folder.document_processor import DocumentProcessor
from magic_folder.file_monitor import FileMonitor
from magic_folder.database import Database
from magic_folder.embeddings import DocumentEmbedder
from magic_folder.settings import Settings

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
settings = Settings()
db = Database(settings.get_database_path())
document_embedder = DocumentEmbedder(settings.get_model_path())
processor = DocumentProcessor(db, document_embedder, settings)

# Make sure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Render the dashboard page."""
    # Get statistics
    total_files = db.get_total_count()
    processed_files = db.get_processed_count()
    pending_files = total_files - processed_files
    issue_files = db.get_error_count()
    
    # Get category distribution
    categories = db.get_category_counts()
    category_labels = json.dumps(list(categories.keys()))
    category_counts = json.dumps(list(categories.values()))
    
    # Get monthly activity data
    activity_data = db.get_monthly_activity()
    activity_labels = json.dumps(list(activity_data.keys()))
    activity_values = json.dumps(list(activity_data.values()))
    
    # Get recent files
    recent_files = db.get_recent_files(10)
    
    # Get activity logs
    activity_logs = db.get_activity_logs(20)
    
    return render_template('index.html',
                           total_files=total_files,
                           processed_files=processed_files,
                           pending_files=pending_files,
                           issue_files=issue_files,
                           category_labels=category_labels,
                           category_counts=category_counts,
                           activity_labels=activity_labels,
                           activity_data=activity_values,
                           recent_files=recent_files,
                           activity_logs=activity_logs,
                           current_year=datetime.datetime.now().year)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handle file uploads."""
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        uploaded_files = request.files.getlist('files[]')
        processed_files = []
        
        for file in uploaded_files:
            if file.filename == '':
                continue
                
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            # Process the file
            try:
                processor.process_document(file_path)
                db.add_activity_log(f"File uploaded and processed: {file.filename}")
                processed_files.append({
                    'name': file.filename,
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                db.add_activity_log(f"Error processing file: {file.filename}")
                processed_files.append({
                    'name': file.filename,
                    'status': 'error',
                    'message': str(e)
                })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'files': processed_files})
        return redirect(url_for('files'))
    
    return render_template('upload.html')

@app.route('/files')
def files():
    """Display all files."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', None)
    search = request.args.get('search', None)
    
    # Get files with pagination
    all_files, total = db.get_files_paginated(page, per_page, category, search)
    
    # Get categories for filter
    categories = db.get_categories()
    
    return render_template('files.html', 
                           files=all_files,
                           total=total,
                           page=page,
                           per_page=per_page,
                           pages=(total + per_page - 1) // per_page,
                           categories=categories,
                           current_category=category,
                           search_query=search)

@app.route('/file/<file_id>')
def file_detail(file_id):
    """Display file details."""
    file_info = db.get_file_by_id(file_id)
    if not file_info:
        return render_template('error.html', message="File not found"), 404
    
    # Get similar files
    similar_files = db.get_similar_files(file_id, 5)
    
    return render_template('file_detail.html', file=file_info, similar_files=similar_files)

@app.route('/file/<file_id>/download')
def download_file(file_id):
    """Download a file."""
    file_info = db.get_file_by_id(file_id)
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_info['path'], as_attachment=True, download_name=file_info['name'])

@app.route('/file/<file_id>/update_category', methods=['POST'])
def update_category(file_id):
    """Update a file's category."""
    category = request.form.get('category')
    if not category:
        return jsonify({'error': 'Category is required'}), 400
    
    success = db.update_file_category(file_id, category)
    if not success:
        return jsonify({'error': 'File not found or update failed'}), 404
    
    db.add_activity_log(f"Updated category for file ID {file_id} to {category}")
    return jsonify({'success': True})

@app.route('/reports')
def reports():
    """Display reports page."""
    # Get date range from parameters or use last 30 days as default
    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=30)
    
    if request.args.get('start_date'):
        start_date = datetime.datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
    if request.args.get('end_date'):
        end_date = datetime.datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
    
    # Get category distribution for the date range
    category_data = db.get_category_counts_by_date_range(start_date, end_date)
    
    # Get daily activity for the date range
    daily_activity = db.get_daily_activity(start_date, end_date)
    
    return render_template('reports.html',
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'),
                           category_data=json.dumps(category_data),
                           daily_activity=json.dumps(daily_activity))

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """Display and update settings."""
    if request.method == 'POST':
        # Update settings
        watch_directory = request.form.get('watch_directory')
        output_directory = request.form.get('output_directory')
        auto_categorize = request.form.get('auto_categorize') == 'on'
        enable_notifications = request.form.get('enable_notifications') == 'on'
        
        # Save settings
        settings.set('watch_directory', watch_directory)
        settings.set('output_directory', output_directory)
        settings.set('auto_categorize', auto_categorize)
        settings.set('enable_notifications', enable_notifications)
        settings.save()
        
        # Restart file monitor if directory changed
        # (In a real app, this would need more complex handling)
        
        db.add_activity_log("Settings updated")
        return redirect(url_for('settings_page'))
    
    # Get current settings
    current_settings = {
        'watch_directory': settings.get('watch_directory'),
        'output_directory': settings.get('output_directory'),
        'auto_categorize': settings.get('auto_categorize'),
        'enable_notifications': settings.get('enable_notifications')
    }
    
    return render_template('settings.html', settings=current_settings)

@app.route('/api/files', methods=['GET'])
def api_files():
    """API endpoint to get files."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', None)
    search = request.args.get('search', None)
    
    files, total = db.get_files_paginated(page, per_page, category, search)
    
    return jsonify({
        'files': files,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """API endpoint to get statistics."""
    return jsonify({
        'total_files': db.get_total_count(),
        'processed_files': db.get_processed_count(),
        'category_counts': db.get_category_counts()
    })

@app.route('/help')
def help_page():
    """Display help page."""
    return render_template('help.html')

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html', message="Server error. Please try again later."), 500

def start_server(host='0.0.0.0', port=5000, debug=False):
    """Start the web server."""
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # Start the server
    start_server(debug=True) 