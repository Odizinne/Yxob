import sys
import os
from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from discord_recorder import DiscordRecorder
from models import UserListModel, RecordingsListModel, GuildsListModel, ChannelsListModel
from setup_manager import SetupManager
import rc_main


def main():
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