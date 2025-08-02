import os
import subprocess
import threading
import queue
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
        self.ffmpeg_processes = {}  # user_id -> subprocess
        self.audio_queues = {}      # user_id -> queue for audio data
        self.writer_threads = {}    # user_id -> thread writing to ffmpeg
        self.sessionid = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.callback = callback
        self.user_session_count = {}
        self.excluded_users = excluded_users or []
        self._is_paused = False
        self._ready_to_record = False

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
        print("Continuous recording mode with direct FFmpeg Opus encoding")

    def set_ready_to_record(self, ready):
        """Set whether the sink should actually create and write to files"""
        self._ready_to_record = ready
        if ready:
            print("Recording sink is now ready to create files")
        else:
            print("Recording sink will not create new files")

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

    def start_ffmpeg_encoder(self, user_id, opus_filepath):
        """Start FFmpeg process for real-time Opus encoding with OGG container"""
        try:
            # Use OGG container for better compatibility
            cmd = [
                'ffmpeg',
                '-f', 's16le',           # Input format: 16-bit little-endian PCM
                '-ar', '48000',          # Sample rate
                '-ac', '2',              # Channels
                '-i', 'pipe:0',          # Read from stdin
                '-c:a', 'libopus',       # Opus codec
                '-f', 'ogg',             # OGG container (better compatibility)
                '-b:a', '64k',           # Bitrate
                '-vbr', 'on',            # Variable bitrate
                '-compression_level', '10',  # Max compression
                '-frame_duration', '20',     # 20ms frames
                '-application', 'voip',      # Optimized for voice
                '-avoid_negative_ts', 'make_zero',  # Avoid timing issues
                '-fflags', '+genpts',    # Generate presentation timestamps
                '-y',                    # Overwrite output
                opus_filepath
            ]
            
            # Use larger buffer and disable buffering
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=8192  # Use reasonable buffer size
            )
            
            self.ffmpeg_processes[user_id] = process
            
            # Create queue for audio data with larger buffer
            audio_queue = queue.Queue(maxsize=200)  # Larger buffer
            self.audio_queues[user_id] = audio_queue
            
            # Start writer thread
            writer_thread = threading.Thread(
                target=self._write_to_ffmpeg,
                args=(user_id, process, audio_queue),
                daemon=True,
                name=f"FFmpegWriter-{user_id}"
            )
            writer_thread.start()
            self.writer_threads[user_id] = writer_thread
            
            print(f"Started FFmpeg OGG Opus encoder for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error starting FFmpeg encoder: {e}")
            return False

    def _write_to_ffmpeg(self, user_id, process, audio_queue):
        """Thread function to write audio data to FFmpeg stdin"""
        try:
            bytes_written = 0
            while True:
                try:
                    # Get audio data from queue (blocking with timeout)
                    audio_data = audio_queue.get(timeout=2.0)
                    
                    # None is our signal to stop
                    if audio_data is None:
                        print(f"Received stop signal for user {user_id}, wrote {bytes_written} bytes total")
                        break
                    
                    # Write to FFmpeg stdin
                    if process.stdin and not process.stdin.closed:
                        try:
                            process.stdin.write(audio_data)
                            process.stdin.flush()
                            bytes_written += len(audio_data)
                        except BrokenPipeError:
                            print(f"FFmpeg process closed stdin for user {user_id}")
                            break
                        except Exception as e:
                            print(f"Error writing to FFmpeg stdin for user {user_id}: {e}")
                            break
                    else:
                        print(f"FFmpeg stdin closed for user {user_id}")
                        break
                    
                    audio_queue.task_done()
                    
                except queue.Empty:
                    # Check if process is still alive
                    if process.poll() is not None:
                        print(f"FFmpeg process died for user {user_id}")
                        break
                    continue
                    
        except Exception as e:
            print(f"Error in FFmpeg writer thread for user {user_id}: {e}")
        finally:
            # Ensure stdin is properly closed
            try:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                    print(f"Closed stdin for user {user_id}")
            except Exception as e:
                print(f"Error closing stdin for user {user_id}: {e}")

    def wants_opus(self):
        return False  # We want PCM data to stream to FFmpeg

    def write(self, user, data):
        if user is None:
            return
    
        # Check if user is excluded
        if self.is_user_excluded(user.display_name):
            return
    
        user_id = str(user.id)
    
        # Calculate audio level for speaking detection FIRST (always do this)
        if hasattr(data, "pcm") and data.pcm:
            audio_level = self.calculate_audio_level(data.pcm)
            # Always update speaking state, even when not ready to record
            self.update_speaking_state(user_id, user.display_name, audio_level)
    
        # Track this user as seen (always do this for UI purposes)
        if user_id not in self.seen_users:
            self.seen_users[user_id] = {
                'name': user.display_name,
                'id': user_id
            }
    
        # Only create files and write audio if we're ready to record
        if not self._ready_to_record:
            return
            
        # Create FFmpeg encoder if it doesn't exist yet
        if user_id not in self.ffmpeg_processes:
            # For continuous recording, we don't increment session count on reconnection
            # Only increment if this is truly a new recording session
            session_count = self.user_session_count.get(user_id, 0) + 1
            self.user_session_count[user_id] = session_count
    
            # Sanitize the username for filename
            safe_username = self.sanitize_filename(user.display_name)
    
            # Only add session suffix if this is actually a new session (not just a reconnection)
            session_suffix = f"_session{session_count}" if session_count > 1 else ""
            filename = f"recording_{self.sessionid}_{safe_username}{session_suffix}.ogg"  # OGG extension
    
            filepath = os.path.join(self.recordings_dir, filename)
    
            if self.start_ffmpeg_encoder(user_id, filepath):
                self.files[user_id] = filepath  # Store filepath for reference
                print(f"User {user.display_name} - started continuous OGG Opus encoding: {filename}")
                
                if self.callback:
                    self.callback.userDetected.emit(user.display_name, user_id)
            else:
                print(f"Failed to start FFmpeg encoder for {user.display_name}")
                return
    
        # Queue audio data for encoding (if not paused)
        if (user_id in self.audio_queues and hasattr(data, "pcm") and 
            data.pcm and not self._is_paused):
            try:
                # Try to put data in queue (non-blocking with short timeout)
                self.audio_queues[user_id].put(data.pcm, timeout=0.1)
            except queue.Full:
                print(f"Audio queue full for user {user_id}, dropping frame")

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
        """Stop all FFmpeg processes and clean up"""
        print(f"Manually stopping recording - stopping {len(self.ffmpeg_processes)} FFmpeg encoders...")
        user_ids = list(self.ffmpeg_processes.keys())
        
        # Emit stopped speaking for all users
        if self.callback:
            for user_id in user_ids:
                self.callback.userStoppedSpeaking.emit(user_id)
        
        # Stop all encoders gracefully
        for user_id in user_ids:
            try:
                user_name = self.seen_users.get(user_id, {}).get('name', user_id)
                print(f"Stopping encoder for {user_name}...")
                
                # Signal writer thread to stop
                if user_id in self.audio_queues:
                    try:
                        # Clear any remaining items in queue first
                        while True:
                            try:
                                self.audio_queues[user_id].get_nowait()
                            except queue.Empty:
                                break
                        
                        # Send stop signal
                        self.audio_queues[user_id].put_nowait(None)
                    except queue.Full:
                        pass  # Queue might be full, that's ok
                
                # Wait for writer thread to finish
                if user_id in self.writer_threads:
                    self.writer_threads[user_id].join(timeout=5.0)
                    if self.writer_threads[user_id].is_alive():
                        print(f"Writer thread timeout for {user_name}")
                
                # Give FFmpeg time to finalize the file
                if user_id in self.ffmpeg_processes:
                    process = self.ffmpeg_processes[user_id]
                    
                    try:
                        # Wait for process to finish encoding
                        print(f"Waiting for FFmpeg to finalize file for {user_name}...")
                        process.wait(timeout=10.0)
                        
                        if process.returncode == 0:
                            # Check if file was created and has reasonable size
                            filepath = self.files.get(user_id, "")
                            if os.path.exists(filepath):
                                file_size = os.path.getsize(filepath)
                                if file_size > 1024:  # At least 1KB
                                    print(f"Successfully completed OGG Opus encoding for {user_name} ({file_size} bytes)")
                                else:
                                    print(f"Warning: File for {user_name} is very small ({file_size} bytes)")
                            else:
                                print(f"Warning: Output file not found for {user_name}")
                        else:
                            stderr_output = ""
                            if process.stderr:
                                try:
                                    stderr_output = process.stderr.read().decode()
                                except:
                                    pass
                            print(f"FFmpeg encoding issues for {user_name} (code {process.returncode}): {stderr_output}")
                            
                    except subprocess.TimeoutExpired:
                        print(f"FFmpeg encoder timeout for {user_name}, terminating forcefully")
                        process.terminate()
                        try:
                            process.wait(timeout=3.0)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            print(f"Force killed FFmpeg process for {user_name}")
                
            except Exception as e:
                print(f"Error cleaning up encoder for user {user_id}: {e}")
        
        # Clear all data structures
        self.files.clear()
        self.ffmpeg_processes.clear()
        self.audio_queues.clear()
        self.writer_threads.clear()
        self.user_session_count.clear()
        self.user_speaking_states.clear()
        self.seen_users.clear()
        
        print("Direct OGG Opus encoding cleanup completed")
        return user_ids

    def get_active_users(self):
        return list(self.ffmpeg_processes.keys())