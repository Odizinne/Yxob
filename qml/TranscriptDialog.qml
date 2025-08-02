import QtQuick 
import QtQuick.Layouts
import QtQuick.Controls.Material
import "."

ApplicationWindow {
    id: transcriptDialog
    title: "Transcript Recordings"
    width: 600
    height: 500
    minimumWidth: 600
    minimumHeight: 500
    flags: Qt.Dialog
    modality: Qt.ApplicationModal
    Material.theme: YxobSettings.darkMode ? Material.Dark : Material.Light
    Material.accent: Colors.accentColor
    Material.primary: Colors.primaryColor
    color: Colors.backgroundColor
        
    onVisibleChanged: {
        if (recorder && visible) {
            console.log("Refreshing date folders and recordings...")
            recorder.refreshDateFolders()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 15
        
        // Date folder selection
        Pane {
            Layout.fillWidth: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale
            
            RowLayout {
                anchors.fill: parent
                spacing: 10
                
                Label {
                    text: "Session date:"
                    font.pixelSize: 14
                }
                
                ComboBox {
                    Layout.fillWidth: true
                    model: recorder ? recorder.dateFoldersModel : null
                    textRole: "display"
                    
                    currentIndex: {
                        if (!recorder || !recorder.dateFoldersModel || !recorder.currentDateFolder) {
                            return -1
                        }
                        
                        for (let i = 0; i < recorder.dateFoldersModel.rowCount(); i++) {
                            let modelIndex = recorder.dateFoldersModel.index(i, 0)
                            let folderName = recorder.dateFoldersModel.data(modelIndex, Qt.UserRole)
                            if (folderName === recorder.currentDateFolder) {
                                return i
                            }
                        }
                        return -1
                    }
                    
                    onActivated: function(index) {
                        if (recorder && index >= 0) {
                            let modelIndex = recorder.dateFoldersModel.index(index, 0)
                            let folderName = recorder.dateFoldersModel.data(modelIndex, Qt.UserRole)
                            recorder.setCurrentDateFolder(folderName)
                        }
                    }
                }
                
                Button {
                    text: "Refresh"
                    onClicked: {
                        if (recorder) {
                            recorder.refreshDateFolders()
                        }
                    }
                }
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                text: "Select All"
                onClicked: {
                    if (recorder) {
                        recorder.selectAllRecordings(true)
                    }
                }
            }
            
            Button {
                text: "Deselect All"
                onClicked: {
                    if (recorder) {
                        recorder.selectAllRecordings(false)
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: "Delete selected"
                icon.source: "icons/delete.png"
                enabled: recorder ? recorder.hasSelectedRecordings : false
                onClicked: {
                    if (recorder) {
                        recorder.deleteSelectedRecordings()
                    }
                }
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            visible: recorder ? recorder.isTranscribing : false
            spacing: 10
            
            BusyIndicator {
                running: recorder ? recorder.isTranscribing : false
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
            }
            
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5
                
                Label {
                    text: recorder ? recorder.transcriptionStatus : ""
                    Layout.fillWidth: true
                    font.pixelSize: 14
                    font.bold: true
                }
                
                Label {
                    text: "This may take several minutes depending on file size and length..."
                    Layout.fillWidth: true
                    font.pixelSize: 12
                    color: Material.hintTextColor
                    visible: recorder ? recorder.isTranscribing : false
                }
            }
        }
        
        Pane {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Material.background: Colors.paneColor
            Material.elevation: 6
            Material.roundedScale: Material.ExtraSmallScale
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 0
                
                Pane {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 35
                    Material.background: Qt.darker(Colors.paneColor, 1.1)
                    Material.elevation: 2
                    Material.roundedScale: Material.ExtraSmallScale
                    
                    RowLayout {
                        anchors.fill: parent
                        spacing: 10
                        
                        Label {
                            text: "Select"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 60
                        }
                        
                        Label {
                            text: "Recording"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        
                        Label {
                            text: "Size"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 45
                        }
                        
                        Label {
                            text: "Status"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 60
                            Layout.rightMargin: -15
                        }
                    }
                }
                
                ListView {
                    id: recordingsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: recorder ? recorder.recordingsModel : null
                    spacing: 2
                    clip: true
                    
                    Label {
                        anchors.centerIn: parent
                        text: {
                            if (!recorder || !recorder.currentDateFolder) {
                                return "Select a session date to view recordings"
                            }
                            return "No recordings found for this date\n\nRecord some audio first, then return here to transcribe it."
                        }
                        opacity: 0.8
                        visible: recordingsList.count === 0 && recorder && recorder.recordingsModel
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 14
                        color: Material.hintTextColor
                    }

                    delegate: ItemDelegate {
                        width: recordingsList.width
                        height: 50
                        
                        onClicked: {
                            if (recorder) {
                                let currentSelected = selected || false
                                recorder.setRecordingSelected(index, !currentSelected)
                            }
                        }
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 5
                            anchors.rightMargin: 10
                            spacing: 10
                            
                            CheckBox {
                                Layout.preferredWidth: 60
                                Layout.leftMargin: -10
                                Layout.rightMargin: 10
                                checked: selected || false
                                onToggled: {
                                    if (recorder) {
                                        recorder.setRecordingSelected(index, checked)
                                    }
                                }
                            }
                            
                            ColumnLayout {
                                Layout.leftMargin: 5
                                Layout.fillWidth: true
                                spacing: 2

                                Label {
                                    text: {
                                        if (!name) return ""
                                        let filename = name.toString()
                                        let parts = filename.replace("recording_", "").replace(".ogg", "").split("_")
                                        if (parts.length >= 3) {
                                            let date = parts[0]
                                            let time = parts[1]
                                            let user = parts.slice(2).join("_")
                                            return `${date} ${time.slice(0,2)}:${time.slice(2,4)}:${time.slice(4,6)} - ${user}`
                                        }
                                        return filename
                                    }
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Label {
                                        text: name || "Unknown"
                                        Layout.fillWidth: true
                                        font.pixelSize: 10
                                        color: Material.hintTextColor
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                            
                            Label {
                                text: size || ""
                                Layout.preferredWidth: 80
                                font.pixelSize: 12
                                color: Material.hintTextColor
                                horizontalAlignment: Text.AlignRight
                            }
                            
                            Rectangle {
                                Layout.preferredWidth: 60
                                height: 20
                                color: hasTranscript ? Material.accent : "transparent"
                                radius: 10
                                border.color: hasTranscript ? Material.accent : Material.hintTextColor
                                border.width: 1
                                
                                Label {
                                    anchors.centerIn: parent
                                    text: hasTranscript ? "Done" : "Pending"
                                    font.pixelSize: 9
                                    color: hasTranscript ? "white" : Material.hintTextColor
                                    font.bold: hasTranscript
                                }
                            }
                        }
                    }
                    
                    ScrollBar.vertical: ScrollBar {
                        active: true
                        policy: ScrollBar.AsNeeded
                    }
                }
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            spacing: 15
            
            Button {
                text: "Open Recordings Folder"
                icon.source: "icons/folder.png"
                icon.height: 14
                icon.width: 14
                onClicked: {
                    if (recorder) {
                        recorder.openRecordingsFolder()
                    } else {
                        console.log("No recorder available!")
                    }
                }
            }
                        
            Button {
                text: "Launch Summarizer"
                enabled: recorder ? !recorder.isTranscribing : false
                onClicked: {
                    if (recorder) {
                        recorder.launchSummarizer()
                    }
                }
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Start Transcription"
                icon.source: "icons/transcript.png"
                icon.height: 14
                icon.width: 14
                enabled: recorder ? (recorder.hasSelectedRecordings && !recorder.isTranscribing) : false
                highlighted: true
                onClicked: {
                    if (recorder) {
                        recorder.startTranscription()
                    }
                }
            }
        }
    }
}