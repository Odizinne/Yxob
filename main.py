#!/usr/bin/env python3

import sys
import os
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
import logging
from discord_recorder import DiscordRecorder
from models import UserListModel, RecordingsListModel, GuildsListModel, ChannelsListModel, DateFoldersListModel
from setup_manager import SetupManager
import rc_main

def configure_logging():
    """Configure logging"""
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"
    discord_player_logger = logging.getLogger('discord.player')
    discord_player_logger.setLevel(logging.WARNING)


def main():
    configure_logging()
    app = QGuiApplication(sys.argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon = os.path.join(script_dir, "qml/icons/mic.png")

    app.setOrganizationName("Odizinne")
    app.setApplicationName("Yxob")
    app.setWindowIcon(QIcon(icon))

    qmlRegisterType(DiscordRecorder, "DiscordRecorder", 1, 0, "DiscordRecorder")
    qmlRegisterType(UserListModel, "DiscordRecorder", 1, 0, "UserListModel")
    qmlRegisterType(RecordingsListModel, "DiscordRecorder", 1, 0, "RecordingsListModel")
    qmlRegisterType(GuildsListModel, "DiscordRecorder", 1, 0, "GuildsListModel")
    qmlRegisterType(ChannelsListModel, "DiscordRecorder", 1, 0, "ChannelsListModel")
    qmlRegisterType(SetupManager, "DiscordRecorder", 1, 0, "SetupManager")
    qmlRegisterType(DateFoldersListModel, "DiscordRecorder", 1, 0, "DateFoldersListModel")

    engine = QQmlApplicationEngine()

    setup_manager = SetupManager()
    engine.rootContext().setContextProperty("setupManager", setup_manager)

    recorder = DiscordRecorder()
    engine.rootContext().setContextProperty("recorder", recorder)

    def cleanup():
        print("Application closing, cleaning up...")
        recorder.cleanup()

    app.aboutToQuit.connect(cleanup)

    if not setup_manager.is_setup_complete():
        print("Setup required, showing setup window...")
        engine.load("qml/SetupWindow.qml")

        def on_setup_completed(token):
            print(f"Setup completed with token: {token[:10]}...")
            engine.clearComponentCache()
            engine.load("qml/Main.qml")
            recorder.startBot()

        # Only connect to the explicit setup completion signal
        setup_manager.setupCompleted.connect(on_setup_completed)

    else:
        print("Setup already complete, loading main window...")
        engine.load("qml/Main.qml")
        recorder.startBot()

    if not engine.rootObjects():
        return -1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())