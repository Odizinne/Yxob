import sys
import asyncio
import threading
import discord
from discord.ext import commands
from discord.ext import voice_recv
import wave
import os
from datetime import datetime
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
    botConnectedChanged = Signal(bool)  # New signal for bot connection status
    userDetected = Signal(str, str)  # name, user_id (both strings now)
    clearUserList = Signal()  # New signal for clearing the list
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "Ready"
        self._is_recording = False
        self._bot_connected = False  # New property for bot connection
        self._current_sink = None
        self._voice_client = None
        self._user_model = UserListModel()
        self._worker = None
        
        # Store recordings directory for easy access
        self._recordings_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(self._recordings_dir, exist_ok=True)
        
        # Connect signals to model slots
        self.userDetected.connect(self._user_model.add_user)
        self.clearUserList.connect(self._user_model.clear_users)
        
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
    def startBot(self):
        if not self._worker:
            self._worker = AsyncWorker(self)
            self._worker.start()
            self._set_status("Bot starting...")
            self._set_bot_connected(False)  # Initially not connected
            
    def cleanup(self):
        """Clean up resources when app is closing"""
        if self._worker:
            print("Stopping Discord bot worker...")
            self._set_bot_connected(False)
            self._worker.stop()
            self._worker = None
            
    async def _run_bot(self):
        @bot.event
        async def on_ready():
            self._set_status(f"Bot connected as {bot.user}")
            self._set_bot_connected(True)  # Set to True when bot is ready
            print(f"Bot is ready. Connected to {len(bot.guilds)} guilds")
            
        @bot.event
        async def on_disconnect():
            self._set_bot_connected(False)  # Set to False when disconnected
            print("Bot disconnected")
            
        try:
            await bot.start('MTM5OTA5NjE0NDY3MTI4MTE3Mg.GONdOk.48DGFJ1sEAYOSISeMBSu2Of79bZLjJw0xe9Szs')
        except Exception as e:
            self._set_status(f"Bot error: {str(e)}")
            self._set_bot_connected(False)  # Set to False on error
    
    @Slot()
    def startRecording(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(self._start_recording_async(), self._worker.loop)
        
    async def _start_recording_async(self):
        try:
            if not bot.guilds:
                self._set_status("No guilds found - bot needs to be in a server")
                return
                
            guild = bot.guilds[0]
            print(f"Looking for voice channels in guild: {guild.name}")
            
            voice_channel = None
            
            # Find a voice channel with members
            for channel in guild.voice_channels:
                print(f"Voice channel: {channel.name}, members: {len(channel.members)}")
                if channel.members:
                    voice_channel = channel
                    break
                    
            if not voice_channel:
                # If no channels have members, just pick the first one
                if guild.voice_channels:
                    voice_channel = guild.voice_channels[0]
                    self._set_status(f"No members in voice channels, connecting to {voice_channel.name} anyway")
                else:
                    self._set_status("No voice channels found")
                    return
            
            print(f"Connecting to voice channel: {voice_channel.name}")
            self._voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
            self._current_sink = SimpleRecordingSink(callback=self)
            self._voice_client.listen(self._current_sink)
            
            self._set_recording(True)
            self._set_status(f"Recording in {voice_channel.name}")
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
            
        except Exception as e:
            self._set_status(f"Error stopping recording: {str(e)}")

def main():
    app = QGuiApplication(sys.argv)
    
    # Set application organization and name for QStandardPaths
    app.setOrganizationName("Odizinne")
    app.setApplicationName("Yxob")
    
    # Set Qt Quick Controls style to Basic to allow customization    
    qmlRegisterType(DiscordRecorder, "DiscordRecorder", 1, 0, "DiscordRecorder")
    qmlRegisterType(UserListModel, "DiscordRecorder", 1, 0, "UserListModel")
    
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