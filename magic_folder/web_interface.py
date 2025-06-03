"""
Web interface for Magic Folder
Provides visualization, statistics, and management capabilities
"""

import os
import json
import datetime
import time
from pathlib import Path
from collections import defaultdict, Counter
import threading
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename

from magic_folder.config import Config
from magic_folder.analyzer import AIAnalyzer
from magic_folder.file_handler import FileHandler
from magic_folder.utils import log_activity, set_log_file, validate_config_values

# File upload settings
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'xlsx', 'xls', 'csv', 'ppt', 'pptx', 'mp3', 'mp4', 'avi', 'mov'}  # Removed: 'zip', 'rar', '7z'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_UPLOAD = 10  # Maximum files per upload
UPLOAD_RATE_LIMIT = 5  # Maximum uploads per minute per IP

# Enhanced rate limiting tracking (IP + session based)
upload_tracking = defaultdict(list)
session_tracking = defaultdict(list)

# File ID tracking for secure operations
file_registry = {}
file_id_counter = 0
file_registry_lock = threading.Lock()

def generate_file_id(file_path):
    """Generate a secure file ID for operations"""
    global file_id_counter
    with file_registry_lock:
        file_id_counter += 1
        file_id = f"file_{file_id_counter}_{hash(file_path) % 10000}"
        file_registry[file_id] = file_path
        return file_id

def get_file_path_from_id(file_id):
    """Get file path from secure file ID"""
    with file_registry_lock:
        return file_registry.get(file_id)

def clear_file_registry():
    """Clear old file registry entries"""
    with file_registry_lock:
        # Keep only recent entries to prevent memory bloat
        if len(file_registry) > 1000:
            # Remove oldest half
            keys = list(file_registry.keys())
            for key in keys[:len(keys)//2]:
                del file_registry[key]

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_rate_limit(ip_address, session_id=None):
    """Check if the IP address or session has exceeded the upload rate limit"""
    now = time.time()
    
    # Check IP-based rate limiting
    upload_tracking[ip_address] = [t for t in upload_tracking[ip_address] if now - t < 60]
    ip_exceeded = len(upload_tracking[ip_address]) >= UPLOAD_RATE_LIMIT
    
    # Check session-based rate limiting if session ID is provided
    session_exceeded = False
    if session_id:
        session_tracking[session_id] = [t for t in session_tracking[session_id] if now - t < 60]
        session_exceeded = len(session_tracking[session_id]) >= UPLOAD_RATE_LIMIT
    
    # If either limit is exceeded, deny the request
    if ip_exceeded or session_exceeded:
        return False
    
    # Record this upload attempt for both IP and session
    upload_tracking[ip_address].append(now)
    if session_id:
        session_tracking[session_id].append(now)
    
    return True

# Initialize Flask app
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), 'web', 'templates'),
           static_folder=os.path.join(os.path.dirname(__file__), 'web', 'static'))

# CSRF Protection
csrf = CSRFProtect()
# Secret key and CSRF will be initialized after config is loaded

# Global variables
config = None
analyzer = None
file_handler = None
stats = {
    'categories': {},
    'recent_files': [],
    'activity_log': [],
    'category_breakdown': {},
    'keyword_counts': defaultdict(Counter),
    'file_types': Counter(),
    'last_updated': datetime.datetime.now()
}
scheduler = BackgroundScheduler()

def setup_app(config_path=None):
    """Initialize the Magic Folder configuration and modules"""
    global config, analyzer, file_handler, stats
    
    # Initialize configuration
    config = Config(config_path)
    
    # Validate configuration
    config_errors = validate_config_values(config)
    if config_errors:
        for error in config_errors:
            log_activity(f"Configuration error: {error}")
    
    # Set up persistent secret key
    if not config.secret_key:
        config.secret_key = os.urandom(24).hex()
        config.save_config()
    app.secret_key = config.secret_key
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize logging system with the config's log file
    set_log_file(config.log_file)
    
    # Initialize AI analyzer
    analyzer = AIAnalyzer(config)
    
    # Initialize file handler
    file_handler = FileHandler(config, analyzer)
    
    # Collect initial statistics
    update_statistics()
    
    # Schedule regular statistics update
    if not scheduler.running:
        scheduler.add_job(update_statistics, 'interval', minutes=5)
        scheduler.start()
    
    return app

def update_statistics():
    """Update the statistics about the Magic Folder"""
    global stats
    
    if not config:
        return
    
    try:
        # Count files in each category
        category_counts = {}
        total_files = 0
        for category in config.categories:
            category_dir = os.path.join(config.organized_dir, category)
            if os.path.exists(category_dir):
                files = [f for f in os.listdir(category_dir) if os.path.isfile(os.path.join(category_dir, f))]
                category_counts[category] = len(files)
                total_files += len(files)
            else:
                category_counts[category] = 0
        
        # Calculate percentages
        category_breakdown = {}
        for category, count in category_counts.items():
            percentage = (count / total_files * 100) if total_files > 0 else 0
            category_breakdown[category] = {
                'count': count,
                'percentage': round(percentage, 1)
            }
        
        # Get recent files
        recent_files = []
        for category in config.categories:
            category_dir = os.path.join(config.organized_dir, category)
            if os.path.exists(category_dir):
                files = [os.path.join(category_dir, f) for f in os.listdir(category_dir) 
                        if os.path.isfile(os.path.join(category_dir, f))]
                files.sort(key=os.path.getmtime, reverse=True)
                for file_path in files[:5]:  # Get 5 most recent files from each category
                    file_name = os.path.basename(file_path)
                    recent_files.append({
                        'name': file_name,
                        'category': category,
                        'modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                        'size': os.path.getsize(file_path)
                    })
        
        # Sort by modification time
        recent_files.sort(key=lambda x: x['modified'], reverse=True)
        recent_files = recent_files[:20]  # Keep only 20 most recent overall
        
        # Get activity log
        log_file = config.log_file
        activity_log = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f.readlines()[-50:]:  # Get last 50 lines
                    activity_log.append(line.strip())
            activity_log.reverse()  # Most recent first
        
        # Count file types
        file_types = Counter()
        for category in config.categories:
            category_dir = os.path.join(config.organized_dir, category)
            if os.path.exists(category_dir):
                for file in os.listdir(category_dir):
                    if os.path.isfile(os.path.join(category_dir, file)):
                        _, ext = os.path.splitext(file)
                        if ext:
                            file_types[ext.lower()] += 1
        
        # Update stats dictionary
        stats['categories'] = category_counts
        stats['category_breakdown'] = category_breakdown
        stats['recent_files'] = recent_files
        stats['activity_log'] = activity_log
        stats['file_types'] = file_types
        stats['last_updated'] = datetime.datetime.now()
        
    except Exception as e:
        log_activity(f"Error updating statistics: {e}")
        # Set minimal stats to prevent errors
        stats['last_updated'] = datetime.datetime.now()

@app.route('/')
def index():
    """Render the dashboard"""
    if not config:
        return redirect(url_for('setup'))
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          config=config)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup page for initial configuration"""
    if request.method == 'POST':
        # Save configuration
        base_dir = request.form.get('base_dir')
        drop_dir = request.form.get('drop_dir')
        organized_dir = request.form.get('organized_dir')
        
        if base_dir:
            config.base_dir = os.path.expanduser(base_dir)
            config.drop_dir_name = drop_dir or config.drop_dir_name
            config.organized_dir_name = organized_dir or config.organized_dir_name
            config.update_paths()
            config.ensure_directories()
            config.save_config()
            
            flash('Configuration saved successfully')
            return redirect(url_for('index'))
    
    return render_template('setup.html', config=config)

@app.route('/categories')
def categories():
    """View and manage categories"""
    return render_template('categories.html', 
                          stats=stats,
                          config=config)

@app.route('/files')
def files():
    """Browse files by category"""
    category = request.args.get('category', 'all')
    
    files_list = []
    if category == 'all':
        # Get files from all categories
        for cat in config.categories:
            category_dir = os.path.join(config.organized_dir, cat)
            if os.path.exists(category_dir):
                for file in os.listdir(category_dir):
                    file_path = os.path.join(category_dir, file)
                    if os.path.isfile(file_path):
                        files_list.append({
                            'name': file,
                            'category': cat,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        })
    else:
        # Get files from the specified category
        category_dir = os.path.join(config.organized_dir, category)
        if os.path.exists(category_dir):
            for file in os.listdir(category_dir):
                file_path = os.path.join(category_dir, file)
                if os.path.isfile(file_path):
                    files_list.append({
                        'name': file,
                        'category': category,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    })
    
    # Sort by modification time (most recent first)
    files_list.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('files.html', 
                          files=files_list,
                          category=category,
                          config=config)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload files for processing"""
    if request.method == 'POST':
        # Check rate limit
        client_ip = request.environ.get('REMOTE_ADDR', '127.0.0.1')
        if not check_rate_limit(client_ip):
            flash('Upload rate limit exceeded. Please wait a minute before uploading again.', 'error')
            return redirect(request.url)
        
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        
        # Check maximum files per upload
        if len(files) > MAX_FILES_PER_UPLOAD:
            flash(f'Too many files. Maximum {MAX_FILES_PER_UPLOAD} files per upload.', 'error')
            return redirect(request.url)
        
        uploaded_count = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            # Validate file type
            if not allowed_file(file.filename):
                flash(f'File type not allowed: {file.filename}', 'error')
                continue
            
            # Check file size (Flask doesn't enforce MAX_CONTENT_LENGTH for individual files in lists)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > MAX_FILE_SIZE:
                flash(f'File too large (max {MAX_FILE_SIZE // (1024*1024)}MB): {file.filename}', 'error')
                continue
            
            try:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(config.drop_dir, filename)
                
                # Check if file already exists and handle duplicates
                if os.path.exists(upload_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(upload_path):
                        new_filename = f"{base}_{counter}{ext}"
                        upload_path = os.path.join(config.drop_dir, new_filename)
                        counter += 1
                    filename = os.path.basename(upload_path)
                
                file.save(upload_path)
                log_activity(f"File uploaded via web interface: {filename}")
                uploaded_count += 1
                
            except Exception as e:
                log_activity(f"Error uploading {file.filename}: {e}")
                flash(f'Error uploading {file.filename}: {str(e)}', 'error')
        
        if uploaded_count > 0:
            flash(f"{uploaded_count} files uploaded successfully")
        else:
            flash('No files were uploaded', 'warning')
            
        return redirect(url_for('index'))
    
    return render_template('upload.html', config=config)

@app.route('/move_file', methods=['POST'])
def move_file():
    """Move a file to a different category using secure file IDs"""
    file_id = request.form.get('file_id')
    new_category = request.form.get('new_category')
    
    if not file_id or not new_category or new_category not in config.categories:
        flash('Invalid request')
        return redirect(url_for('files'))
    
    # Get file path from secure ID
    file_path = get_file_path_from_id(file_id)
    if not file_path:
        flash('Invalid file reference')
        return redirect(url_for('files'))
    
    # Validate the file path is within organized directory
    try:
        if not os.path.commonpath([file_path, config.organized_dir]) == config.organized_dir:
            flash('Invalid file location')
            return redirect(url_for('files'))
    except ValueError:
        flash('Invalid file location')
        return redirect(url_for('files'))
    
    # Get the current category from the path
    try:
        # Get relative path from organized_dir
        rel_path = os.path.relpath(file_path, config.organized_dir)
        current_category = rel_path.split(os.sep)[0]
    except (ValueError, IndexError):
        flash('Could not determine current category')
        return redirect(url_for('files'))
    
    if current_category == new_category:
        flash('File is already in this category')
        return redirect(url_for('files'))
    
    # Move the file to the new category
    filename = os.path.basename(file_path)
    new_path = os.path.join(config.organized_dir, new_category, filename)
    
    # Ensure the destination directory exists
    new_category_dir = os.path.join(config.organized_dir, new_category)
    if not os.path.exists(new_category_dir):
        os.makedirs(new_category_dir)
    
    try:
        import shutil
        shutil.move(file_path, new_path)
        log_activity(f"Moved {filename} from {current_category} to {new_category}")
        flash(f'Successfully moved {filename} from {current_category} to {new_category}')
    except Exception as e:
        log_activity(f"Error moving {filename}: {e}")
        flash(f'Error moving file: {str(e)}')
    
    return redirect(url_for('files'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for getting statistics"""
    update_statistics()  # Get fresh stats
    return jsonify({
        'categories': stats['category_breakdown'],
        'file_types': dict(stats['file_types']),
        'last_updated': stats['last_updated'].isoformat()
    })

@app.route('/api/log')
def api_log():
    """API endpoint for getting the activity log"""
    return jsonify({
        'log': stats['activity_log'][:30],  # Return the 30 most recent entries
        'last_updated': stats['last_updated'].isoformat()
    })

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Update settings
        try:
            # Basic settings
            config.model_name = request.form.get('model_name', config.model_name)
            config.sample_length = int(request.form.get('sample_length', config.sample_length))
            
            # Feature toggles
            config.enable_content_cache = request.form.get('enable_content_cache') == 'on'
            config.enable_embedding_cache = request.form.get('enable_embedding_cache') == 'on'
            config.enable_feedback_system = request.form.get('enable_feedback_system') == 'on'
            config.dedup_enabled = request.form.get('dedup_enabled') == 'on'
            
            # Save the config
            config.save_config()
            flash('Settings updated successfully')
        except Exception as e:
            flash(f'Error saving settings: {str(e)}')
    
    return render_template('settings.html', config=config)

@app.route('/reports')
def reports():
    """Generate and view reports"""
    # Get the date for the report (default to today)
    date_str = request.args.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
    try:
        report_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        report_date = datetime.datetime.now()
    
    # Generate report data for the selected date
    report_data = generate_report(report_date)
    
    return render_template('reports.html', 
                          report=report_data,
                          report_date=report_date,
                          config=config)

def generate_report(date):
    """
    Generate a report for the specified date
    
    Args:
        date (datetime): The date to generate the report for
        
    Returns:
        dict: Report data
    """
    report = {
        'date': date,
        'categories': {},
        'file_types': {},
        'total_files': 0,
        'total_size': 0,
        'activity': []
    }
    
    # Get timestamp range for the day
    start_of_day = datetime.datetime.combine(date.date(), datetime.time.min).timestamp()
    end_of_day = datetime.datetime.combine(date.date(), datetime.time.max).timestamp()
    
    # Count files in each category created/modified on the specified date
    for category in config.categories:
        category_dir = os.path.join(config.organized_dir, category)
        if os.path.exists(category_dir):
            count = 0
            size = 0
            for file in os.listdir(category_dir):
                file_path = os.path.join(category_dir, file)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    if start_of_day <= mtime <= end_of_day:
                        count += 1
                        size += os.path.getsize(file_path)
                        # Count file types
                        _, ext = os.path.splitext(file)
                        if ext:
                            ext = ext.lower()
                            report['file_types'][ext] = report['file_types'].get(ext, 0) + 1
            
            report['categories'][category] = {
                'count': count,
                'size': size
            }
            report['total_files'] += count
            report['total_size'] += size
    
    # Get activity log for the day
    log_file = config.log_file
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Parse log line to extract date
                try:
                    parts = line.strip().split(' - ', 1)
                    if len(parts) > 1:
                        log_date_str = parts[0]
                        log_date = datetime.datetime.strptime(log_date_str, '%Y-%m-%d %H:%M:%S')
                        if log_date.date() == date.date():
                            report['activity'].append(line.strip())
                except Exception:
                    continue
    
    return report

def generate_weekly_report():
    """Generate a weekly report and email it if configured"""
    # This would integrate with an email service
    # For now, just log that it was generated
    log_activity("Weekly report generated")
    
    # Generate last week's report
    today = datetime.datetime.now()
    last_week = today - datetime.timedelta(days=7)
    report = generate_report(last_week)
    
    # TODO: Email the report
    
    return report

def run_web_interface(config_path=None, host='0.0.0.0', port=5000, debug=False):
    """
    Run the Magic Folder web interface
    
    Args:
        config_path (str, optional): Path to configuration file
        host (str): Host to run the server on
        port (int): Port to run the server on
        debug (bool): Whether to run in debug mode
    """
    setup_app(config_path)
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # This allows running the web interface standalone
    run_web_interface(debug=True) 