import os
import threading
import queue
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
        self.audio_queues = {}        # user_id -> queue for audio data
        self.writer_threads = {}      # user_id -> thread writing to wav
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
        print("Continuous recording mode with WAV files")

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

    def start_wav_recorder(self, user_id, wav_filepath):
        """Start WAV file recording for a user"""
        try:
            # Create WAV file with proper parameters
            wav_file = wave.open(wav_filepath, 'wb')
            wav_file.setnchannels(2)      # Stereo
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(48000)  # 48kHz
            
            self.wav_files[user_id] = wav_file
            
            # Create queue for audio data
            audio_queue = queue.Queue(maxsize=200)
            self.audio_queues[user_id] = audio_queue
            
            # Start writer thread
            writer_thread = threading.Thread(
                target=self._write_to_wav,
                args=(user_id, wav_file, audio_queue),
                daemon=True,
                name=f"WAVWriter-{user_id}"
            )
            writer_thread.start()
            self.writer_threads[user_id] = writer_thread
            
            print(f"Started WAV recording for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error starting WAV recorder: {e}")
            return False

    def _write_to_wav(self, user_id, wav_file, audio_queue):
        """Thread function to write audio data to WAV file"""
        try:
            frames_written = 0
            while True:
                try:
                    audio_data = audio_queue.get(timeout=2.0)
                    
                    if audio_data is None:
                        print(f"Received stop signal for user {user_id}, wrote {frames_written} frames")
                        break
                    
                    try:
                        wav_file.writeframes(audio_data)
                        frames_written += len(audio_data) // 4  # 2 channels * 2 bytes per sample
                    except Exception as e:
                        print(f"Error writing to WAV file for user {user_id}: {e}")
                        break
                    
                    audio_queue.task_done()
                    
                except queue.Empty:
                    continue
                    
        except Exception as e:
            print(f"Error in WAV writer thread for user {user_id}: {e}")

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
            
        # Create WAV recorder if it doesn't exist yet
        if user_id not in self.wav_files:
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count

            safe_username = self.sanitize_filename(user.display_name)
            session_suffix = f"_session{session_count}" if session_count > 1 else ""
            filename = f"recording_{self.sessionid}_{safe_username}{session_suffix}.wav"

            filepath = os.path.join(self.recordings_dir, filename)

            if self.start_wav_recorder(user_id, filepath):
                self.files[user_id] = filepath
                print(f"User {user.display_name} - started WAV recording: {filename}")
                
                if self.callback:
                    self.callback.userDetected.emit(user.display_name, user_id)
            else:
                print(f"Failed to start WAV recorder for {user.display_name}")
                return

        # Queue audio data for recording (if not paused)
        if (user_id in self.audio_queues and hasattr(data, "pcm") and 
            data.pcm and not self._is_paused):
            try:
                self.audio_queues[user_id].put(data.pcm, timeout=0.1)
            except queue.Full:
                print(f"Audio queue full for user {user_id}, dropping frame")

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
        
        # Stop all recordings gracefully
        for user_id in user_ids:
            try:
                user_name = self.seen_users.get(user_id, {}).get('name', user_id)
                print(f"Stopping recording for {user_name}...")
                
                # Signal writer thread to stop
                if user_id in self.audio_queues:
                    try:
                        while True:
                            try:
                                self.audio_queues[user_id].get_nowait()
                            except queue.Empty:
                                break
                        
                        self.audio_queues[user_id].put_nowait(None)
                    except queue.Full:
                        pass
                
                # Wait for writer thread to finish
                if user_id in self.writer_threads:
                    self.writer_threads[user_id].join(timeout=5.0)
                    if self.writer_threads[user_id].is_alive():
                        print(f"Writer thread timeout for {user_name}")
                
                # Close WAV file
                if user_id in self.wav_files:
                    try:
                        self.wav_files[user_id].close()
                        print(f"Successfully saved WAV file for {user_name}")
                        
                        # Check file size
                        filepath = self.files.get(user_id, "")
                        if os.path.exists(filepath):
                            file_size = os.path.getsize(filepath)
                            print(f"WAV file size for {user_name}: {file_size} bytes")
                        
                    except Exception as e:
                        print(f"Error closing WAV file for {user_name}: {e}")
                
            except Exception as e:
                print(f"Error cleaning up recording for user {user_id}: {e}")
        
        # Clear all data structures
        self.files.clear()
        self.wav_files.clear()
        self.audio_queues.clear()
        self.writer_threads.clear()
        self.user_session_count.clear()
        self.user_speaking_states.clear()
        self.seen_users.clear()
        
        print("WAV recording cleanup completed")
        return user_ids

    def get_active_users(self):
        return list(self.wav_files.keys())