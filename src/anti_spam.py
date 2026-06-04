"""
Anti-Spam Module for KomakYaar Bot
Features:
- Flood detection (message rate limiting)
- Spam detection (repeated identical messages)
- Configurable limits per group
"""

import time
from collections import defaultdict


class AntiSpam:
    def __init__(self, db):
        self.db = db
        # Track user message counts: {chat_id: {user_id: [timestamp1, timestamp2, ...]}}
        self.message_timestamps = defaultdict(lambda: defaultdict(list))
        # Track last message content for spam detection
        self.last_message = defaultdict(dict)
        
        # Default settings
        self.DEFAULT_FLOOD_LIMIT = 5  # messages
        self.DEFAULT_FLOOD_WINDOW = 10  # seconds
        self.DEFAULT_SPAM_THRESHOLD = 3  # repeated messages
        
    def get_flood_limit(self, chat_id):
        """Get flood limit for a group"""
        limit = self.db.get_group_setting(chat_id, "FLOOD_LIMIT")
        return int(limit) if limit else self.DEFAULT_FLOOD_LIMIT
    
    def get_flood_window(self, chat_id):
        """Get flood time window for a group"""
        window = self.db.get_group_setting(chat_id, "FLOOD_WINDOW")
        return int(window) if window else self.DEFAULT_FLOOD_WINDOW
    
    def get_spam_threshold(self, chat_id):
        """Get spam threshold for a group"""
        threshold = self.db.get_group_setting(chat_id, "SPAM_THRESHOLD")
        return int(threshold) if threshold else self.DEFAULT_SPAM_THRESHOLD
    
    def check_flood(self, chat_id, user_id):
        """
        Check if user is flooding
        Returns: (is_flooding, message_count)
        """
        if not self.db.get_group_setting(chat_id, "FLOOD_LOCK"):
            return False, 0
            
        limit = self.get_flood_limit(chat_id)
        window = self.get_flood_window(chat_id)
        current_time = time.time()
        
        # Get user's message timestamps
        timestamps = self.message_timestamps[chat_id][user_id]
        
        # Remove old timestamps outside the window
        timestamps = [ts for ts in timestamps if current_time - ts < window]
        self.message_timestamps[chat_id][user_id] = timestamps
        
        # Check if over limit
        if len(timestamps) >= limit:
            return True, len(timestamps)
        
        # Add current timestamp
        timestamps.append(current_time)
        return False, len(timestamps)
    
    def check_spam(self, chat_id, user_id, text):
        """
        Check if user is spamming (repeated identical messages)
        Returns: (is_spam, repeat_count)
        """
        if not self.db.get_group_setting(chat_id, "SPAM_LOCK"):
            return False, 0
            
        if not text:
            return False, 0
            
        threshold = self.get_spam_threshold(chat_id)
        current_time = time.time()
        
        # Get last message info
        last_msg = self.last_message.get(chat_id, {}).get(user_id, {})
        
        if last_msg.get("text") == text:
            # Same message, increment count
            count = last_msg.get("count", 1) + 1
            # Reset if more than threshold time passed
            if current_time - last_msg.get("time", 0) > 60:
                count = 1
            
            self.last_message[chat_id][user_id] = {
                "text": text,
                "count": count,
                "time": current_time
            }
            
            if count >= threshold:
                return True, count
        else:
            # New message, reset count
            self.last_message[chat_id][user_id] = {
                "text": text,
                "count": 1,
                "time": current_time
            }
        
        return False, 0
    
    def check(self, chat_id, user_id, text=""):
        """
        Main check method - checks both flood and spam
        Returns: (violation_type, details)
        violation_type can be: "flood", "spam", or None
        """
        # Check flood
        is_flood, count = self.check_flood(chat_id, user_id)
        if is_flood:
            return "flood", count
        
        # Check spam
        is_spam, count = self.check_spam(chat_id, user_id, text)
        if is_spam:
            return "spam", count
        
        return None, 0
    
    def reset_user(self, chat_id, user_id):
        """Reset flood/spam tracking for a user"""
        if user_id in self.message_timestamps[chat_id]:
            del self.message_timestamps[chat_id][user_id]
        if user_id in self.last_message.get(chat_id, {}):
            del self.last_message[chat_id][user_id]