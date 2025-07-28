import QtQuick 
import QtQuick.Window 
import QtQuick.Controls.FluentWinUI3
import QtQuick.Layouts 

ApplicationWindow {
    id: window
    width: 360
    height: 520  // Increased height to accommodate new controls
    visible: true
    title: "Yxob"
    
    property int recordingSeconds: 0
    property string recordingTime: "00:00"
    
    Timer {
        id: recordingTimer
        interval: 1000
        repeat: true
        onTriggered: {
            recordingSeconds++
            let minutes = Math.floor(recordingSeconds / 60)
            let seconds = recordingSeconds % 60
            let hours = Math.floor(minutes / 60)
            minutes = minutes % 60
            
            if (hours > 0) {
                recordingTime = String(hours).padStart(2, '0') + ":" + 
                               String(minutes).padStart(2, '0') + ":" + 
                               String(seconds).padStart(2, '0')
            } else {
                recordingTime = String(minutes).padStart(2, '0') + ":" + 
                               String(seconds).padStart(2, '0')
            }
        }
    }
    
    TranscriptDialog {
        id: transcriptDialog
    }
    
    header: Rectangle {
        Layout.fillWidth: true
        height: 50
        color: "#1e1e1e"
        border.color: "#333"
        border.width: 1
        
        RowLayout {
            anchors.centerIn: parent
            spacing: 15
            
            Rectangle {
                width: 8
                height: 8
                color: recorder && recorder.isRecording ? "#d13438" : "#666"
                radius: 4
                visible: recorder ? recorder.isRecording : false
                
                SequentialAnimation on opacity {
                    running: recorder ? recorder.isRecording : false
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 800 }
                    NumberAnimation { to: 1.0; duration: 800 }
                }
            }
            
            Label {
                text: recordingTime
                font.pixelSize: 20
                font.bold: true
                font.family: "Consolas, Monaco, monospace"
                color: recorder && recorder.isRecording ? "#ffffff" : "#666"
            }
        }
    }
        
    footer: Rectangle {
        Layout.fillWidth: true
        height: 30
        color: {
            if (recorder && recorder.isRecording) {
                return "#d13438"  // Red when recording
            } else if (recorder && recorder.botConnected) {
                return "#107c10"  // Green when connected
            } else {
                return "#ff8c00"  // Orange when connecting
            }
        }
        
        RowLayout {
            anchors.centerIn: parent
            spacing: 10
            
            Rectangle {
                width: 10
                height: 10
                color: "white"
                radius: 5
                visible: recorder ? recorder.isRecording : false
                
                SequentialAnimation on opacity {
                    running: recorder ? recorder.isRecording : false
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }
            }
            
            Label {
                text: {
                    if (recorder && recorder.isRecording) {
                        return "Recording..."
                    } else if (recorder && recorder.botConnected) {
                        return "Connected!"
                    } else {
                        return "Connecting..."
                    }
                }
                font.pixelSize: 14
                color: "white"
                font.bold: recorder ? recorder.isRecording : false
            }
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15
        
        // Server and Channel selection
        GridLayout {
            Layout.fillWidth: true
            rowSpacing: 10
            columnSpacing: 10
            columns: 2
            //visible: recorder ? recorder.botConnected : false
            
            Label {
                text: "Server"
                font.pixelSize: 14
                font.bold: true
            }

            ComboBox {
                id: guildsCombo
                Layout.fillWidth: true
                textRole: "name"
                model: recorder ? recorder.guildsModel : null
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                
                // Bind currentIndex to the recorder's selectedGuildIndex
                currentIndex: recorder ? recorder.selectedGuildIndex : -1
                
                onActivated: {
                    if (recorder && currentIndex !== recorder.selectedGuildIndex) {
                        recorder.setSelectedGuild(currentIndex)
                    }
                }
                
                // Update currentIndex when the recorder's selection changes
                Connections {
                    target: recorder
                    function onGuildsUpdated() {
                        if (recorder && recorder.selectedGuildIndex >= 0) {
                            guildsCombo.currentIndex = recorder.selectedGuildIndex
                        }
                    }
                }
                
                delegate: ItemDelegate {
                    width: guildsCombo.width
                    text: name
                    highlighted: guildsCombo.highlightedIndex === index
                }
            }
            
            Label {
                text: "Channel"
                font.pixelSize: 14
                font.bold: true
            }
            
            ComboBox {
                id: channelsCombo
                Layout.fillWidth: true
                textRole: "name"
                model: recorder ? recorder.channelsModel : null
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                
                // Bind currentIndex to the recorder's selectedChannelIndex
                currentIndex: recorder ? recorder.selectedChannelIndex : -1
                
                onActivated: {
                    if (recorder && currentIndex !== recorder.selectedChannelIndex) {
                        recorder.setSelectedChannel(currentIndex)
                    }
                }
                
                // Update currentIndex when the recorder's selection changes
                Connections {
                    target: recorder
                    function onChannelsUpdated() {
                        if (recorder && recorder.selectedChannelIndex >= 0) {
                            channelsCombo.currentIndex = recorder.selectedChannelIndex
                        }
                    }
                }
                
                delegate: ItemDelegate {
                    width: channelsCombo.width
                    highlighted: channelsCombo.highlightedIndex === index
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        
                        Label {
                            text: name
                            Layout.fillWidth: true
                            font.pixelSize: 14
                        }
                        
                        Rectangle {
                            Layout.preferredWidth: 25
                            Layout.preferredHeight: 18
                            color: memberCount > 0 ? "#4CAF50" : "#666"
                            radius: 9
                            
                            Label {
                                anchors.centerIn: parent
                                text: memberCount
                                font.pixelSize: 10
                                color: "white"
                                font.bold: true
                            }
                        }
                    }
                }
                
                displayText: currentIndex >= 0 ? currentText + " (" + 
                           (model && model.data ? model.data(model.index(currentIndex, 0), Qt.UserRole + 1) : "0") + 
                           " members)" : "Select channel..."
            }
        }
        
        // Control buttons
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                spacing: 20
                
                Button {
                    Layout.fillWidth: true
                    text: "Start Recording"
                    icon.source: "icons/record.png"
                    enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                    onClicked: {
                        if (recorder) {
                            recorder.startRecording()
                            recordingSeconds = 0
                            recordingTime = "00:00"
                            recordingTimer.start()
                        }
                    }
                }
                
                Button {
                    Layout.fillWidth: true
                    text: "Stop Recording"
                    icon.source: "icons/stop.png"
                    enabled: recorder ? recorder.isRecording : false
                    onClicked: {
                        if (recorder) {
                            recorder.stopRecording()
                            recordingTimer.stop()
                            recordingSeconds = 0
                            recordingTime = "00:00"
                        }
                    }
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#2b2b2b"
            radius: 5
            
            ListView {
                id: usersList
                anchors.fill: parent
                anchors.margins: 10
                model: recorder ? recorder.userModel : null
                spacing: 5
                
                delegate: ItemDelegate {
                    width: usersList.width
                    height: 40
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        
                        Rectangle {
                            width: 12
                            height: 12
                            color: "#4CAF50"
                            radius: 6
                        }
                        
                        Label {
                            text: model.name || ""
                            Layout.fillWidth: true
                            font.pixelSize: 14
                        }
                        
                        Label {
                            text: "Recording"
                            color: "#666"
                            font.pixelSize: 12
                        }
                    }
                }
                
                Label {
                    anchors.centerIn: parent
                    text: "No users being recorded"
                    color: "#999"
                    visible: usersList.count === 0
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                text: "Transcript Recordings"
                icon.source: "icons/transcript.png"
                enabled: recorder ? (recorder.botConnected && !recorder.isRecording) : false
                onClicked: {
                    transcriptDialog.show()
                }
            }
        }
    }
}