import QtQuick 
import QtQuick.Window 
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts 

ApplicationWindow {
    id: transcriptDialog
    title: "Transcript Recordings"
    width: 600
    height: 500
    minimumWidth: 600
    minimumHeight: 500
    flags: Qt.Dialog
    modality: Qt.ApplicationModal
        
    onVisibleChanged: {
        if (recorder && visible) {
            console.log("Refreshing recordings...")
            recorder.refreshRecordings()
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 15
        
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
                    color: "#999"
                    visible: recorder ? recorder.isTranscribing : false
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#2b2b2b"
            radius: 8
            border.color: "#444"
            border.width: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 0
                
                Rectangle {
                    Layout.fillWidth: true
                    height: 35
                    color: "#3a3a3a"
                    radius: 4
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        
                        Label {
                            text: "Select"
                            font.pixelSize: 12
                            font.bold: true
                            color: "#ccc"
                            Layout.preferredWidth: 60
                        }
                        
                        Label {
                            text: "Recording"
                            font.pixelSize: 12
                            font.bold: true
                            color: "#ccc"
                            Layout.fillWidth: true
                        }
                        
                        Label {
                            text: "Size"
                            font.pixelSize: 12
                            font.bold: true
                            color: "#ccc"
                            Layout.preferredWidth: 80
                        }
                        
                        Label {
                            text: "Status"
                            font.pixelSize: 12
                            font.bold: true
                            color: "#ccc"
                            Layout.preferredWidth: 60
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
                        text: "No recordings found\n\nRecord some audio first, then return here to transcribe it."
                        color: "#999"
                        visible: recordingsList.count === 0 && recorder && recorder.recordingsModel
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 14
                    }

                    delegate: Rectangle {
                        width: recordingsList.width
                        height: 50
                        color: mouseArea.containsMouse ? "#404040" : "transparent"
                        radius: 4
                        
                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (recorder) {
                                    let currentSelected = selected || false
                                    recorder.setRecordingSelected(index, !currentSelected)
                                }
                            }
                        }
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10
                            
                            CheckBox {
                                Layout.preferredWidth: 60
                                checked: selected || false
                                onToggled: {
                                    if (recorder) {
                                        recorder.setRecordingSelected(index, checked)
                                    }
                                }
                            }
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                
                                Label {
                                    text: name || "Unknown"
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    color: "#fff"
                                }
                                
                                Label {
                                    text: {
                                        if (!name) return ""
                                        let filename = name.toString()
                                        let parts = filename.replace("recording_", "").replace(".wav", "").split("_")
                                        if (parts.length >= 3) {
                                            let date = parts[0]
                                            let time = parts[1]
                                            let user = parts.slice(2).join("_")
                                            return `${date} ${time.slice(0,2)}:${time.slice(2,4)}:${time.slice(4,6)} - ${user}`
                                        }
                                        return filename
                                    }
                                    Layout.fillWidth: true
                                    font.pixelSize: 10
                                    color: "#999"
                                    elide: Text.ElideRight
                                }
                            }
                            
                            Label {
                                text: size || ""
                                Layout.preferredWidth: 80
                                font.pixelSize: 12
                                color: "#ccc"
                                horizontalAlignment: Text.AlignRight
                            }
                            
                            Rectangle {
                                Layout.preferredWidth: 60
                                height: 20
                                color: hasTranscript ? "#4CAF50" : "transparent"
                                radius: 10
                                border.color: hasTranscript ? "#4CAF50" : "#666"
                                border.width: 1
                                
                                Label {
                                    anchors.centerIn: parent
                                    text: hasTranscript ? "Done" : "Pending"
                                    font.pixelSize: 9
                                    color: hasTranscript ? "white" : "#999"
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
                onClicked: {
                    if (recorder) {
                        recorder.openRecordingsFolder()
                    } else {
                        console.log("No recorder available!")
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: "Start Transcription"
                icon.source: "icons/transcript.png"
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