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
    
    SystemPalette {
        id: systemPalette
        colorGroup: SystemPalette.Active
    }

    readonly property bool isDarkMode: {
        // Method 1: Qt 6.5+ color scheme detection
        if (typeof Qt.styleHints !== 'undefined' && Qt.styleHints.colorScheme !== undefined) {
            return Qt.styleHints.colorScheme === Qt.Dark
        }

        // Method 2: Fallback - check if window background is darker than text
        const windowColor = systemPalette.window
        const textColor = systemPalette.windowText

        // Calculate luminance of window background
        const r = ((windowColor.r * 255) * 0.299)
        const g = ((windowColor.g * 255) * 0.587)
        const b = ((windowColor.b * 255) * 0.114)
        const luminance = (r + g + b) / 255

        return luminance < 0.5 // Dark if luminance is less than 50%
    }

    readonly property color surfaceColor: isDarkMode ? "#2b2b2b" : "#ffffff"
    readonly property color headerColor: isDarkMode ? "#3a3a3a" : "#cccccc"
    readonly property color headerBorderColor: isDarkMode ? "#2b2b2b" : "#cccccc"
    readonly property color borderColor: isDarkMode ? "#444444" : "#cccccc"
    readonly property color primaryTextColor: isDarkMode ? "#ffffff" : "#000000"
    readonly property color secondaryTextColor: isDarkMode ? "#999999" : "#666666"
    readonly property color tertiaryTextColor: isDarkMode ? "#cccccc" : "#888888"
    readonly property color hoverColor: isDarkMode ? "#404040" : "#f0f0f0"
    readonly property color statusBorderColor: isDarkMode ? "#666666" : "#999999"
    readonly property color placeholderTextColor: isDarkMode ? "#888888" : "#999999"

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
                    color: primaryTextColor
                }
                
                Label {
                    text: "This may take several minutes depending on file size and length..."
                    Layout.fillWidth: true
                    font.pixelSize: 12
                    color: secondaryTextColor
                    visible: recorder ? recorder.isTranscribing : false
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: transcriptDialog.surfaceColor
            radius: 8
            border.color: transcriptDialog.borderColor
            border.width: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 0
                
                Rectangle {
                    Layout.fillWidth: true
                    height: 35
                    color: transcriptDialog.headerColor
                    radius: 4
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        
                        Label {
                            text: "Select"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 60
                            color: primaryTextColor
                        }
                        
                        Label {
                            text: "Recording"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.fillWidth: true
                            color: primaryTextColor
                        }
                        
                        Label {
                            text: "Size"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 45
                            color: primaryTextColor

                        }
                        
                        Label {
                            text: "Status"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.preferredWidth: 60
                            Layout.rightMargin: - 15
                            color: primaryTextColor
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
                        opacity: 0.8
                        visible: recordingsList.count === 0 && recorder && recorder.recordingsModel
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 14
                        color: placeholderTextColor
                    }

                    delegate: Rectangle {
                        width: recordingsList.width
                        height: 50
                        color: mouseArea.containsMouse ? transcriptDialog.hoverColor : "transparent"
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
                                Layout.leftMargin: - 10
                                Layout.rightMargin: 10
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
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    color: primaryTextColor
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Label {
                                        text: name || "Unknown"
                                        Layout.fillWidth: true
                                        font.pixelSize: 10
                                        color: secondaryTextColor
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                            
                            Label {
                                text: size || ""
                                Layout.preferredWidth: 80
                                font.pixelSize: 12
                                color: tertiaryTextColor
                                horizontalAlignment: Text.AlignRight
                            }
                            
                            Rectangle {
                                Layout.preferredWidth: 60
                                height: 20
                                color: hasTranscript ? "#4CAF50" : "transparent"
                                radius: 10
                                border.color: hasTranscript ? "#4CAF50" : statusBorderColor
                                border.width: 1
                                
                                Label {
                                    anchors.centerIn: parent
                                    text: hasTranscript ? "Done" : "Pending"
                                    font.pixelSize: 9
                                    color: hasTranscript ? "white" : secondaryTextColor
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
                        
            Button {
                text: "Launch Summarizer"
                icon.source: "icons/folder.png"
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