import os
import glob
from datetime import datetime
from PySide6.QtCore import (
    QAbstractListModel,
    Qt,
    QModelIndex,
    Slot,
)
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "DiscordRecorder"
QML_IMPORT_MAJOR_VERSION = 1


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
            return guild["name"]
        elif role == Qt.UserRole:
            return guild["id"]
        return None

    def roleNames(self):
        return {Qt.DisplayRole: b"name", Qt.UserRole: b"guildId"}

    @Slot(str, str)
    def add_guild(self, name, guild_id):
        print(f"Adding guild to model: {name} (ID: {guild_id})")

        for guild in self._guilds:
            if guild["id"] == guild_id:
                return

        self.beginInsertRows(QModelIndex(), len(self._guilds), len(self._guilds))
        self._guilds.append({"name": name, "id": guild_id})
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
            return channel["name"]
        elif role == Qt.UserRole:
            return channel["id"]
        elif role == Qt.UserRole + 1:
            return channel["member_count"]
        return None

    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"channelId",
            Qt.UserRole + 1: b"memberCount",
        }

    @Slot(str, str, int)
    def add_channel(self, name, channel_id, member_count):
        print(
            f"Adding channel to model: {name} (ID: {channel_id}, Members: {member_count})"
        )

        for channel in self._channels:
            if channel["id"] == channel_id:
                return

        self.beginInsertRows(QModelIndex(), len(self._channels), len(self._channels))
        self._channels.append(
            {"name": name, "id": channel_id, "member_count": member_count}
        )
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
            return recording["name"]
        elif role == Qt.UserRole:
            return recording["path"]
        elif role == Qt.UserRole + 1:
            return recording["selected"]
        elif role == Qt.UserRole + 2:
            return recording["size"]
        elif role == Qt.UserRole + 3:
            return recording["hasTranscript"]
        elif role == Qt.UserRole + 4:  # Add date folder info
            return recording["dateFolder"]

        return None

    def roleNames(self):
        return {
            Qt.DisplayRole: b"name",
            Qt.UserRole: b"path",
            Qt.UserRole + 1: b"selected",
            Qt.UserRole + 2: b"size",
            Qt.UserRole + 3: b"hasTranscript",
            Qt.UserRole + 4: b"dateFolder",
        }

    def delete_selected_files(self):
        files_to_delete = []
        indices_to_remove = []

        for i, recording in enumerate(self._recordings):
            if recording["selected"]:
                files_to_delete.append(recording["path"])
                indices_to_remove.append(i)

        if not files_to_delete:
            return 0

        deleted_count = 0

        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")

        return deleted_count

    def refresh_recordings(self, base_recordings_dir):
        """Scan all date folders for recordings"""
        self.beginResetModel()
        self._recordings.clear()
    
        # Scan for date folders (YYYY-MM-DD format)
        date_folders = []
        if os.path.exists(base_recordings_dir):
            for item in os.listdir(base_recordings_dir):
                item_path = os.path.join(base_recordings_dir, item)
                if os.path.isdir(item_path) and self._is_date_folder(item):
                    date_folders.append(item)
        
        # Also check for any .wav files in the root (for backward compatibility)
        root_wav_files = glob.glob(os.path.join(base_recordings_dir, "*.wav"))
        if root_wav_files:
            date_folders.append("")  # Empty string represents root folder
    
        # Sort date folders (newest first)
        date_folders.sort(reverse=True)
    
        for date_folder in date_folders:
            if date_folder == "":
                # Root folder
                folder_path = base_recordings_dir
                transcripts_dir = os.path.join(base_recordings_dir, "transcripts")
                display_folder = "Root"
            else:
                # Date folder
                folder_path = os.path.join(base_recordings_dir, date_folder)
                transcripts_dir = os.path.join(folder_path, "transcripts")
                display_folder = date_folder
    
            wav_pattern = os.path.join(folder_path, "*.wav")
            wav_files = glob.glob(wav_pattern)
    
            for wav_file in sorted(wav_files):
                file_size = os.path.getsize(wav_file)
                size_str = self._format_file_size(file_size)
    
                base_name = os.path.splitext(os.path.basename(wav_file))[0]
                transcript_path = os.path.join(transcripts_dir, f"{base_name}.txt")
                has_transcript = os.path.exists(transcript_path)
    
                self._recordings.append(
                    {
                        "name": os.path.basename(wav_file),
                        "path": wav_file,
                        "selected": False,
                        "size": size_str,
                        "hasTranscript": has_transcript,
                        "dateFolder": display_folder,
                    }
                )
    
        self.endResetModel()
        print(f"Refreshed recordings list: {len(self._recordings)} files found across {len(date_folders)} folders")

    def _is_date_folder(self, folder_name):
        """Check if folder name matches YYYY-MM-DD format"""
        try:
            datetime.strptime(folder_name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

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
            self._recordings[index]["selected"] = selected
            model_index = self.index(index, 0)
            self.dataChanged.emit(model_index, model_index, [Qt.UserRole + 1])

    @Slot(bool)
    def select_all(self, selected):
        for i in range(len(self._recordings)):
            self._recordings[i]["selected"] = selected

        if self._recordings:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._recordings) - 1, 0)
            self.dataChanged.emit(top_left, bottom_right, [Qt.UserRole + 1])

    def get_selected_files(self):
        return [rec["path"] for rec in self._recordings if rec["selected"]]

    def has_selected(self):
        return any(rec["selected"] for rec in self._recordings)


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
            return user["name"]
        elif role == Qt.UserRole:
            return user["id"]
        elif role == Qt.UserRole + 1:  # Speaking state
            return user.get("speaking", False)
        return None

    def roleNames(self):
        return {
            Qt.DisplayRole: b"name", 
            Qt.UserRole: b"userId",
            Qt.UserRole + 1: b"speaking"
        }

    @Slot(str, str, bool)
    def add_user_with_speaking_state(self, name, user_id, speaking=False):
        """Add user with initial speaking state"""
        print(f"Adding user to model: {name} (ID: {user_id}, Speaking: {speaking})")

        for user in self._users:
            if user["id"] == user_id:
                print(f"User {name} already exists in model, updating speaking state")
                user["speaking"] = speaking
                # Find index and emit dataChanged
                for i, u in enumerate(self._users):
                    if u["id"] == user_id:
                        model_index = self.index(i, 0)
                        self.dataChanged.emit(model_index, model_index, [Qt.UserRole + 1])
                        break
                return

        self.beginInsertRows(QModelIndex(), len(self._users), len(self._users))
        self._users.append({"name": name, "id": user_id, "speaking": speaking})
        self.endInsertRows()

        print(f"User {name} added to model with speaking={speaking}. Total users: {len(self._users)}")

    @Slot(str, str)
    def add_user(self, name, user_id):
        """Add user with default non-speaking state"""
        self.add_user_with_speaking_state(name, user_id, False)

    @Slot(str)
    def remove_user(self, user_id):
        """Remove a user from the model"""
        for i, user in enumerate(self._users):
            if user["id"] == user_id:
                print(f"Removing user {user['name']} from model")
                self.beginRemoveRows(QModelIndex(), i, i)
                self._users.pop(i)
                self.endRemoveRows()
                return
        
        print(f"User ID {user_id} not found in model")

    @Slot(str, bool)
    def set_user_speaking(self, user_id, speaking):
        """Update speaking state for a user"""
        for i, user in enumerate(self._users):
            if user["id"] == user_id:
                if user.get("speaking", False) != speaking:
                    user["speaking"] = speaking
                    model_index = self.index(i, 0)
                    self.dataChanged.emit(model_index, model_index, [Qt.UserRole + 1])
                return
        
        # If user not found and they're speaking, they might be new
        if speaking:
            print(f"User {user_id} is speaking but not in model yet")

    @Slot()
    def clear_users(self):
        if len(self._users) > 0:
            print(f"Clearing {len(self._users)} users from model")
            self.beginResetModel()
            self._users.clear()
            self.endResetModel()
        else:
            print("User list already empty")