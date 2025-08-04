# In audio_sink.py - Replace the entire class with this simplified version:

import os
import threading
import re
import struct
import wave
import time
from datetime import datetime
from discord.ext import voice_recv
from PySide6.QtCore import QStandardPaths


class SimpleRecordingSink(voice_recv.AudioSink):
    def __init__(self, callback=None, excluded_users=None):
        super().__init__()
        self.files = {}
        self.wav_files = {}           # user_id -> wave file object
        self.wav_locks = {}           # user_id -> threading lock for file access
        self.sessionid = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.callback = callback
        self.user_session_count = {}
        self.excluded_users = excluded_users or []
        self._is_paused = False
        self._ready_to_record = False

        # Speaking detection
        self.user_speaking_states = {}
        self.speaking_threshold = 50
        
        # Track users who have been seen
        self.seen_users = {}
        
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
        print("Direct WAV writing mode (no queues)")

    def set_ready_to_record(self, ready):
        """Set whether the sink should actually create and write to files"""
        self._ready_to_record = ready
        if ready:
            print("Recording sink is now ready to create files")
        else:
            print("Recording sink will not create new files")

    def sanitize_filename(self, filename):
        """Sanitize a string to be safe for use as a filename"""
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '_', filename)
        sanitized = ''.join(char if ord(char) < 127 or char.isalnum() else '_' 
                          for char in sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('. ')
        
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = sanitized.split('.')[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"_{sanitized}"
        
        if not sanitized or sanitized == '_':
            sanitized = "unknown_user"
        
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized

    def calculate_audio_level(self, pcm_data):
        """Calculate RMS level of PCM audio data"""
        if not pcm_data or len(pcm_data) < 2:
            return 0
        
        try:
            samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
            if not samples:
                return 0
            
            sum_squares = sum(sample * sample for sample in samples)
            rms = (sum_squares / len(samples)) ** 0.5
            return rms
        except:
            return 0

    def update_speaking_state(self, user_id, user_display_name, audio_level):
        """Update speaking state based on audio level"""
        is_speaking_now = audio_level > self.speaking_threshold
        was_speaking = self.user_speaking_states.get(user_id, False)

        self.user_speaking_states[user_id] = is_speaking_now

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

    def create_wav_file(self, user_id, wav_filepath):
        """Create and open WAV file for a user"""
        try:
            wav_file = wave.open(wav_filepath, 'wb')
            wav_file.setnchannels(2)      # Stereo
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(48000)  # 48kHz
            
            self.wav_files[user_id] = wav_file
            self.wav_locks[user_id] = threading.Lock()
            
            print(f"Created WAV file for user {user_id}: {wav_filepath}")
            return True
            
        except Exception as e:
            print(f"Error creating WAV file for user {user_id}: {e}")
            return False

    def wants_opus(self):
        return False

    def write(self, user, data):
        if user is None:
            return

        if self.is_user_excluded(user.display_name):
            return

        user_id = str(user.id)

        # Calculate audio level for speaking detection
        if hasattr(data, "pcm") and data.pcm:
            audio_level = self.calculate_audio_level(data.pcm)
            self.update_speaking_state(user_id, user.display_name, audio_level)

        # Track this user as seen
        if user_id not in self.seen_users:
            self.seen_users[user_id] = {
                'name': user.display_name,
                'id': user_id
            }

        # Only create files and write audio if we're ready to record
        if not self._ready_to_record:
            return
            
        # Create WAV file if it doesn't exist yet
        if user_id not in self.wav_files:
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count

            safe_username = self.sanitize_filename(user.display_name)
            session_suffix = f"_session{session_count}" if session_count > 1 else ""
            filename = f"recording_{self.sessionid}_{safe_username}{session_suffix}.wav"

            filepath = os.path.join(self.recordings_dir, filename)

            if self.create_wav_file(user_id, filepath):
                self.files[user_id] = filepath
                print(f"User {user.display_name} - started WAV recording: {filename}")
                
                if self.callback:
                    self.callback.userDetected.emit(user.display_name, user_id)
            else:
                print(f"Failed to create WAV file for {user.display_name}")
                return

        # Write audio data directly to file (if not paused)
        if (user_id in self.wav_files and hasattr(data, "pcm") and 
            data.pcm and not self._is_paused):
            
            try:
                # Use lock to ensure thread safety
                with self.wav_locks[user_id]:
                    self.wav_files[user_id].writeframes(data.pcm)
                    
            except Exception as e:
                print(f"Error writing audio data for user {user_id}: {e}")
                # Try to recover by removing the problematic file
                if user_id in self.wav_files:
                    try:
                        self.wav_files[user_id].close()
                    except:
                        pass
                    del self.wav_files[user_id]
                    del self.wav_locks[user_id]

    def user_left_channel(self, user_id):
        """Called when user leaves channel"""
        print(f"User {user_id} left channel, keeping recording open")
        
        if user_id in self.user_speaking_states:
            self.user_speaking_states[user_id] = False
            
        if self.callback:
            self.callback.userStoppedSpeaking.emit(user_id)

    def user_joined_channel(self, user_id, user_display_name):
        """Called when user joins channel"""
        print(f"User {user_display_name} joined channel")
        
        self.seen_users[user_id] = {
            'name': user_display_name,
            'id': user_id
        }

    def set_paused(self, paused):
        """Set the paused state"""
        self._is_paused = paused
        print(f"Recording {'paused' if paused else 'resumed'}")

    def cleanup(self):
        """Stop all recordings and clean up"""
        print(f"Stopping recording - closing {len(self.wav_files)} WAV files...")
        user_ids = list(self.wav_files.keys())
        
        # Emit stopped speaking for all users
        if self.callback:
            for user_id in user_ids:
                self.callback.userStoppedSpeaking.emit(user_id)
        
        # Close all WAV files
        for user_id in user_ids:
            try:
                user_name = self.seen_users.get(user_id, {}).get('name', user_id)
                print(f"Closing WAV file for {user_name}...")
                
                # Use lock to ensure thread safety during cleanup
                if user_id in self.wav_locks:
                    with self.wav_locks[user_id]:
                        if user_id in self.wav_files:
                            self.wav_files[user_id].close()
                            print(f"Successfully saved WAV file for {user_name}")
                            
                            # Check file size
                            filepath = self.files.get(user_id, "")
                            if os.path.exists(filepath):
                                file_size = os.path.getsize(filepath)
                                print(f"WAV file size for {user_name}: {file_size} bytes")
                else:
                    # Fallback if no lock exists
                    if user_id in self.wav_files:
                        self.wav_files[user_id].close()
                        print(f"Successfully saved WAV file for {user_name} (no lock)")
                
            except Exception as e:
                print(f"Error closing WAV file for user {user_id}: {e}")
        
        # Clear all data structures
        self.files.clear()
        self.wav_files.clear()
        self.wav_locks.clear()
        self.user_session_count.clear()
        self.user_speaking_states.clear()
        self.seen_users.clear()
        
        print("WAV recording cleanup completed")
        return user_ids

    def get_active_users(self):
        return list(self.wav_files.keys())