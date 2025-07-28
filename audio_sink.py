import os
import wave
from datetime import datetime
from discord.ext import voice_recv
from PySide6.QtCore import QStandardPaths


class SimpleRecordingSink(voice_recv.AudioSink):
    def __init__(self, callback=None):
        super().__init__()
        self.files = {}
        self.sessionid = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.callback = callback
        self.user_session_count = {}  # Track how many times each user joined
        
        self.recordings_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        os.makedirs(self.recordings_dir, exist_ok=True)
        print(f"Recordings will be saved to: {self.recordings_dir}")

    def wants_opus(self):
        return False

    def write(self, user, data):
        if user is None:
            return

        user_id = str(user.id)

        if user_id not in self.files:
            # Increment session count for this user
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count
            
            # Include session count in filename if user rejoined
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
        """Close and finalize a specific user's recording"""
        if user_id in self.files:
            print(f"Finalizing recording for user ID: {user_id}")
            self.files[user_id].close()
            del self.files[user_id]
            return True
        return False

    def cleanup(self):
        """Close all remaining open files"""
        for user_id, wav_file in self.files.items():
            wav_file.close()
        user_ids = list(self.files.keys())
        self.files.clear()
        self.user_session_count.clear()
        return user_ids

    def get_active_users(self):
        """Get list of currently recording user IDs"""
        return list(self.files.keys())