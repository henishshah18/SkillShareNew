import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from db_helper import (get_user, create_user, save_session, get_user_sessions, 
                      update_user_profile, get_users_by_skill, save_booking, 
                      get_user_bookings, save_rating, get_user_ratings, 
                      check_availability_conflict)
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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile with edit functionality"""
    username = session['username']
    user = get_user(username)
    
    if request.method == 'POST':
        # Handle profile updates
        bio = request.form.get('bio', '').strip()
        skills_teach = request.form.get('skills_teach', '').strip()
        skills_learn = request.form.get('skills_learn', '').strip()
        github_link = request.form.get('github_link', '').strip()
        linkedin_link = request.form.get('linkedin_link', '').strip()
        website_link = request.form.get('website_link', '').strip()
        
        # Convert skills to lists
        skills_teach_list = [skill.strip() for skill in skills_teach.split(',') if skill.strip()]
        skills_learn_list = [skill.strip() for skill in skills_learn.split(',') if skill.strip()]
        
        profile_data = {
            'bio': bio,
            'skills_teach': skills_teach_list,
            'skills_learn': skills_learn_list,
            'github_link': github_link,
            'linkedin_link': linkedin_link,
            'website_link': website_link
        }
        
        if update_user_profile(username, profile_data):
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Error updating profile. Please try again.', 'error')
    
    # Get updated user data
    user = get_user(username)
    user_sessions = get_user_sessions(username)
    user_bookings = get_user_bookings(username)
    user_ratings = get_user_ratings(username)
    
    # Separate offers and requests
    offers = [s for s in user_sessions if s.get('type') == 'offer']
    requests = [s for s in user_sessions if s.get('type') == 'request']
    
    # Separate bookings by role
    teaching_bookings = [b for b in user_bookings if b.get('teacher') == username]
    learning_bookings = [b for b in user_bookings if b.get('learner') == username]
    
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
    
    def categorize_bookings(bookings):
        upcoming = []
        past = []
        for booking in bookings:
            try:
                booking_date = datetime.strptime(booking.get('session_date', ''), '%Y-%m-%d').date()
                if booking_date >= today:
                    upcoming.append(booking)
                else:
                    past.append(booking)
            except ValueError:
                past.append(booking)
        
        return upcoming, past
    
    upcoming_offers, past_offers = categorize_sessions(offers)
    upcoming_requests, past_requests = categorize_sessions(requests)
    upcoming_teaching, past_teaching = categorize_bookings(teaching_bookings)
    upcoming_learning, past_learning = categorize_bookings(learning_bookings)
    
    return render_template('profile.html', 
                         user=user,
                         username=username,
                         upcoming_offers=upcoming_offers,
                         past_offers=past_offers,
                         upcoming_requests=upcoming_requests,
                         past_requests=past_requests,
                         upcoming_teaching=upcoming_teaching,
                         past_teaching=past_teaching,
                         upcoming_learning=upcoming_learning,
                         past_learning=past_learning,
                         user_ratings=user_ratings)

@app.route('/user/<username>')
@login_required
def view_user_profile(username):
    """View another user's profile"""
    user = get_user(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    
    # Get user's ratings and sessions
    user_ratings = get_user_ratings(username)
    user_sessions = get_user_sessions(username)
    
    # Only show offers (not requests) on public profile
    offers = [s for s in user_sessions if s.get('type') == 'offer']
    
    return render_template('user_profile.html', 
                         user=user,
                         user_ratings=user_ratings,
                         offers=offers)

@app.route('/find', methods=['GET', 'POST'])
@login_required
def find_teachers():
    """Find teachers for a specific skill"""
    if request.method == 'POST':
        skill = request.form.get('skill', '').strip()
        if not skill:
            flash('Please enter a skill to search for', 'error')
            return render_template('find.html')
        
        # Find users who can teach this skill
        teachers = get_users_by_skill(skill)
        
        # Remove current user from results
        current_user = session['username']
        teachers = [t for t in teachers if t['username'] != current_user]
        
        return render_template('find.html', 
                             skill=skill, 
                             teachers=teachers)
    
    return render_template('find.html')

@app.route('/book/<teacher_username>')
@login_required
def book_session(teacher_username):
    """Book a session with a teacher"""
    teacher = get_user(teacher_username)
    if not teacher:
        flash('Teacher not found', 'error')
        return redirect(url_for('find_teachers'))
    
    # Get teacher's available sessions
    teacher_sessions = get_user_sessions(teacher_username)
    offers = [s for s in teacher_sessions if s.get('type') == 'offer']
    
    # Filter for upcoming offers only
    today = datetime.now().date()
    upcoming_offers = []
    
    for offer in offers:
        has_upcoming = False
        for date_str in offer.get('dates', []):
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_obj >= today:
                    has_upcoming = True
                    break
            except ValueError:
                continue
        
        if has_upcoming:
            upcoming_offers.append(offer)
    
    return render_template('book.html', 
                         teacher=teacher,
                         offers=upcoming_offers)

@app.route('/confirm_booking', methods=['POST'])
@login_required
def confirm_booking():
    """Confirm a session booking"""
    teacher_username = request.form.get('teacher')
    session_id = request.form.get('session_id')
    session_date = request.form.get('session_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Validation
    if not all([teacher_username, session_id, session_date, start_time, end_time]):
        flash('Missing booking information', 'error')
        return redirect(url_for('find_teachers'))
    
    # Check if date is in the future
    try:
        if session_date:
            booking_date = datetime.strptime(session_date, '%Y-%m-%d').date()
            if booking_date < datetime.now().date():
                flash('Cannot book sessions in the past', 'error')
                return redirect(url_for('book_session', teacher_username=teacher_username))
        else:
            flash('Session date is required', 'error')
            return redirect(url_for('book_session', teacher_username=teacher_username))
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('book_session', teacher_username=teacher_username))
    
    # Check for conflicts
    if check_availability_conflict(teacher_username, session_date, start_time, end_time):
        flash('This time slot is no longer available', 'error')
        return redirect(url_for('book_session', teacher_username=teacher_username))
    
    # Create booking
    booking_data = {
        'teacher': teacher_username,
        'learner': session['username'],
        'session_id': session_id,
        'session_date': session_date,
        'start_time': start_time,
        'end_time': end_time,
        'status': 'confirmed',
        'created_at': datetime.now().isoformat()
    }
    
    booking_id = save_booking(booking_data)
    if booking_id:
        flash('Session booked successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Error booking session. Please try again.', 'error')
        return redirect(url_for('book_session', teacher_username=teacher_username))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing all sessions and bookings"""
    username = session['username']
    user = get_user(username)
    user_bookings = get_user_bookings(username)
    
    # Separate bookings by role
    teaching_bookings = [b for b in user_bookings if b.get('teacher') == username]
    learning_bookings = [b for b in user_bookings if b.get('learner') == username]
    
    # Separate upcoming and past bookings
    today = datetime.now().date()
    
    def categorize_bookings(bookings):
        upcoming = []
        past = []
        for booking in bookings:
            try:
                booking_date = datetime.strptime(booking.get('session_date', ''), '%Y-%m-%d').date()
                if booking_date >= today:
                    upcoming.append(booking)
                else:
                    past.append(booking)
            except ValueError:
                past.append(booking)
        
        return upcoming, past
    
    upcoming_teaching, past_teaching = categorize_bookings(teaching_bookings)
    upcoming_learning, past_learning = categorize_bookings(learning_bookings)
    
    return render_template('dashboard.html',
                         user=user,
                         upcoming_teaching=upcoming_teaching,
                         past_teaching=past_teaching,
                         upcoming_learning=upcoming_learning,
                         past_learning=past_learning)

@app.route('/rate/<booking_id>', methods=['GET', 'POST'])
@login_required
def rate_session(booking_id):
    """Rate a completed session"""
    # Get booking details
    user_bookings = get_user_bookings(session['username'])
    booking = None
    for b in user_bookings:
        if b.get('id') == booking_id:
            booking = b
            break
    
    if not booking:
        flash('Booking not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if session is in the past
    try:
        booking_date = datetime.strptime(booking.get('session_date', ''), '%Y-%m-%d').date()
        if booking_date >= datetime.now().date():
            flash('Can only rate completed sessions', 'error')
            return redirect(url_for('dashboard'))
    except ValueError:
        flash('Invalid booking date', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        feedback = request.form.get('feedback', '').strip()
        
        try:
            if rating:
                rating_int = int(rating)
                if rating_int < 1 or rating_int > 10:
                    raise ValueError()
            else:
                flash('Please provide a rating', 'error')
                return render_template('rate.html', booking=booking)
        except (ValueError, TypeError):
            flash('Please provide a valid rating (1-10)', 'error')
            return render_template('rate.html', booking=booking)
        
        # Determine who to rate
        current_user = session['username']
        if booking.get('teacher') == current_user:
            rated_user = booking.get('learner')
            role = 'teacher'
        else:
            rated_user = booking.get('teacher')
            role = 'learner'
        
        rating_data = {
            'booking_id': booking_id,
            'rater': current_user,
            'rated_user': rated_user,
            'rating': rating_int,
            'feedback': feedback,
            'role': role,
            'timestamp': datetime.now().isoformat()
        }
        
        if save_rating(rating_data):
            flash('Rating submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error submitting rating. Please try again.', 'error')
    
    return render_template('rate.html', booking=booking)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
