import os
import uuid
from replit import db
import logging

def get_user(username):
    """Get user by username"""
    try:
        users = db.get("users", {})
        user = users.get(username)
        if user:
            # Ensure all new fields exist for backward compatibility
            default_fields = {
                'bio': '',
                'skills_teach': [],
                'skills_learn': [],
                'github_link': '',
                'linkedin_link': '',
                'website_link': '',
                'sessions_taught': 0,
                'sessions_attended': 0,
                'total_rating': 0,
                'rating_count': 0,
                'average_rating': 0
            }
            for key, default_value in default_fields.items():
                if key not in user:
                    user[key] = default_value
        return user
    except Exception as e:
        logging.error(f"Error getting user {username}: {e}")
        return None

def create_user(username, email, password_hash):
    """Create a new user"""
    try:
        users = db.get("users", {})
        
        # Check if username already exists
        if username in users:
            return None
        
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'bio': '',
            'skills_teach': [],
            'skills_learn': [],
            'github_link': '',
            'linkedin_link': '',
            'website_link': '',
            'sessions_taught': 0,
            'sessions_attended': 0,
            'total_rating': 0,
            'rating_count': 0,
            'average_rating': 0
        }
        
        users[username] = user_data
        db["users"] = users
        
        return user_id
    except Exception as e:
        logging.error(f"Error creating user {username}: {e}")
        return None

def save_session(session_data):
    """Save a session (offer or request) to the database"""
    try:
        sessions = db.get("sessions", {})
        
        session_id = str(uuid.uuid4())
        session_data['id'] = session_id
        
        sessions[session_id] = session_data
        db["sessions"] = sessions
        
        return session_id
    except Exception as e:
        logging.error(f"Error saving session: {e}")
        return None

def get_user_sessions(username):
    """Get all sessions for a user"""
    try:
        sessions = db.get("sessions", {})
        user_sessions = []
        
        for session_id, session_data in sessions.items():
            if session_data.get('user') == username:
                user_sessions.append(session_data)
        
        # Sort by timestamp (newest first)
        user_sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return user_sessions
    except Exception as e:
        logging.error(f"Error getting sessions for user {username}: {e}")
        return []

def get_all_sessions():
    """Get all sessions (for potential matching features)"""
    try:
        sessions = db.get("sessions", {})
        return list(sessions.values())
    except Exception as e:
        logging.error(f"Error getting all sessions: {e}")
        return []

def update_user_profile(username, profile_data):
    """Update user profile information"""
    try:
        users = db.get("users", {})
        if username not in users:
            return False
        
        user = users[username]
        # Update only provided fields
        for key, value in profile_data.items():
            if key in user:
                user[key] = value
        
        users[username] = user
        db["users"] = users
        return True
    except Exception as e:
        logging.error(f"Error updating profile for {username}: {e}")
        return False

def get_users_by_skill(skill):
    """Get users who can teach a specific skill"""
    try:
        users = db.get("users", {})
        matching_users = []
        
        for username, user_data in users.items():
            if skill.lower() in [s.lower() for s in user_data.get('skills_teach', [])]:
                matching_users.append(user_data)
        
        return matching_users
    except Exception as e:
        logging.error(f"Error getting users by skill {skill}: {e}")
        return []

def save_booking(booking_data):
    """Save a session booking"""
    try:
        bookings = db.get("bookings", {})
        
        booking_id = str(uuid.uuid4())
        booking_data['id'] = booking_id
        
        bookings[booking_id] = booking_data
        db["bookings"] = bookings
        
        return booking_id
    except Exception as e:
        logging.error(f"Error saving booking: {e}")
        return None

def get_user_bookings(username):
    """Get all bookings for a user (both as teacher and learner)"""
    try:
        bookings = db.get("bookings", {})
        user_bookings = []
        
        for booking_id, booking_data in bookings.items():
            if booking_data.get('teacher') == username or booking_data.get('learner') == username:
                user_bookings.append(booking_data)
        
        # Sort by booking date
        user_bookings.sort(key=lambda x: x.get('session_date', ''), reverse=True)
        return user_bookings
    except Exception as e:
        logging.error(f"Error getting bookings for user {username}: {e}")
        return []

def save_rating(rating_data):
    """Save a rating for a session"""
    try:
        ratings = db.get("ratings", {})
        
        rating_id = str(uuid.uuid4())
        rating_data['id'] = rating_id
        
        ratings[rating_id] = rating_data
        db["ratings"] = ratings
        
        # Update user's average rating
        rated_user = rating_data.get('rated_user')
        if rated_user:
            update_user_rating(rated_user, rating_data.get('rating', 0))
        
        return rating_id
    except Exception as e:
        logging.error(f"Error saving rating: {e}")
        return None

def update_user_rating(username, new_rating):
    """Update user's average rating"""
    try:
        users = db.get("users", {})
        if username not in users:
            return False
        
        user = users[username]
        current_total = user.get('total_rating', 0)
        current_count = user.get('rating_count', 0)
        
        user['total_rating'] = current_total + new_rating
        user['rating_count'] = current_count + 1
        user['average_rating'] = round(user['total_rating'] / user['rating_count'], 1)
        
        users[username] = user
        db["users"] = users
        return True
    except Exception as e:
        logging.error(f"Error updating rating for {username}: {e}")
        return False

def get_user_ratings(username):
    """Get all ratings received by a user"""
    try:
        ratings = db.get("ratings", {})
        user_ratings = []
        
        for rating_id, rating_data in ratings.items():
            if rating_data.get('rated_user') == username:
                user_ratings.append(rating_data)
        
        # Sort by date (newest first)
        user_ratings.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return user_ratings
    except Exception as e:
        logging.error(f"Error getting ratings for user {username}: {e}")
        return []

def check_availability_conflict(teacher, session_date, start_time, end_time):
    """Check if a teacher has a booking conflict"""
    try:
        bookings = db.get("bookings", {})
        
        for booking_id, booking_data in bookings.items():
            if (booking_data.get('teacher') == teacher and 
                booking_data.get('session_date') == session_date and
                booking_data.get('status') != 'cancelled'):
                
                # Check time overlap
                existing_start = booking_data.get('start_time')
                existing_end = booking_data.get('end_time')
                
                if (start_time < existing_end and end_time > existing_start):
                    return True
        
        return False
    except Exception as e:
        logging.error(f"Error checking availability conflict: {e}")
        return True  # Err on the side of caution
