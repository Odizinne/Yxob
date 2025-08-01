import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import Odizinne.DNDSummarizer
import "."

ApplicationWindow {
    id: window
    width: 600
    height: mainLyt.implicitHeight + 40
    minimumWidth: 600
    minimumHeight: mainLyt.implicitHeight + 40
    visible: true
    title: "D&D Session Summarizer"
    Material.theme: UserSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor

    property string currentSummary: ""

    ColumnLayout {
        id: mainLyt
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // Folder selection and settings
        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale

            ColumnLayout {
                anchors.fill: parent
                spacing: 20

            RowLayout {
                Layout.fillWidth: true
                spacing: 15

                Item {
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.preferredWidth: 12
                    Layout.preferredHeight: 12
                    radius: 6
                    color: SessionManager.ollamaConnected ? Material.accent : "#f44336"
                }

                Label {
                    text: "D&D Session Summarizer"
                    font.pixelSize: 20
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Label {
                    text: "Session folder:"
                    font.pixelSize: 14
                }

                ComboBox {
                    Layout.fillWidth: true
                    model: SessionManager.folderModel
                    textRole: "display"

                    currentIndex: {
                        if (!SessionManager.folderModel || !SessionManager.currentFolder) {
                            return -1
                        }

                        for (let i = 0; i < SessionManager.folderModel.rowCount(); i++) {
                            let modelIndex = SessionManager.folderModel.index(i, 0)
                            let folderName = SessionManager.folderModel.data(modelIndex, Qt.DisplayRole)
                            if (folderName === SessionManager.currentFolder) {
                                return i
                            }
                        }
                        return -1
                    }

                    onActivated: function(index) {
                        console.log("ComboBox activated with index:", index)
                        if (index >= 0) {
                            let modelIndex = SessionManager.folderModel.index(index, 0)
                            let folderName = SessionManager.folderModel.data(modelIndex, Qt.DisplayRole)
                            console.log("Setting current folder to:", folderName)
                            SessionManager.currentFolder = folderName
                        }
                    }
                }

                Button {
                    text: "Refresh"
                    onClicked: SessionManager.refreshFolders()
                }

                Button {
                    text: "Settings"
                    onClicked: settingsDialog.show()
                }
            }
        }
        }

        // File selection
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Label {
                    text: "Transcript files:"
                    font.pixelSize: 14
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "Select All"
                    onClicked: SessionManager.selectAllFiles(true)
                }

                Button {
                    text: "Deselect All"
                    onClicked: SessionManager.selectAllFiles(false)
                }
            }

            Pane {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 260
                Material.background: Colors.paneColor
                Material.elevation: 6
                Material.roundedScale: Material.ExtraSmallScale
                clip: true

                ListView {
                    id: fileListView
                    anchors.fill: parent
                    anchors.margins: 10
                    model: SessionManager.fileModel

                    delegate: ItemDelegate {
                        width: fileListView.width
                        height: 45

                        onClicked: selCheck.click()

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            spacing: 10

                            CheckBox {
                                id: selCheck
                                Layout.alignment: Qt.AlignVCenter
                                checked: {
                                    if (!SessionManager.fileModel || index < 0) return false
                                    let modelIndex = SessionManager.fileModel.index(index, 1)
                                    return SessionManager.fileModel.data(modelIndex, Qt.CheckStateRole) === Qt.Checked
                                }
                                onToggled: SessionManager.toggleFileSelection(index)
                            }

                            Label {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                text: {
                                    if (!SessionManager.fileModel || index < 0) return ""
                                    let modelIndex = SessionManager.fileModel.index(index, 0)
                                    return SessionManager.fileModel.data(modelIndex, Qt.DisplayRole) || ""
                                }
                            }
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        text: "No files found\n\nSelect a valid session folder."
                        color: Material.hintTextColor
                        visible: fileListView.count === 0
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        // Summary controls
        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale

            RowLayout {
                anchors.fill: parent
                spacing: 15

                Button {
                    text: "Summarize Session"
                    enabled: !SessionManager.isProcessing &&
                             SessionManager.ollamaConnected &&
                             SessionManager.selectedFiles.length > 0
                    highlighted: true

                    onClicked: SessionManager.summarizeSelectedFiles()
                }

                Item { Layout.fillWidth: true }

                Label {
                    text: SessionManager.selectedFiles.length + " file(s) selected"
                    color: Material.hintTextColor
                    font.pixelSize: 12
                }
            }
        }

        // Progress indicator
        Pane {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale
            visible: SessionManager.isProcessing

            RowLayout {
                anchors.centerIn: parent
                spacing: 15

                BusyIndicator {
                    running: SessionManager.isProcessing
                }

                Label {
                    text: SessionManager.processingStatus
                    font.pixelSize: 14
                }
            }
        }
    }

    ApplicationWindow {
        id: settingsDialog
        title: "Prompt Settings"
        width: 700
        height: 620
        minimumWidth: 700
        minimumHeight: 620
        flags: Qt.Dialog
        modality: Qt.ApplicationModal
        Material.theme: UserSettings.darkMode ? Material.Dark : Material.Light
        Material.accent: Colors.accentColor
        Material.primary: Colors.primaryColor
        color: Colors.backgroundColor

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15

            // Header with reset button
            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: "Customize AI Prompts"
                    font.pixelSize: 16
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "Reset to Default"
                    onClicked: SessionManager.resetPromptsToDefault()
                }
            }

            // Chunk Prompt Section
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Label {
                    text: "Chunk Prompt Template"
                    font.pixelSize: 14
                    font.bold: true
                }

                Label {
                    text: "This prompt is used for each individual chunk of text. Use {TEXT} as placeholder for the content to be summarized."
                    font.pixelSize: 12
                    color: Material.hintTextColor
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 150

                    TextArea {
                        id: chunkPromptEdit
                        text: SessionManager.chunkPrompt
                        wrapMode: TextArea.Wrap
                        font.pixelSize: 12
                        selectByMouse: true
                        topInset: 0

                        onTextChanged: {
                            if (text !== SessionManager.chunkPrompt) {
                                SessionManager.chunkPrompt = text
                            }
                        }
                    }
                }
            }

            // Final Prompt Section
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Label {
                    text: "Final Summary Prompt Template"
                    font.pixelSize: 14
                    font.bold: true
                }

                Label {
                    text: "This prompt is used to create the final summary from all chunk summaries. Use {TEXT} as placeholder for the combined chunk summaries."
                    font.pixelSize: 12
                    color: Material.hintTextColor
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 150

                    TextArea {
                        id: finalPromptEdit
                        text: SessionManager.finalPrompt
                        wrapMode: TextArea.Wrap
                        font.pixelSize: 12
                        selectByMouse: true
                        topInset: 0

                        onTextChanged: {
                            if (text !== SessionManager.finalPrompt) {
                                SessionManager.finalPrompt = text
                            }
                        }
                    }
                }
            }

            // Dialog buttons
            RowLayout {
                Layout.fillWidth: true

                Item { Layout.fillWidth: true }

                Button {
                    text: "Close"
                    onClicked: settingsDialog.close()
                }
            }
        }
    }

    // Connections (unchanged)
    Connections {
        target: SessionManager

        function onSummaryReady(summary) {
            currentSummary = summary
            saveDialog.selectedFile = SessionManager.getDefaultSaveFileName()
            saveDialog.open()
        }

        function onErrorOccurred(error) {
            errorDialog.text = error
            errorDialog.open()
        }
    }

    // Save dialog
    FileDialog {
        id: saveDialog
        title: "Save Session Summary"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text files (*.txt)"]
        defaultSuffix: "txt"

        onAccepted: {
            SessionManager.saveNarrativeToFile(selectedFile, currentSummary)
        }
    }

    // Error dialog
    MessageDialog {
        id: errorDialog
        title: "Error"
        buttons: MessageDialog.Ok
    }
}
