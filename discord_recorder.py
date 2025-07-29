import os
import asyncio
import discord
from discord.ext import commands
from discord.ext import voice_recv
from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    Property,
    QStandardPaths,
    QUrl,
)
from PySide6.QtQml import QmlElement
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QProcess

from audio_sink import SimpleRecordingSink
from workers import AsyncWorker, TranscriptionWorker
from models import UserListModel, RecordingsListModel, GuildsListModel, ChannelsListModel
from setup_manager import SetupManager

QML_IMPORT_NAME = "DiscordRecorder"
QML_IMPORT_MAJOR_VERSION = 1

# Discord bot setup
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@QmlElement
class DiscordRecorder(QObject):
    statusChanged = Signal(str)
    recordingStateChanged = Signal(bool)
    botConnectedChanged = Signal(bool)
    userDetected = Signal(str, str)
    userLeft = Signal(str)
    clearUserList = Signal()
    transcriptionStateChanged = Signal(bool)
    transcriptionStatusChanged = Signal(str)
    hasSelectedRecordingsChanged = Signal(bool)
    guildsUpdated = Signal()
    channelsUpdated = Signal()
    joinedStateChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "Ready"
        self._is_recording = False
        self._bot_connected = False
        self._current_sink = None
        self._voice_client = None
        self._user_model = UserListModel()
        self._recordings_model = RecordingsListModel()
        self._guilds_model = GuildsListModel()
        self._channels_model = ChannelsListModel()
        self._worker = None
        self._transcription_worker = None
        self._is_transcribing = False
        self._transcription_status = ""
        self._selected_guild_index = -1
        self._selected_channel_index = -1
        self._is_joined = False
        self._excluded_users = []

        self._recordings_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        os.makedirs(self._recordings_dir, exist_ok=True)

        # Connect signals
        self.userDetected.connect(self._user_model.add_user)
        self.userLeft.connect(self._user_model.remove_user)
        self.clearUserList.connect(self._user_model.clear_users)

        self._recordings_model.refresh_recordings(self._recordings_dir)
        
        # Load excluded users from settings
        self._load_excluded_users()

    def _load_excluded_users(self):
        """Load excluded users from settings"""
        setup_manager = SetupManager()
        excluded_users_list = setup_manager.get_excluded_users_list()
        self._excluded_users = excluded_users_list
        print(f"Loaded excluded users: {self._excluded_users}")

    @Slot()
    def launchSummarizer(self):
        """Launch the DNDSummarizer executable"""
        try:
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            summarizer_path = os.path.join(script_dir, "summarizer", "bin", "DNDSummarizer.exe")

            if not os.path.exists(summarizer_path):
                print(f"Summarizer not found at: {summarizer_path}")
                return

            process = QProcess()
            success = process.startDetached(summarizer_path)

            if success:
                print(f"Successfully launched summarizer: {summarizer_path}")
            else:
                print(f"Failed to launch summarizer: {summarizer_path}")

        except Exception as e:
            print(f"Error launching summarizer: {e}")

    @Slot(str)
    def updateExcludedUsers(self, excluded_users_str):
        """Update the excluded users list from QML"""
        setup_manager = SetupManager()
        setup_manager.set_excluded_users(excluded_users_str)
        self._load_excluded_users()
        
        # If we're currently recording, update the sink
        if self._current_sink:
            self._current_sink.update_excluded_users(self._excluded_users)
        
        print(f"Updated excluded users from QML: {self._excluded_users}")

    def is_user_excluded(self, user_display_name):
        """Check if a user should be excluded from recording"""
        if not user_display_name:
            return False
        
        user_name_lower = user_display_name.lower()
        return user_name_lower in self._excluded_users

    # Properties
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

    @Property(bool, notify=joinedStateChanged)
    def isJoined(self):
        return self._is_joined

    # Setters
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

    def _set_joined(self, joined):
        if self._is_joined != joined:
            self._is_joined = joined
            self.joinedStateChanged.emit(joined)

    # Guild and Channel management
    @Slot(int)
    def setSelectedGuild(self, index):
        if self._selected_guild_index != index:
            self._selected_guild_index = index
            self.guildsUpdated.emit()

            if self._worker and self._worker.loop:
                asyncio.run_coroutine_threadsafe(
                    self._update_channels_for_guild(index), self._worker.loop
                )

    @Slot(int)
    def setSelectedChannel(self, index):
        if self._selected_channel_index != index:
            self._selected_channel_index = index
            self.channelsUpdated.emit()

    async def _update_channels_for_guild(self, guild_index):
        try:
            self._channels_model.clear_channels()

            if guild_index < 0 or guild_index >= len(bot.guilds):
                self._selected_channel_index = -1
                self.channelsUpdated.emit()
                return

            guild = bot.guilds[guild_index]
            print(f"Updating channels for guild: {guild.name}")

            for channel in guild.voice_channels:
                member_count = len(channel.members)
                self._channels_model.add_channel(
                    channel.name, str(channel.id), member_count
                )

            if guild.voice_channels:
                self._selected_channel_index = 0
            else:
                self._selected_channel_index = -1

            self.channelsUpdated.emit()

        except Exception as e:
            print(f"Error updating channels: {e}")
            self._selected_channel_index = -1
            self.channelsUpdated.emit()

    # File management
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
    def deleteSelectedRecordings(self):
        """Delete selected recordings and refresh the list"""
        deleted_count = self._recordings_model.delete_selected_files()

        if deleted_count > 0:
            print(f"Deleted {deleted_count} recording(s)")
            self.refreshRecordings()
        else:
            print("No files were deleted")

    # Transcription
    @Slot()
    def startTranscription(self):
        """Start transcription of selected recordings"""
        if self._is_transcribing:
            return

        if self._transcription_worker:
            if self._transcription_worker.isRunning():
                self._transcription_worker.terminate()
                self._transcription_worker.wait()
            self._transcription_worker.deleteLater()
            self._transcription_worker = None

        selected_files = self._recordings_model.get_selected_files()
        if not selected_files:
            print("No files selected for transcription")
            return

        print(f"Starting transcription of {len(selected_files)} files")

        self._set_transcribing(True)
        self._set_transcription_status("Preparing transcription...")

        self._transcription_worker = TranscriptionWorker(
            selected_files, self._recordings_dir
        )
        self._transcription_worker.progress.connect(self._set_transcription_status)
        self._transcription_worker.finished.connect(self._on_transcription_finished)
        self._transcription_worker.error.connect(self._on_transcription_error)
        self._transcription_worker.start()

    def _on_transcription_finished(self):
        """Handle transcription completion"""
        self._set_transcribing(False)
        self._set_transcription_status("")

        if self._transcription_worker:
            self._transcription_worker.wait()
            self._transcription_worker.deleteLater()
            self._transcription_worker = None

        self.refreshRecordings()
        print("Transcription completed successfully")

    def _on_transcription_error(self, error_message):
        """Handle transcription error"""
        self._set_transcribing(False)
        self._set_transcription_status(f"Error: {error_message}")

        if self._transcription_worker:
            self._transcription_worker.wait()
            self._transcription_worker.deleteLater()
            self._transcription_worker = None

        print(f"Transcription error: {error_message}")

    # Bot management
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
            self._transcription_worker.deleteLater()

        if self._worker:
            print("Stopping Discord bot worker...")
            self._set_bot_connected(False)
            self._worker.stop()
            self._worker = None

    # Voice channel management
    @Slot()
    def joinChannel(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(
                self._join_channel_async(), self._worker.loop
            )

    async def _join_channel_async(self):
        try:
            if self._voice_client:
                self._set_status("Already connected to a voice channel")
                return

            if not bot.guilds:
                self._set_status("No guilds found - bot needs to be in a server")
                return

            guild = None
            voice_channel = None

            if self._selected_guild_index >= 0 and self._selected_guild_index < len(
                bot.guilds
            ):
                guild = bot.guilds[self._selected_guild_index]

                if (
                    self._selected_channel_index >= 0
                    and self._selected_channel_index < len(guild.voice_channels)
                ):
                    voice_channel = guild.voice_channels[self._selected_channel_index]
                else:
                    # Find a channel with members
                    for channel in guild.voice_channels:
                        if channel.members:
                            voice_channel = channel
                            break

                    if not voice_channel and guild.voice_channels:
                        voice_channel = guild.voice_channels[0]
            else:
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

            print(f"Joining voice channel: {voice_channel.name} in guild: {guild.name}")
            self._voice_client = await voice_channel.connect(
                cls=voice_recv.VoiceRecvClient
            )

            self._set_joined(True)
            self._set_status(f"Joined {voice_channel.name} ({guild.name})")
            print("Successfully joined voice channel")

        except Exception as e:
            self._set_status(f"Error joining channel: {str(e)}")
            print(f"Join error: {e}")

    @Slot()
    def leaveChannel(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(
                self._leave_channel_async(), self._worker.loop
            )

    async def _leave_channel_async(self):
        try:
            if not self._voice_client:
                self._set_status("Not connected to any voice channel")
                return

            if self._is_recording:
                if self._current_sink:
                    self._voice_client.stop_listening()
                    recorded_users = self._current_sink.cleanup()
                    self._current_sink = None

                self._set_recording(False)
                self.clearUserList.emit()
                self.refreshRecordings()

            await self._voice_client.disconnect()
            self._voice_client = None

            self._set_joined(False)
            self._set_status("Left voice channel")
            print("Successfully left voice channel")

        except Exception as e:
            self._set_status(f"Error leaving channel: {str(e)}")
            print(f"Leave error: {e}")

    # Recording management
    @Slot()
    def startRecording(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(
                self._start_recording_async(), self._worker.loop
            )

    async def _start_recording_async(self):
        try:
            # Auto-join if not connected
            if not self._voice_client:
                await self._join_channel_async()
                if not self._voice_client:
                    return

            # Pass excluded users to the sink
            self._current_sink = SimpleRecordingSink(callback=self, excluded_users=self._excluded_users)
            self._voice_client.listen(self._current_sink)

            self._set_recording(True)
            channel_name = "Unknown"
            guild_name = "Unknown"

            if self._voice_client.channel:
                channel_name = self._voice_client.channel.name
                guild_name = self._voice_client.channel.guild.name

            self._set_status(f"Recording in {channel_name} ({guild_name})")
            print("Recording started successfully")
            
            if self._excluded_users:
                print(f"Excluded users: {self._excluded_users}")

        except Exception as e:
            self._set_status(f"Error starting recording: {str(e)}")
            print(f"Recording error: {e}")

    @Slot()
    def stopRecording(self):
        if self._worker and self._worker.loop:
            asyncio.run_coroutine_threadsafe(
                self._stop_recording_async(), self._worker.loop
            )

    async def _stop_recording_async(self):
        try:
            if not self._voice_client:
                self._set_status("Not connected to any voice channel")
                return

            if self._current_sink:
                self._voice_client.stop_listening()
                recorded_users = self._current_sink.cleanup()
                self._current_sink = None

            self._set_recording(False)

            channel_name = "Unknown"
            guild_name = "Unknown"

            if self._voice_client.channel:
                channel_name = self._voice_client.channel.name
                guild_name = self._voice_client.channel.guild.name

            self._set_status(
                f"Recording stopped - still in {channel_name} ({guild_name})"
            )

            self.clearUserList.emit()
            self.refreshRecordings()

        except Exception as e:
            self._set_status(f"Error stopping recording: {str(e)}")

    async def _run_bot(self):
        @bot.event
        async def on_ready():
            self._set_status(f"Bot connected as {bot.user}")
            self._set_bot_connected(True)
            print(f"Bot is ready. Connected to {len(bot.guilds)} guilds")

            self._guilds_model.clear_guilds()
            for guild in bot.guilds:
                self._guilds_model.add_guild(guild.name, str(guild.id))

            self.guildsUpdated.emit()

            if bot.guilds:
                self._selected_guild_index = 0
                await self._update_channels_for_guild(0)

        @bot.event
        async def on_voice_state_update(member, before, after):
            # Only handle events if we're currently recording
            if not self._is_recording or not self._current_sink:
                return
            
            # Check if user left the voice channel we're recording in
            if (before.channel and after.channel != before.channel and 
                self._voice_client and before.channel == self._voice_client.channel):
                
                user_id = str(member.id)
                if user_id in self._current_sink.files:
                    print(f"User {member.display_name} left channel - finalizing their recording")
                    # Close their WAV file
                    self._current_sink.finalize_user_recording(user_id)
                    
                    # Remove from UI
                    self.userLeft.emit(user_id)

        @bot.event
        async def on_disconnect():
            self._set_bot_connected(False)
            self._guilds_model.clear_guilds()
            self._channels_model.clear_channels()
            self.guildsUpdated.emit()
            self.channelsUpdated.emit()
            print("Bot disconnected")

        try:
            setup_manager = SetupManager()
            token = setup_manager.get_token()
            if not token:
                self._set_status("No bot token found - please run setup")
                return

            await bot.start(token)
        except Exception as e:
            self._set_status(f"Bot error: {str(e)}")
            self._set_bot_connected(False)