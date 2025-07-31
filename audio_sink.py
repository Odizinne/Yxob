import os
import wave
import re
import struct
from datetime import datetime
from discord.ext import voice_recv
from PySide6.QtCore import QStandardPaths


class SimpleRecordingSink(voice_recv.AudioSink):
    def __init__(self, callback=None, excluded_users=None):
        super().__init__()
        self.files = {}
        self.sessionid = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.callback = callback
        self.user_session_count = {}
        self.excluded_users = excluded_users or []
        self._is_paused = False

        # Speaking detection - simplified
        self.user_speaking_states = {}
        self.speaking_threshold = 50
        
        # Track users who have been seen (for UI purposes)
        self.seen_users = {}  # user_id -> user info
        
        # Base recordings directory
        self.base_recordings_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.recordings_dir = os.path.join(self.base_recordings_dir, date_str)
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        print(f"Recordings will be saved to: {self.recordings_dir}")
        print(f"Excluded users: {self.excluded_users}")
        print("Continuous recording mode - files will only close when recording is manually stopped")

    def sanitize_filename(self, filename):
        """
        Sanitize a string to be safe for use as a filename on Windows/Linux/Mac
        """
        # Characters that are invalid in Windows filenames: \/:*?"<>| 
        # Also remove control characters (0-31) and other problematic chars
        
        # Replace invalid characters with underscore
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '_', filename)
        
        # Remove or replace other problematic Unicode characters
        # Keep only printable ASCII, basic Latin, and some safe Unicode
        sanitized = ''.join(char if ord(char) < 127 or char.isalnum() else '_' 
                          for char in sanitized)
        
        # Handle multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing dots and spaces (problematic on Windows)
        sanitized = sanitized.strip('. ')
        
        # Handle reserved names on Windows
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = sanitized.split('.')[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"_{sanitized}"
        
        # Ensure filename isn't empty
        if not sanitized or sanitized == '_':
            sanitized = "unknown_user"
        
        # Limit length (Windows has 255 char limit for filenames)
        if len(sanitized) > 100:  # Conservative limit for our use case
            sanitized = sanitized[:100]
        
        return sanitized

    def calculate_audio_level(self, pcm_data):
        """Calculate RMS level of PCM audio data"""
        if not pcm_data or len(pcm_data) < 2:
            return 0
        
        # PCM data is 16-bit, so unpack as shorts
        try:
            samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
            if not samples:
                return 0
            
            # Calculate RMS
            sum_squares = sum(sample * sample for sample in samples)
            rms = (sum_squares / len(samples)) ** 0.5
            return rms
        except:
            return 0

    def update_speaking_state(self, user_id, user_display_name, audio_level):
        """Update speaking state based on audio level - immediate detection only"""
        is_speaking_now = audio_level > self.speaking_threshold
        was_speaking = self.user_speaking_states.get(user_id, False)

        # Always update the current state
        self.user_speaking_states[user_id] = is_speaking_now

        # Only emit signals when state actually changes
        if is_speaking_now != was_speaking:
            if is_speaking_now:
                if self.callback:
                    self.callback.userStartedSpeaking.emit(user_id)
            else:
                if self.callback:
                    self.callback.userStoppedSpeaking.emit(user_id)

    def update_excluded_users(self, excluded_users):
        """Update the excluded users list"""
        self.excluded_users = excluded_users or []
        print(f"Updated excluded users: {self.excluded_users}")

    def is_user_excluded(self, user_display_name):
        """Check if a user should be excluded from recording"""
        if not user_display_name or not self.excluded_users:
            return False
        
        user_name_lower = user_display_name.lower()
        return user_name_lower in self.excluded_users

    def wants_opus(self):
        return False

    def write(self, user, data):
        if user is None:
            return
    
        # Check if user is excluded
        if self.is_user_excluded(user.display_name):
            return
    
        user_id = str(user.id)
    
        # Calculate audio level for speaking detection FIRST (even when paused)
        if hasattr(data, "pcm") and data.pcm:
            audio_level = self.calculate_audio_level(data.pcm)
            # Always update speaking state, even when paused
            self.update_speaking_state(user_id, user.display_name, audio_level)
    
        # Track this user as seen
        if user_id not in self.seen_users:
            self.seen_users[user_id] = {
                'name': user.display_name,
                'id': user_id
            }
    
        # Create recording file if it doesn't exist yet
        if user_id not in self.files:
            # For continuous recording, we don't increment session count on reconnection
            # Only increment if this is truly a new recording session
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count
    
            # Sanitize the username for filename
            safe_username = self.sanitize_filename(user.display_name)
    
            # Only add session suffix if this is actually a new session (not just a reconnection)
            session_suffix = f"_session{session_count}" if session_count > 1 else ""
            filename = f"recording_{self.sessionid}_{safe_username}{session_suffix}.wav"
    
            filepath = os.path.join(self.recordings_dir, filename)
    
            try:
                wav_file = wave.open(filepath, "wb")
                # Set parameters immediately to avoid issues during cleanup
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48000)
                self.files[user_id] = wav_file
    
                print(f"User {user.display_name} - starting continuous recording: {filename}")
    
                if self.callback:
                    self.callback.userDetected.emit(user.display_name, user_id)
    
            except Exception as e:
                print(f"Error creating wave file for user {user.display_name}: {e}")
                print(f"Attempted filename: {filename}")
                print(f"Sanitized username: {safe_username}")
                return
    
        # Write audio data only if not paused (this continues even if user temporarily disconnects)
        try:
            if user_id in self.files and hasattr(data, "pcm") and data.pcm and not self._is_paused:
                self.files[user_id].writeframes(data.pcm)
        except Exception as e:
            print(f"Error writing audio data for user {user.display_name}: {e}")

    def user_left_channel(self, user_id):
        """Called when user leaves channel - but we DON'T close the recording"""
        print(f"User {user_id} left channel, but keeping recording open for continuous recording")
        
        # Just update speaking state to false (they can't speak if they're not in channel)
        if user_id in self.user_speaking_states:
            self.user_speaking_states[user_id] = False
            
        # Emit stopped speaking when user leaves
        if self.callback:
            self.callback.userStoppedSpeaking.emit(user_id)

    def user_joined_channel(self, user_id, user_display_name):
        """Called when user joins channel - update UI but recording continues"""
        print(f"User {user_display_name} joined channel, continuing existing recording")
        
        # Update seen users info
        self.seen_users[user_id] = {
            'name': user_display_name,
            'id': user_id
        }
        
        # If they already have a recording file, we just continue using it
        # No need to create a new file or emit userDetected again

    def set_paused(self, paused):
        """Set the paused state"""
        self._is_paused = paused
        print(f"Recording {'paused' if paused else 'resumed'}")

    def cleanup(self):
        """Safely cleanup all recordings - ONLY called when manually stopping recording"""
        print(f"Manually stopping recording - closing {len(self.files)} continuous recordings...")
        user_ids = list(self.files.keys())
        
        # Emit stopped speaking for all users
        if self.callback:
            for user_id in user_ids:
                self.callback.userStoppedSpeaking.emit(user_id)
        
        for user_id in user_ids:
            try:
                if user_id in self.files:
                    self.files[user_id].close()
                    user_name = self.seen_users.get(user_id, {}).get('name', user_id)
                    print(f"Successfully closed continuous recording for {user_name}")
            except Exception as e:
                print(f"Error closing recording for user ID {user_id}: {e}")
        
        # Clear all data structures
        self.files.clear()
        self.user_session_count.clear()
        self.user_speaking_states.clear()
        self.seen_users.clear()
        
        print("Continuous recording cleanup completed")
        return user_ids

    def get_active_users(self):
        return list(self.files.keys())