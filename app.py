import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from db_helper import get_user, create_user, save_session, get_user_sessions
from auth import login_required

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

@app.route('/')
def index():
    """Home page - shows different content based on login status"""
    if 'user_id' in session:
        username = session.get('username', 'User')
        return render_template('index.html', logged_in=True, username=username)
    return render_template('index.html', logged_in=False)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('signup.html', username=username, email=email)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html', username=username, email=email)
        
        # Check if user already exists
        existing_user = get_user(username)
        if existing_user:
            flash('Username already exists', 'error')
            return render_template('signup.html', username=username, email=email)
        
        # Create new user
        password_hash = generate_password_hash(password)
        user_id = create_user(username, email, password_hash)
        
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            flash('Account created successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Error creating account. Please try again.', 'error')
            return render_template('signup.html', username=username, email=email)
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html', username=username)
        
        user = get_user(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html', username=username)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/offer', methods=['GET', 'POST'])
@login_required
def offer():
    """Offer a skill session"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        skill = request.form.get('skill', '').strip()
        description = request.form.get('description', '').strip()
        mode = request.form.get('mode', '')
        date_option = request.form.get('date_option', '')
        
        # Preserve form data for error cases
        form_data = {
            'title': title,
            'skill': skill,
            'description': description,
            'mode': mode,
            'date_option': date_option
        }
        
        # Basic validation
        if not all([title, skill, description, mode]):
            flash('All fields are required', 'error')
            return render_template('offer.html', **form_data)
        
        # Handle dates and time ranges
        dates = []
        time_ranges = []
        
        if date_option == 'weekdays':
            # Generate next 5 weekdays
            current_date = datetime.now().date()
            while len(dates) < 5:
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    dates.append(current_date.isoformat())
                current_date += timedelta(days=1)
            # Default time range for presets
            time_ranges = [['09:00', '17:00']]
        elif date_option == 'weekends':
            # Generate next 4 weekend days
            current_date = datetime.now().date()
            while len(dates) < 4:
                if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    dates.append(current_date.isoformat())
                current_date += timedelta(days=1)
            # Default time range for presets
            time_ranges = [['10:00', '16:00']]
        elif date_option == 'custom':
            # Handle custom dates
            custom_dates = request.form.getlist('custom_dates')
            if not custom_dates:
                flash('Please select at least one date', 'error')
                return render_template('offer.html', **form_data)
            
            # Validate dates are not in the past
            today = datetime.now().date()
            for date_str in custom_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date_obj < today:
                        flash('Cannot select dates in the past', 'error')
                        return render_template('offer.html', **form_data)
                    dates.append(date_str)
                except ValueError:
                    flash('Invalid date format', 'error')
                    return render_template('offer.html', **form_data)
            
            # Handle time ranges
            start_times = request.form.getlist('start_time')
            end_times = request.form.getlist('end_time')
            
            if not start_times or not end_times:
                flash('Please add at least one time range', 'error')
                return render_template('offer.html', **form_data)
            
            for start, end in zip(start_times, end_times):
                if not start or not end:
                    flash('Please fill in all time ranges', 'error')
                    return render_template('offer.html', **form_data)
                
                # Validate time format and order
                try:
                    start_time = datetime.strptime(start, '%H:%M').time()
                    end_time = datetime.strptime(end, '%H:%M').time()
                    if start_time >= end_time:
                        flash('End time must be after start time', 'error')
                        return render_template('offer.html', **form_data)
                    time_ranges.append([start, end])
                except ValueError:
                    flash('Invalid time format', 'error')
                    return render_template('offer.html', **form_data)
        
        # Save session to database
        session_data = {
            'user': session['username'],
            'type': 'offer',
            'title': title,
            'skill': skill,
            'description': description,
            'mode': mode,
            'dates': dates,
            'time_ranges': time_ranges,
            'timestamp': datetime.now().isoformat()
        }
        
        session_id = save_session(session_data)
        if session_id:
            flash('Skill session offered successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Error saving session. Please try again.', 'error')
            return render_template('offer.html', **form_data)
    
    return render_template('offer.html')

@app.route('/request', methods=['GET', 'POST'])
@login_required
def request_skill():
    """Request a skill session"""
    if request.method == 'POST':
        skill = request.form.get('skill', '').strip()
        mode = request.form.get('mode', '')
        
        # Preserve form data for error cases
        form_data = {
            'skill': skill,
            'mode': mode
        }
        
        # Basic validation
        if not skill or not mode:
            flash('Skill and session type are required', 'error')
            return render_template('request.html', **form_data)
        
        # Handle custom dates
        custom_dates = request.form.getlist('custom_dates')
        if not custom_dates:
            flash('Please select at least one date', 'error')
            return render_template('request.html', **form_data)
        
        dates = []
        # Validate dates are not in the past
        today = datetime.now().date()
        for date_str in custom_dates:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_obj < today:
                    flash('Cannot select dates in the past', 'error')
                    return render_template('request.html', **form_data)
                dates.append(date_str)
            except ValueError:
                flash('Invalid date format', 'error')
                return render_template('request.html', **form_data)
        
        # Handle time ranges
        start_times = request.form.getlist('start_time')
        end_times = request.form.getlist('end_time')
        
        if not start_times or not end_times:
            flash('Please add at least one time range', 'error')
            return render_template('request.html', **form_data)
        
        time_ranges = []
        for start, end in zip(start_times, end_times):
            if not start or not end:
                flash('Please fill in all time ranges', 'error')
                return render_template('request.html', **form_data)
            
            # Validate time format and order
            try:
                start_time = datetime.strptime(start, '%H:%M').time()
                end_time = datetime.strptime(end, '%H:%M').time()
                if start_time >= end_time:
                    flash('End time must be after start time', 'error')
                    return render_template('request.html', **form_data)
                time_ranges.append([start, end])
            except ValueError:
                flash('Invalid time format', 'error')
                return render_template('request.html', **form_data)
        
        # Save request to database
        session_data = {
            'user': session['username'],
            'type': 'request',
            'skill': skill,
            'mode': mode,
            'dates': dates,
            'time_ranges': time_ranges,
            'timestamp': datetime.now().isoformat()
        }
        
        session_id = save_session(session_data)
        if session_id:
            flash('Skill request submitted successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Error saving request. Please try again.', 'error')
            return render_template('request.html', **form_data)
    
    return render_template('request.html')

@app.route('/profile')
@login_required
def profile():
    """User profile with session calendar"""
    username = session['username']
    user_sessions = get_user_sessions(username)
    
    # Separate offers and requests
    offers = [s for s in user_sessions if s.get('type') == 'offer']
    requests = [s for s in user_sessions if s.get('type') == 'request']
    
    # Separate upcoming and past sessions
    today = datetime.now().date()
    
    def categorize_sessions(sessions):
        upcoming = []
        past = []
        for session in sessions:
            # Check if any date is upcoming
            has_upcoming = False
            for date_str in session.get('dates', []):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date_obj >= today:
                        has_upcoming = True
                        break
                except ValueError:
                    continue
            
            if has_upcoming:
                upcoming.append(session)
            else:
                past.append(session)
        
        return upcoming, past
    
    upcoming_offers, past_offers = categorize_sessions(offers)
    upcoming_requests, past_requests = categorize_sessions(requests)
    
    return render_template('profile.html', 
                         username=username,
                         upcoming_offers=upcoming_offers,
                         past_offers=past_offers,
                         upcoming_requests=upcoming_requests,
                         past_requests=past_requests)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
