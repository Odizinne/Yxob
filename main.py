import sys
import asyncio
import threading
import discord
from discord.ext import commands
from discord.ext import voice_recv
import wave
import os
import glob
from datetime import datetime
from pathlib import Path
import whisper
from PySide6.QtCore import QObject, Signal, Slot, QTimer, Property, QAbstractListModel, Qt, QThread, QModelIndex, QStandardPaths, QUrl
from PySide6.QtQml import qmlRegisterType, QmlElement
from PySide6.QtGui import QGuiApplication, QDesktopServices
from PySide6.QtQml import QQmlApplicationEngine

QML_IMPORT_NAME = "DiscordRecorder"
QML_IMPORT_MAJOR_VERSION = 1

# Discord bot setup
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

class SimpleRecordingSink(voice_recv.AudioSink):
    def __init__(self, callback=None):
        super().__init__()
        self.files = {}
        self.sessionid = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.callback = callback
        
        # Create recordings directory in app data
        self.recordings_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(self.recordings_dir, exist_ok=True)
        print(f"Recordings will be saved to: {self.recordings_dir}")
        
    def wants_opus(self):
        return False
    
    def write(self, user, data):
        if user is None:
            return
            
        user_id = str(user.id)  # Convert to string to avoid overflow
        
        if user_id not in self.files:
            # Remove user_id from filename and save to app data directory
            filename = f"recording_{self.sessionid}_{user.display_name}.wav"
            filepath = os.path.join(self.recordings_dir, filename)
            wav_file = wave.open(filepath, 'wb')
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            self.files[user_id] = wav_file
            
            print(f"New user detected: {user.display_name} (ID: {user_id})")
            print(f"Recording to: {filepath}")
            
            if self.callback:
                # Use display_name which preserves casing and handles nicknames
                self.callback.userDetected.emit(user.display_name, user_id)
                
        if hasattr(data, 'pcm') and data.pcm:
            self.files[user_id].writeframes(data.pcm)
    
    def cleanup(self):
        for user_id, wav_file in self.files.items():
            wav_file.close()
        return list(self.files.keys())

class AsyncWorker(QThread):
    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.loop = None
        self.should_stop = False
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.recorder._run_bot())
        except Exception as e:
            print(f"Bot error: {e}")
        finally:
            self.loop.close()
    
    def stop(self):
        self.should_stop = True
        if self.loop and not self.loop.is_closed():
            # Schedule bot shutdown
            asyncio.run_coroutine_threadsafe(bot.close(), self.loop)
            # Give it a moment to shutdown gracefully
            self.wait(2000)  # Wait up to 2 seconds
            if self.isRunning():
                self.terminate()  # Force terminate if needed

class TranscriptionWorker(QThread):
    progress = Signal(str)  # Status message
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, files_to_transcribe, recordings_dir):
        super().__init__()
        self.files_to_transcribe = files_to_transcribe
        self.recordings_dir = recordings_dir
        self.transcripts_dir = os.path.join(recordings_dir, "transcripts")
        os.makedirs(self.transcripts_dir, exist_ok=True)
        
    def run(self):
        try:
            self.progress.emit("Loading Whisper model...")
            model = whisper.load_model("large")  # "base", "small", "medium", "large" 
            
            total_files = len(self.files_to_transcribe)
            
            for i, wav_file in enumerate(self.files_to_transcribe, 1):
                self.progress.emit(f"Transcribing {os.path.basename(wav_file)} ({i}/{total_files})...")
                
                # Transcribe the audio
                result = model.transcribe(wav_file)
                
                # Create transcript filename
                base_name = os.path.splitext(os.path.basename(wav_file))[0]
                transcript_file = os.path.join(self.transcripts_dir, f"{base_name}.txt")
                
                # Save transcript
                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(result["text"])
                
                print(f"Transcript saved: {transcript_file}")
            
            self.progress.emit(f"Completed transcription of {total_files} files")
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(f"Transcription error: {str(e)}")

@QmlElement
class GuildsListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._guilds = []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._guilds)
        
    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._guilds):
            return None
            
        guild = self._guilds[index.row()]
        if role == Qt.DisplayRole:
            return guild['name']
        elif role == Qt.UserRole:
            return guild['id']
        return None
        
    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"guildId"
        }
    
    @Slot(str, str)
    def add_guild(self, name, guild_id):
        print(f"Adding guild to model: {name} (ID: {guild_id})")
        
        # Check if guild already exists
        for guild in self._guilds:
            if guild['id'] == guild_id:
                return
                
        self.beginInsertRows(QModelIndex(), len(self._guilds), len(self._guilds))
        self._guilds.append({'name': name, 'id': guild_id})
        self.endInsertRows()
    
    @Slot()
    def clear_guilds(self):
        if len(self._guilds) > 0:
            self.beginResetModel()
            self._guilds.clear()
            self.endResetModel()
    
    def get_guild_by_index(self, index):
        if 0 <= index < len(self._guilds):
            return self._guilds[index]
        return None

@QmlElement
class ChannelsListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._channels)
        
    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._channels):
            return None
            
        channel = self._channels[index.row()]
        if role == Qt.DisplayRole:
            return channel['name']
        elif role == Qt.UserRole:
            return channel['id']
        elif role == Qt.UserRole + 1:
            return channel['member_count']
        return None
        
    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"channelId",
            Qt.UserRole + 1: b"memberCount"
        }
    
    @Slot(str, str, int)
    def add_channel(self, name, channel_id, member_count):
        print(f"Adding channel to model: {name} (ID: {channel_id}, Members: {member_count})")
        
        # Check if channel already exists
        for channel in self._channels:
            if channel['id'] == channel_id:
                return
                
        self.beginInsertRows(QModelIndex(), len(self._channels), len(self._channels))
        self._channels.append({'name': name, 'id': channel_id, 'member_count': member_count})
        self.endInsertRows()
    
    @Slot()
    def clear_channels(self):
        if len(self._channels) > 0:
            self.beginResetModel()
            self._channels.clear()
            self.endResetModel()
    
    def get_channel_by_index(self, index):
        if 0 <= index < len(self._channels):
            return self._channels[index]
        return None

@QmlElement
class RecordingsListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._recordings = []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._recordings)
        
    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._recordings):
            return None
            
        recording = self._recordings[index.row()]
        
        if role == Qt.DisplayRole:
            return recording['name']
        elif role == Qt.UserRole:
            return recording['path']
        elif role == Qt.UserRole + 1:
            return recording['selected']
        elif role == Qt.UserRole + 2:
            return recording['size']
        elif role == Qt.UserRole + 3:
            return recording['hasTranscript']
        
        return None
        
    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"path",
            Qt.UserRole + 1: b"selected",
            Qt.UserRole + 2: b"size",
            Qt.UserRole + 3: b"hasTranscript"
        }
    
    def delete_selected_files(self):
        """Delete selected recording files and remove them from the model"""
        files_to_delete = []
        indices_to_remove = []
        
        # Collect files to delete and their indices
        for i, recording in enumerate(self._recordings):
            if recording['selected']:
                files_to_delete.append(recording['path'])
                indices_to_remove.append(i)
        
        if not files_to_delete:
            return 0
        
        deleted_count = 0
        
        # Delete files from filesystem
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")
        
        return deleted_count
    
    def refresh_recordings(self, recordings_dir):
        transcripts_dir = os.path.join(recordings_dir, "transcripts")
        
        self.beginResetModel()
        self._recordings.clear()
        
        # Find all .wav files
        wav_pattern = os.path.join(recordings_dir, "*.wav")
        wav_files = glob.glob(wav_pattern)
        
        for wav_file in sorted(wav_files):
            file_size = os.path.getsize(wav_file)
            size_str = self._format_file_size(file_size)
            
            # Check if transcript exists
            base_name = os.path.splitext(os.path.basename(wav_file))[0]
            transcript_path = os.path.join(transcripts_dir, f"{base_name}.txt")
            has_transcript = os.path.exists(transcript_path)
            
            self._recordings.append({
                'name': os.path.basename(wav_file),
                'path': wav_file,
                'selected': False,
                'size': size_str,
                'hasTranscript': has_transcript
            })
        
        self.endResetModel()
        print(f"Refreshed recordings list: {len(self._recordings)} files found")
    
    def _format_file_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    @Slot(int, bool)
    def set_selected(self, index, selected):
        if 0 <= index < len(self._recordings):
            self._recordings[index]['selected'] = selected
            model_index = self.index(index, 0)
            self.dataChanged.emit(model_index, model_index, [Qt.UserRole + 1])
    
    @Slot(bool)
    def select_all(self, selected):
        for i in range(len(self._recordings)):
            self._recordings[i]['selected'] = selected
        
        if self._recordings:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._recordings) - 1, 0)
            self.dataChanged.emit(top_left, bottom_right, [Qt.UserRole + 1])
    
    def get_selected_files(self):
        return [rec['path'] for rec in self._recordings if rec['selected']]
    
    def has_selected(self):
        return any(rec['selected'] for rec in self._recordings)

@QmlElement
class UserListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._users = []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._users)
        
    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._users):
            return None
            
        user = self._users[index.row()]
        if role == Qt.DisplayRole:
            return user['name']
        elif role == Qt.UserRole:
            return user['id']
        return None
        
    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"userId"
        }
    
    @Slot(str, str)  # Changed from int to str for user_id
    def add_user(self, name, user_id):
        print(f"Adding user to model: {name} (ID: {user_id})")
        
        # Check if user already exists
        for user in self._users:
            if user['id'] == user_id:
                print(f"User {name} already exists in model")
                return
                
        self.beginInsertRows(QModelIndex(), len(self._users), len(self._users))
        self._users.append({'name': name, 'id': user_id})
        self.endInsertRows()
        
        print(f"User {name} added to model. Total users: {len(self._users)}")
    
    @Slot()
    def clear_users(self):
        if len(self._users) > 0:
            print(f"Clearing {len(self._users)} users from model")
            self.beginResetModel()
            self._users.clear()
            self.endResetModel()
        else:
            print("User list already empty")

@QmlElement
class DiscordRecorder(QObject):
    statusChanged = Signal(str)
    recordingStateChanged = Signal(bool)
    botConnectedChanged = Signal(bool)
    userDetected = Signal(str, str)  # name, user_id (both strings now)
    clearUserList = Signal()
    transcriptionStateChanged = Signal(bool)
    transcriptionStatusChanged = Signal(str)
    hasSelectedRecordingsChanged = Signal(bool)
    guildsUpdated = Signal()  # New signal for guild updates
    channelsUpdated = Signal()  # New signal for channel updates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "Ready"
        self._is_recording = False
        self._bot_connected = False
        self._current_sink = None
        self._voice_client = None
        self._user_model = UserListModel()
        self._recordings_model = RecordingsListModel()
        self._guilds_model = GuildsListModel()  # New guild model
        self._channels_model = ChannelsListModel()  # New channel model
        self._worker = None
        self._transcription_worker = None
        self._is_transcribing = False
        self._transcription_status = ""
        self._selected_guild_index = -1  # Track selected guild
        self._selected_channel_index = -1  # Track selected channel
        
        # Store recordings directory for easy access
        self._recordings_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(self._recordings_dir, exist_ok=True)
        
        # Connect signals to model slots
        self.userDetected.connect(self._user_model.add_user)
        self.clearUserList.connect(self._user_model.clear_users)
        
        # Refresh recordings on startup
        self._recordings_model.refresh_recordings(self._recordings_dir)
        
    @Property(str, notify=statusChanged)
    def status(self):
        return self._status
        
    @Property(bool, notify=recordingStateChanged)
    def isRecording(self):
        return self._is_recording
        
    @Property(bool, notify=botConnectedChanged)
    def botConnected(self):
        return self._bot_connected
        
    @Property(UserListModel, constant=True)
    def userModel(self):
        return self._user_model
        
    @Property(RecordingsListModel, constant=True)
    def recordingsModel(self):
        return self._recordings_model
        
    @Property(GuildsListModel, constant=True)
    def guildsModel(self):
        return self._guilds_model
        
    @Property(ChannelsListModel, constant=True)
    def channelsModel(self):
        return self._channels_model
        
    @Property(bool, notify=transcriptionStateChanged)
    def isTranscribing(self):
        return self._is_transcribing
        
    @Property(str, notify=transcriptionStatusChanged)
    def transcriptionStatus(self):
        return self._transcription_status
        
    @Property(bool, notify=hasSelectedRecordingsChanged)
    def hasSelectedRecordings(self):
        return self._recordings_model.has_selected()
    
    @Property(int, notify=guildsUpdated)
    def selectedGuildIndex(self):
        return self._selected_guild_index
    
    @Property(int, notify=channelsUpdated) 
    def selectedChannelIndex(self):
        return self._selected_channel_index
        
    def _set_status(self, status):
        if self._status != status:
            self._status = status
            self.statusChanged.emit(status)
            
    def _set_recording(self, recording):
        if self._is_recording != recording:
            self._is_recording = recording
            self.recordingStateChanged.emit(recording)
            
    def _set_bot_connected(self, connected):
        if self._bot_connected != connected:
            self._bot_connected = connected
            self.botConnectedChanged.emit(connected)
            print(f"Bot connection status changed: {connected}")
            
    def _set_transcribing(self, transcribing):
        if self._is_transcribing != transcribing:
            self._is_transcribing = transcribing
            self.transcriptionStateChanged.emit(transcribing)
            
    def _set_transcription_status(self, status):
        if self._transcription_status != status:
            self._transcription_status = status
            self.transcriptionStatusChanged.emit(status)
    
    @Slot(int)
    def setSelectedGuild(self, index):
        if self._selected_guild_index != index:
            self._selected_guild_index = index
            self.guildsUpdated.emit()
            
            # Update channels when guild changes
            if self._worker and self._worker.loop:
                asyncio.run_coroutine_threadsafe(self._update_channels_for_guild(index), self._worker.loop)
    
    @Slot(int)
    def setSelectedChannel(self, index):
        if self._selected_channel_index != index:
            self._selected_channel_index = index
            self.channelsUpdated.emit()
    
    async def _update_channels_for_guild(self, guild_index):
        try:
            self._channels_model.clear_channels()
            
            if guild_index < 0 or guild_index >= len(bot.guilds):
                self._selected_channel_index = -1  # Reset channel selection
                self.channelsUpdated.emit()
                return
                
            guild = bot.guilds[guild_index]
            print(f"Updating channels for guild: {guild.name}")
            
            for channel in guild.voice_channels:
                member_count = len(channel.members)
                self._channels_model.add_channel(channel.name, str(channel.id), member_count)
            
            # Auto-select first channel if available
            if guild.voice_channels:
                self._selected_channel_index = 0
            else:
                self._selected_channel_index = -1
                
            self.channelsUpdated.emit()
            
        except Exception as e:
            print(f"Error updating channels: {e}")
            self._selected_channel_index = -1
            self.channelsUpdated.emit()
    
    @Slot()
    def openRecordingsFolder(self):
        """Open the recordings folder in the system file manager"""
        folder_url = QUrl.fromLocalFile(self._recordings_dir)
        success = QDesktopServices.openUrl(folder_url)
        if success:
            print(f"Opened recordings folder: {self._recordings_dir}")
        else:
            print(f"Failed to open recordings folder: {self._recordings_dir}")
    
    @Slot()
    def refreshRecordings(self):
        """Refresh the recordings list"""
        self._recordings_model.refresh_recordings(self._recordings_dir)
        self.hasSelectedRecordingsChanged.emit(self._recordings_model.has_selected())
    
    @Slot(int, bool)
    def setRecordingSelected(self, index, selected):
        """Set the selection state of a recording"""
        self._recordings_model.set_selected(index, selected)
        self.hasSelectedRecordingsChanged.emit(self._recordings_model.has_selected())
    
    @Slot(bool)
    def selectAllRecordings(self, selected):
        """Select or deselect all recordings"""
        self._recordings_model.select_all(selected)
        self.hasSelectedRecordingsChanged.emit(self._recordings_model.has_selected())
    
    @Slot()
    def startTranscription(self):
        """Start transcription of selected recordings"""
        if self._is_transcribing:
            return
            
        selected_files = self._recordings_model.get_selected_files()
        if not selected_files:
            print("No files selected for transcription")
            return
            
        print(f"Starting transcription of {len(selected_files)} files")
        
        self._set_transcribing(True)
        self._set_transcription_status("Preparing transcription...")
        
        # Create and start transcription worker
        self._transcription_worker = TranscriptionWorker(selected_files, self._recordings_dir)
        self._transcription_worker.progress.connect(self._set_transcription_status)
        self._transcription_worker.finished.connect(self._on_transcription_finished)
        self._transcription_worker.error.connect(self._on_transcription_error)
        self._transcription_worker.start()
    
    def _on_transcription_finished(self):
        """Handle transcription completion"""
        self._set_transcribing(False)
        self._set_transcription_status("")
        self._transcription_worker = None
        
        # Refresh recordings to show transcript status
        self.refreshRecordings()
        print("Transcription completed successfully")
    
    def _on_transcription_error(self, error_message):
        """Handle transcription error"""
        self._set_transcribing(False)
        self._set_transcription_status(f"Error: {error_message}")
        self._transcription_worker = None
        print(f"Transcription error: {error_message}")
    
    @Slot()
    def startBot(self):
        if not self._worker:
            self._worker = AsyncWorker(self)
            self._worker.start()
            self._set_status("Bot starting...")
            self._set_bot_connected(False)
            
    def cleanup(self):
        """Clean up resources when app is closing"""
        if self._transcription_worker and self._transcription_worker.isRunning():
            print("Stopping transcription worker...")
            self._transcription_worker.terminate()
            self._transcription_worker.wait(3000)
            
        if self._worker:
            print("Stopping Discord bot worker...")
            self._set_bot_connected(False)
            self._worker.stop()
            self._worker = None
            
    async def _run_bot(self):
        @bot.event
        async def on_ready():
            self._set_status(f"Bot connected as {bot.user}")
            self._set_bot_connected(True)
            print(f"Bot is ready. Connected to {len(bot.guilds)} guilds")
            
            # Populate guilds
            self._guilds_model.clear_guilds()
            for guild in bot.guilds:
                self._guilds_model.add_guild(guild.name, str(guild.id))
            
            self.guildsUpdated.emit()
            
            # If we have guilds, select the first one and update channels
            if bot.guilds:
                self._selected_guild_index = 0
                await self._update_channels_for_guild(0)
            
        @bot.event
        async def on_disconnect():
            self._set_bot_connected(False)
            self._guilds_model.clear_guilds()
            self._channels_model.clear_channels()
            self.guildsUpdated.emit()
            self.channelsUpdated.emit()
            print("Bot disconnected")
            
        try:
            await bot.start('MTM5OTA5NjE0NDY3MTI4MTE3Mg.GONdOk.48DGFJ1sEAYOSISeMBSu2Of79bZLjJw0xe9Szs')
        except Exception as e:
            self._set_status(f"Bot error: {str(e)}")
            self._set_bot_connected(False)
    
    @Slot()
    def startRecording(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(self._start_recording_async(), self._worker.loop)
        
    async def _start_recording_async(self):
        try:
            if not bot.guilds:
                self._set_status("No guilds found - bot needs to be in a server")
                return
            
            # Use selected guild and channel
            guild = None
            voice_channel = None
            
            if self._selected_guild_index >= 0 and self._selected_guild_index < len(bot.guilds):
                guild = bot.guilds[self._selected_guild_index]
                print(f"Using selected guild: {guild.name}")
                
                if self._selected_channel_index >= 0 and self._selected_channel_index < len(guild.voice_channels):
                    voice_channel = guild.voice_channels[self._selected_channel_index]
                    print(f"Using selected channel: {voice_channel.name}")
                else:
                    # Fallback to first channel with members
                    for channel in guild.voice_channels:
                        if channel.members:
                            voice_channel = channel
                            break
                    
                    # If no channels have members, use first available
                    if not voice_channel and guild.voice_channels:
                        voice_channel = guild.voice_channels[0]
            else:
                # Fallback to original behavior
                guild = bot.guilds[0]
                for channel in guild.voice_channels:
                    if channel.members:
                        voice_channel = channel
                        break
                        
                if not voice_channel and guild.voice_channels:
                    voice_channel = guild.voice_channels[0]
            
            if not voice_channel:
                self._set_status("No voice channels found")
                return
            
            print(f"Connecting to voice channel: {voice_channel.name} in guild: {guild.name}")
            self._voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
            self._current_sink = SimpleRecordingSink(callback=self)
            self._voice_client.listen(self._current_sink)
            
            self._set_recording(True)
            self._set_status(f"Recording in {voice_channel.name} ({guild.name})")
            print("Recording started successfully")
            
        except Exception as e:
            self._set_status(f"Error starting recording: {str(e)}")
            print(f"Recording error: {e}")
    
    @Slot()
    def stopRecording(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(self._stop_recording_async(), self._worker.loop)
        
    async def _stop_recording_async(self):
        try:
            if self._voice_client:
                self._voice_client.stop_listening()
                await self._voice_client.disconnect()
                self._voice_client = None
                
            if self._current_sink:
                recorded_users = self._current_sink.cleanup()
                self._current_sink = None
                
            self._set_recording(False)
            self._set_status("Recording stopped")
            
            # Clear the user list using signal (thread-safe)
            print("Emitting clearUserList signal")
            self.clearUserList.emit()
            
            # Refresh recordings list to show new recordings
            self.refreshRecordings()
            
        except Exception as e:
            self._set_status(f"Error stopping recording: {str(e)}")

    @Slot()
    def deleteSelectedRecordings(self):
        """Delete selected recordings and refresh the list"""
        deleted_count = self._recordings_model.delete_selected_files()

        if deleted_count > 0:
            print(f"Deleted {deleted_count} recording(s)")
            # Refresh the recordings list to update the UI
            self.refreshRecordings()
        else:
            print("No files were deleted")

def main():
    app = QGuiApplication(sys.argv)
    
    # Set application organization and name for QStandardPaths
    app.setOrganizationName("Odizinne")
    app.setApplicationName("Yxob")
    
    # Register QML types
    qmlRegisterType(DiscordRecorder, "DiscordRecorder", 1, 0, "DiscordRecorder")
    qmlRegisterType(UserListModel, "DiscordRecorder", 1, 0, "UserListModel")
    qmlRegisterType(RecordingsListModel, "DiscordRecorder", 1, 0, "RecordingsListModel")
    qmlRegisterType(GuildsListModel, "DiscordRecorder", 1, 0, "GuildsListModel")
    qmlRegisterType(ChannelsListModel, "DiscordRecorder", 1, 0, "ChannelsListModel")
    
    engine = QQmlApplicationEngine()
    
    # Create recorder instance and register it globally
    recorder = DiscordRecorder()
    engine.rootContext().setContextProperty("recorder", recorder)
    
    # Handle app closing
    def cleanup():
        print("Application closing, cleaning up...")
        recorder.cleanup()
    
    app.aboutToQuit.connect(cleanup)
    
    engine.load("qml/Main.qml")
    
    if not engine.rootObjects():
        return -1
        
    # Start the bot
    recorder.startBot()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())