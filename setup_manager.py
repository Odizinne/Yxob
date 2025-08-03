import os
import platform
import subprocess
import threading
import requests
from PySide6.QtCore import QObject, Signal, Slot, Property, QStandardPaths, QSettings

class SetupManager(QObject):
    # Define the signals
    setupCompleted = Signal(str)  # Emitted when setup is complete with token
    tokenValidationStatusChanged = Signal(str)
    inviteLinkChanged = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.config_dir = self.get_config_dir()
        self.token_file = os.path.join(self.config_dir, "token.txt")
        self._os_type = platform.system()
        self._token_validation_status = "Not Validated"
        self._client_id = ""
        self._invite_link = ""
        
    def get_config_dir(self):
        """Get platform-specific config directory using Qt's standard paths"""
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        
        # Create directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        return config_dir

    @Property(str, notify=inviteLinkChanged)
    def inviteLink(self):
        return self._invite_link
        
    @Property(str, notify=tokenValidationStatusChanged)
    def tokenValidationStatus(self):
        return self._token_validation_status
    
    @Property(str, constant=True)
    def osType(self):
        return self._os_type
        
    @tokenValidationStatus.setter
    def tokenValidationStatus(self, value):
        if self._token_validation_status != value:
            self._token_validation_status = value
            self.tokenValidationStatusChanged.emit(value)

    @Slot(str)
    def validate_token(self, token):
        """Validate the bot token and generate the invite link."""
        if not token or token.strip() == "":
            self.tokenValidationStatus = "Invalid Token"
            return

        # Run validation in a separate thread to avoid blocking UI
        threading.Thread(target=self._validate_token_async, args=(token,), daemon=True).start()

    def _validate_token_async(self, token):
        """Validate token in a separate thread"""
        try:
            # Fetch client ID from Discord API
            url = "https://discord.com/api/v10/users/@me"
            headers = {"Authorization": f"Bot {token}"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self._client_id = data.get("id")
                self.tokenValidationStatus = "Validated"

                # Permissions: Connect (0x100000), Use Voice Activity (0x2000000)
                permissions = 34603008  # Basic bot permissions + voice permissions
                self._invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self._client_id}&permissions={permissions}&scope=bot"
                self.inviteLinkChanged.emit(self._invite_link)
            elif response.status_code == 401:
                self.tokenValidationStatus = "Invalid Token"
            else:
                self.tokenValidationStatus = f"Error: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            self.tokenValidationStatus = "Error: Request timeout"
        except requests.exceptions.ConnectionError:
            self.tokenValidationStatus = "Error: Connection failed"
        except Exception as e:
            self.tokenValidationStatus = f"Error: {str(e)}"

    def is_setup_complete(self):
        """Check if token is set up"""
        token_valid = False
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                token = f.read().strip()
                token_valid = token != "" and not token.startswith("REPLACE_THIS")

        return token_valid
    
    @Slot(str)
    def save_token(self, token):
        """Save bot token to file and signal completion"""
        with open(self.token_file, "w") as f:
            f.write(token)
        
        self.setupCompleted.emit(token)
    
    @Slot(result=str)
    def get_token(self):
        """Get the saved token"""
        if not os.path.exists(self.token_file):
            return ""
            
        with open(self.token_file, "r") as f:
            token = f.read().strip()
            if token == "" or token.startswith("REPLACE_THIS"):
                return ""
            return token

    # User exclusion methods
    @Slot(result=str)
    def get_excluded_users(self):
        """Get the excluded users list"""
        settings = QSettings()
        return settings.value("excludedUsers", "")

    @Slot(str)
    def set_excluded_users(self, excluded_users):
        """Set the excluded users list"""
        settings = QSettings()
        settings.setValue("excludedUsers", excluded_users)
        settings.sync()

    def get_excluded_users_list(self):
        """Get excluded users as a list"""
        excluded_users_str = self.get_excluded_users()
        if not excluded_users_str.strip():
            return []
        
        # Split by comma and clean up whitespace
        excluded_users = [user.strip().lower() for user in excluded_users_str.split(",")]
        return [user for user in excluded_users if user]  # Remove empty strings