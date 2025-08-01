import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import Odizinne.DNDSummarizer

ApplicationWindow {
    id: setupWindow
    width: 500
    height: setupLyt.implicitHeight + 40
    minimumWidth: 500
    minimumHeight: setupLyt.implicitHeight + 40
    visible: true
    title: "Ollama Setup Required"
    Material.theme: UserSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
    flags: Qt.Dialog

    signal setupCompleted()

    ColumnLayout {
        id: setupLyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale

            ColumnLayout {
                anchors.fill: parent
                spacing: 20

                Label {
                    text: "Ollama Installation Required"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                    color: Colors.accentColor
                }

                Label {
                    text: "Ollama is required to generate summaries using AI."
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 14
                }

                Label {
                    text: "Ollama is a free, open-source tool that runs AI models locally on your computer."
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 14
                    color: Material.hintTextColor
                }
            }
        }

        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale

            ColumnLayout {
                anchors.fill: parent
                spacing: 15

                Label {
                    text: "Installation Steps:"
                    font.pixelSize: 14
                    font.bold: true
                    color: Colors.accentColor
                }

                Label {
                    text: "- Click 'Download Ollama' to get the installer"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                }

                Label {
                    text: "- Run the downloaded installer when it appears"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                }

                Label {
                    text: "- Follow the installation wizard and close Ollama window on finished"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                }

                Label {
                    text: "- The summarizer will automatically start once installation is complete"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                }
            }
        }

        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale
            visible: SessionManager.isDownloadingOllama

            RowLayout {
                anchors.fill: parent
                spacing: 15

                BusyIndicator {
                    running: SessionManager.isDownloadingOllama
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Material.accent: Colors.accentColor
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: SessionManager.downloadStatus
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        value: SessionManager.downloadProgress
                        visible: SessionManager.downloadProgress > 0
                        Material.accent: Colors.accentColor

                        Behavior on value {
                            NumberAnimation {
                                duration: 200
                                easing.type: Easing.OutQuad
                            }
                        }
                    }

                    Label {
                        text: {
                            if (SessionManager.downloadStatus.includes("Please complete")) {
                                return "The Ollama installer window should have opened."
                            } else if (SessionManager.downloadStatus.includes("Waiting for Ollama")) {
                                return "Installation detected, waiting for Ollama service to start..."
                            } else if (SessionManager.downloadStatus.includes("Downloading")) {
                                return "Downloading Ollama installer from ollama.com..."
                            } else if (SessionManager.downloadStatus.includes("Starting")) {
                                return "Preparing to launch the installer..."
                            }
                            return ""
                        }
                        Layout.fillWidth: true
                        font.pixelSize: 12
                        color: Material.hintTextColor
                        visible: text !== ""
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Pane {
            Layout.fillWidth: true
            Material.background: Qt.rgba(Colors.accentColor.r, Colors.accentColor.g, Colors.accentColor.b, 0.3)
            Material.elevation: 2
            Material.roundedScale: Material.ExtraSmallScale
            visible: !SessionManager.isDownloadingOllama

            RowLayout {
                anchors.fill: parent
                spacing: 15

                Rectangle {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 16
                    color: Colors.accentColor
                    Layout.alignment: Qt.AlignTop

                    Label {
                        anchors.centerIn: parent
                        text: "ℹ"
                        font.pixelSize: 16
                        font.bold: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5

                    Label {
                        text: "Important Notes:"
                        font.pixelSize: 13
                        font.bold: true
                    }

                    Label {
                        text: "• Ollama is about 600MB and requires an internet connection\n• Your data stays private - all AI processing happens locally\n• The first summary may take longer while the AI model downloads"
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        font.pixelSize: 12
                        opacity: 0.7
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            Button {
                text: "Download Ollama"
                highlighted: true
                enabled: !SessionManager.isDownloadingOllama
                Material.accent: Colors.accentColor
                font.pixelSize: 13
                Layout.preferredHeight: 40
                onClicked: SessionManager.downloadOllama()
            }
        }
    }

    Connections {
        target: SessionManager
        function onOllamaInstallationDetected() {
            setupWindow.setupCompleted()
            setupWindow.close()
        }
    }
}
