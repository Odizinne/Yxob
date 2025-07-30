import os
import wave
import re
import struct
import time
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
        
        # Speaking detection - simplified
        self.user_speaking_states = {}
        self.speaking_threshold = 50  # Very low threshold just to detect any audio vs silence
        
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

        # Calculate audio level for speaking detection FIRST
        if hasattr(data, "pcm") and data.pcm:
            audio_level = self.calculate_audio_level(data.pcm)
            # Always update speaking state, even for new users
            self.update_speaking_state(user_id, user.display_name, audio_level)

        if user_id not in self.files:
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count

            # Sanitize the username for filename
            safe_username = self.sanitize_filename(user.display_name)

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

                print(f"User {user.display_name} ({'rejoined' if session_count > 1 else 'joined'}) - starting new recording: {filename}")

                if self.callback:
                    self.callback.userDetected.emit(user.display_name, user_id)

            except Exception as e:
                print(f"Error creating wave file for user {user.display_name}: {e}")
                print(f"Attempted filename: {filename}")
                print(f"Sanitized username: {safe_username}")
                return

        # Write audio data
        try:
            if user_id in self.files and hasattr(data, "pcm") and data.pcm:
                self.files[user_id].writeframes(data.pcm)
        except Exception as e:
            print(f"Error writing audio data for user {user.display_name}: {e}")

    def finalize_user_recording(self, user_id):
        """Safely close a specific user's recording"""
        if user_id in self.files:
            print(f"Finalizing recording for user ID: {user_id}")
            try:
                self.files[user_id].close()
                print(f"Successfully closed recording for user ID: {user_id}")
            except Exception as e:
                print(f"Error closing recording for user ID {user_id}: {e}")
            finally:
                # Always remove from files dict even if close failed
                del self.files[user_id]
                
            # Clean up speaking state and emit stopped speaking
            if user_id in self.user_speaking_states:
                del self.user_speaking_states[user_id]
                
            # Always emit stopped speaking when user leaves
            if self.callback:
                self.callback.userStoppedSpeaking.emit(user_id)
                
            return True
        return False

    def cleanup(self):
        """Safely cleanup all recordings"""
        print(f"Cleaning up {len(self.files)} open recordings...")
        user_ids = list(self.files.keys())
        
        # Emit stopped speaking for all users
        if self.callback:
            for user_id in user_ids:
                self.callback.userStoppedSpeaking.emit(user_id)
        
        for user_id in user_ids:
            try:
                if user_id in self.files:
                    self.files[user_id].close()
                    print(f"Successfully closed recording for user ID: {user_id}")
            except Exception as e:
                print(f"Error closing recording for user ID {user_id}: {e}")
        
        # Clear all data structures
        self.files.clear()
        self.user_session_count.clear()
        self.user_speaking_states.clear()
        
        print("Cleanup completed")
        return user_ids

    def get_active_users(self):
        return list(self.files.keys())