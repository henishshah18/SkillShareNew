import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import logging
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text, default='')
    skills_teach = db.Column(db.JSON, default=list)
    skills_learn = db.Column(db.JSON, default=list)
    github_link = db.Column(db.String(200), default='')
    linkedin_link = db.Column(db.String(200), default='')
    website_link = db.Column(db.String(200), default='')
    sessions_taught = db.Column(db.Integer, default=0)
    sessions_attended = db.Column(db.Integer, default=0)
    total_rating = db.Column(db.Float, default=0)
    rating_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0)

class Session(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'offer' or 'request'
    title = db.Column(db.String(200), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    dates = db.Column(db.JSON, nullable=False)
    time_ranges = db.Column(db.JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    learner = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    session_id = db.Column(db.String(36), db.ForeignKey('session.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Rating(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('booking.id'), nullable=False)
    rated_user = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    rating_user = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Helper functions
def get_user(username):
    """Get user by username"""
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'password_hash': user.password_hash,
                'bio': user.bio,
                'skills_teach': user.skills_teach,
                'skills_learn': user.skills_learn,
                'github_link': user.github_link,
                'linkedin_link': user.linkedin_link,
                'website_link': user.website_link,
                'sessions_taught': user.sessions_taught,
                'sessions_attended': user.sessions_attended,
                'total_rating': user.total_rating,
                'rating_count': user.rating_count,
                'average_rating': user.average_rating
            }
        return None
    except Exception as e:
        logging.error(f"Error getting user {username}: {e}")
        return None

def create_user(username, email, password_hash):
    """Create a new user"""
    try:
        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        db.session.add(user)
        db.session.commit()
        return user.id
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating user {username}: {e}")
        return None

def save_session(session_data):
    """Save a session (offer or request) to the database"""
    try:
        session = Session(
            user=session_data['user'],
            type=session_data['type'],
            title=session_data['title'],
            skill=session_data['skill'],
            description=session_data['description'],
            mode=session_data['mode'],
            dates=session_data['dates'],
            time_ranges=session_data['time_ranges']
        )
        db.session.add(session)
        db.session.commit()
        return session.id
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving session: {e}")
        return None

def get_user_sessions(username):
    """Get all sessions for a user"""
    try:
        sessions = Session.query.filter_by(user=username).order_by(Session.timestamp.desc()).all()
        return [
            {
                'id': session.id,
                'user': session.user,
                'type': session.type,
                'title': session.title,
                'skill': session.skill,
                'description': session.description,
                'mode': session.mode,
                'dates': session.dates,
                'time_ranges': session.time_ranges,
                'timestamp': session.timestamp.isoformat()
            }
            for session in sessions
        ]
    except Exception as e:
        logging.error(f"Error getting sessions for user {username}: {e}")
        return []

def update_user_profile(username, profile_data):
    """Update user profile information"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        
        # Update only provided fields
        for key, value in profile_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile for {username}: {e}")
        return False

def get_users_by_skill(skill):
    """Get users who can teach a specific skill"""
    try:
        users = User.query.all()
        matching_users = []
        
        for user in users:
            if skill.lower() in [s.lower() for s in user.skills_teach]:
                matching_users.append({
                    'id': user.id,
                    'username': user.username,
                    'bio': user.bio,
                    'skills_teach': user.skills_teach,
                    'average_rating': user.average_rating
                })
        
        return matching_users
    except Exception as e:
        logging.error(f"Error getting users by skill {skill}: {e}")
        return []

def save_booking(booking_data):
    """Save a session booking"""
    try:
        booking = Booking(
            teacher=booking_data['teacher'],
            learner=booking_data['learner'],
            session_id=booking_data['session_id'],
            session_date=datetime.strptime(booking_data['session_date'], '%Y-%m-%d').date(),
            start_time=booking_data['start_time'],
            end_time=booking_data['end_time'],
            status=booking_data.get('status', 'pending')
        )
        db.session.add(booking)
        db.session.commit()
        return booking.id
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving booking: {e}")
        return None

def get_user_bookings(username):
    """Get all bookings for a user (both as teacher and learner)"""
    try:
        bookings = Booking.query.filter(
            (Booking.teacher == username) | (Booking.learner == username)
        ).order_by(Booking.session_date.desc()).all()
        
        return [{
            'id': booking.id,
            'teacher': booking.teacher,
            'learner': booking.learner,
            'session_id': booking.session_id,
            'session_date': booking.session_date.strftime('%Y-%m-%d'),
            'start_time': booking.start_time,
            'end_time': booking.end_time,
            'status': booking.status,
            'timestamp': booking.timestamp.isoformat()
        } for booking in bookings]
    except Exception as e:
        logging.error(f"Error getting bookings for user {username}: {e}")
        return []

def save_rating(rating_data):
    """Save a rating for a session"""
    try:
        rating = Rating(
            booking_id=rating_data['booking_id'],
            rated_user=rating_data['rated_user'],
            rating_user=rating_data['rating_user'],
            rating=rating_data['rating'],
            comment=rating_data.get('comment', '')
        )
        db.session.add(rating)
        
        # Update user's average rating
        user = User.query.filter_by(username=rating_data['rated_user']).first()
        if user:
            user.total_rating += rating_data['rating']
            user.rating_count += 1
            user.average_rating = user.total_rating / user.rating_count
        
        db.session.commit()
        return rating.id
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving rating: {e}")
        return None

def get_user_ratings(username):
    """Get all ratings for a user"""
    try:
        ratings = Rating.query.filter_by(rated_user=username).order_by(Rating.timestamp.desc()).all()
        return [{
            'id': rating.id,
            'booking_id': rating.booking_id,
            'rating_user': rating.rating_user,
            'rating': rating.rating,
            'comment': rating.comment,
            'timestamp': rating.timestamp.isoformat()
        } for rating in ratings]
    except Exception as e:
        logging.error(f"Error getting ratings for user {username}: {e}")
        return []

def check_availability_conflict(teacher, session_date, start_time, end_time):
    """Check if there's a booking conflict for the given time slot"""
    try:
        date_obj = datetime.strptime(session_date, '%Y-%m-%d').date()
        existing_bookings = Booking.query.filter(
            Booking.teacher == teacher,
            Booking.session_date == date_obj,
            Booking.status != 'cancelled'
        ).all()
        
        for booking in existing_bookings:
            if (start_time < booking.end_time and end_time > booking.start_time):
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking availability: {e}")
        return True  # Return True to prevent booking in case of error 