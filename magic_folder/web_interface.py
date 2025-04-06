"""
Web interface for Magic Folder
Provides visualization, statistics, and management capabilities
"""

import os
import json
import datetime
from pathlib import Path
from collections import defaultdict, Counter
import threading
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename

from magic_folder.config import Config
from magic_folder.analyzer import AIAnalyzer
from magic_folder.file_handler import FileHandler
from magic_folder.utils import log_activity

# Initialize Flask app
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), 'web', 'templates'),
           static_folder=os.path.join(os.path.dirname(__file__), 'web', 'static'))
app.secret_key = os.urandom(24)

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
    'file_types': Counter()
}
scheduler = BackgroundScheduler()

def setup_app(config_path=None):
    """Initialize the Magic Folder configuration and modules"""
    global config, analyzer, file_handler, stats
    
    # Initialize configuration
    config = Config(config_path)
    
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
        with open(log_file, 'r') as f:
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
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        
        for file in files:
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            
            if file:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(config.drop_dir, filename)
                file.save(upload_path)
                log_activity(f"File uploaded via web interface: {filename}")
        
        flash(f"{len(files)} files uploaded successfully")
        return redirect(url_for('index'))
    
    return render_template('upload.html', config=config)

@app.route('/feedback')
def feedback():
    """Manage feedback and corrections"""
    return render_template('feedback.html', 
                          config=config,
                          stats=stats)

@app.route('/move_file', methods=['POST'])
def move_file():
    """Move a file to a different category"""
    file_path = request.form.get('file_path')
    new_category = request.form.get('new_category')
    
    if not file_path or not new_category or new_category not in config.categories:
        flash('Invalid request')
        return redirect(url_for('files'))
    
    # Get the current category from the path
    parts = file_path.split(os.path.sep)
    current_category = None
    for i, part in enumerate(parts):
        if part == config.organized_dir_name and i < len(parts) - 1:
            current_category = parts[i+1]
            break
    
    if not current_category or current_category == new_category:
        flash('File is already in this category')
        return redirect(url_for('files'))
    
    # Create feedback correction by moving to feedback directory
    filename = os.path.basename(file_path)
    feedback_file = f"{current_category}--{filename}"
    feedback_path = os.path.join(config.feedback_dir, new_category, feedback_file)
    
    # Ensure the destination directory exists
    feedback_category_dir = os.path.join(config.feedback_dir, new_category)
    if not os.path.exists(feedback_category_dir):
        os.makedirs(feedback_category_dir)
    
    try:
        # We don't move directly; we put in feedback dir for learning
        import shutil
        shutil.copy2(file_path, feedback_path)
        # The feedback mechanism will handle the move and learn
        flash(f'File will be moved from {current_category} to {new_category}')
    except Exception as e:
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
        with open(log_file, 'r') as f:
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