import os
import uuid
from replit import db
import logging

def get_user(username):
    """Get user by username"""
    try:
        users = db.get("users", {})
        return users.get(username)
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
            'password_hash': password_hash
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
