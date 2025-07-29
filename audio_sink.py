import os
import wave
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

        if user_id not in self.files:
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count
            
            session_suffix = f"_session{session_count}" if session_count > 1 else ""
            filename = f"recording_{self.sessionid}_{user.display_name}{session_suffix}.wav"
            
            filepath = os.path.join(self.recordings_dir, filename)
            wav_file = wave.open(filepath, "wb")
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            self.files[user_id] = wav_file

            print(f"User {user.display_name} {'rejoined' if session_count > 1 else 'joined'} - starting new recording: {filename}")

            if self.callback:
                self.callback.userDetected.emit(user.display_name, user_id)

        if hasattr(data, "pcm") and data.pcm:
            self.files[user_id].writeframes(data.pcm)

    def finalize_user_recording(self, user_id):
        if user_id in self.files:
            print(f"Finalizing recording for user ID: {user_id}")
            self.files[user_id].close()
            del self.files[user_id]
            return True
        return False

    def cleanup(self):
        for user_id, wav_file in self.files.items():
            wav_file.close()
        user_ids = list(self.files.keys())
        self.files.clear()
        self.user_session_count.clear()
        return user_ids

    def get_active_users(self):
        return list(self.files.keys())