pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    property var backend
    property var voice
    property color ink: "#18212f"
    property color panel: "#fbfcff"
    property color line: "#d9e2ef"

    width: 430
    height: 640
    minimumWidth: 390
    minimumHeight: 580
    visible: false
    color: "#f5f7fb"
    title: "Mimo Settings"
    flags: Qt.Window | Qt.WindowStaysOnTopHint

    onVisibleChanged: {
        if (visible) {
            refreshFields()
        }
    }

    onClosing: function(close) {
        close.accepted = false
        root.hide()
    }

    function refreshFields() {
        if (root.backend) {
            backendTargetInput.text = root.backend.backendTarget
            playerIdInput.text = root.backend.playerId
        }
    }

    function normalizedPlayerId(value) {
        const trimmed = value.trim()
        return trimmed.length === 0 ? "demo-player" : trimmed
    }

    function loginPlayer() {
        if (!root.backend) {
            return
        }

        root.backend.playerId = normalizedPlayerId(playerIdInput.text)
        playerIdInput.text = root.backend.playerId
    }

    Connections {
        target: root.backend

        function onPlayerIdChanged() {
            if (root.visible) {
                playerIdInput.text = root.backend.playerId
            }
        }

        function onBackendTargetChanged() {
            if (root.visible) {
                backendTargetInput.text = root.backend.backendTarget
            }
        }
    }

    function setVoiceActivityMode(enabled) {
        if (!root.voice || root.voice.voiceActivityEnabled === enabled) {
            return
        }

        if (enabled) {
            root.voice.startVoiceActivity()
        } else {
            root.voice.stopVoiceActivity()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.panel
        border.color: root.line

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            Text {
                text: "Mimo Settings"
                color: root.ink
                font.pixelSize: 22
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                radius: 8
                color: root.backend && root.backend.online ? "#e8fff3" : "#fff7e6"
                border.color: root.backend && root.backend.online ? "#9fe2bd" : "#ffd18a"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 8
                        Layout.preferredHeight: 8
                        radius: 4
                        color: root.backend && root.backend.online ? "#1fa760" : "#d58b19"
                    }

                    Text {
                        text: root.backend ? root.backend.statusText : "Backend unavailable"
                        color: root.ink
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }

            Text {
                text: "Player Login"
                color: root.ink
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: playerIdInput
                    Layout.fillWidth: true
                    font.pixelSize: 14
                    placeholderText: "player-id"
                    selectByMouse: true
                    onAccepted: loginButton.clicked()
                }

                Button {
                    id: loginButton
                    text: root.backend && root.backend.playerId === root.normalizedPlayerId(playerIdInput.text) ? "Signed In" : "Login"
                    enabled: root.backend
                        && playerIdInput.text.trim().length > 0
                        && root.backend.playerId !== root.normalizedPlayerId(playerIdInput.text)
                    Layout.preferredWidth: 96
                    font.pixelSize: 14
                    onClicked: root.loginPlayer()
                }

                Button {
                    text: "Demo"
                    Layout.preferredWidth: 82
                    font.pixelSize: 14
                    ToolTip.visible: hovered
                    ToolTip.text: "Use demo-player"
                    onClicked: {
                        playerIdInput.text = "demo-player"
                        root.loginPlayer()
                    }
                }
            }

            Text {
                text: root.backend ? "Signed in as " + root.backend.playerId : "Not signed in"
                color: "#667085"
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.line
            }

            Text {
                text: "Connection"
                color: root.ink
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: backendTargetInput
                    Layout.fillWidth: true
                    font.pixelSize: 14
                    placeholderText: "127.0.0.1:50051"
                    selectByMouse: true
                    onAccepted: applyBackendButton.clicked()
                }

                Button {
                    id: applyBackendButton
                    text: "Apply"
                    Layout.preferredWidth: 90
                    font.pixelSize: 14
                    onClicked: {
                        if (root.backend) {
                            root.backend.backendTarget = backendTargetInput.text
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Button {
                    text: "Pull"
                    Layout.fillWidth: true
                    ToolTip.visible: hovered
                    ToolTip.text: "Pull pending gRPC messages"
                    onClicked: {
                        if (root.backend) {
                            root.backend.pullMessages()
                        }
                    }
                }

                Button {
                    text: root.backend && root.backend.streamConnected ? "Stop Stream" : "Stream"
                    Layout.fillWidth: true
                    ToolTip.visible: hovered
                    ToolTip.text: root.backend && root.backend.streamConnected ? "Disconnect gRPC receive stream" : "Connect gRPC receive stream"
                    onClicked: {
                        if (!root.backend) {
                            return
                        }
                        if (root.backend.streamConnected) {
                            root.backend.disconnectMessageStream()
                        } else {
                            root.backend.connectMessageStream()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.line
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Voice mode"
                    color: "#667085"
                    font.pixelSize: 14
                    Layout.preferredWidth: 112
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        id: pushModeButton
                        text: "Push"
                        checkable: true
                        checked: root.voice ? !root.voice.voiceActivityEnabled : true
                        Layout.fillWidth: true
                        ToolTip.visible: hovered
                        ToolTip.text: "Use hold-to-talk in chat"
                        onClicked: root.setVoiceActivityMode(false)
                    }

                    Button {
                        id: listenModeButton
                        text: "Listen"
                        checkable: true
                        checked: root.voice ? root.voice.voiceActivityEnabled : false
                        Layout.fillWidth: true
                        ToolTip.visible: hovered
                        ToolTip.text: "Use voice activity detection"
                        onClicked: root.setVoiceActivityMode(true)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Voice sensitivity"
                    color: "#667085"
                    font.pixelSize: 14
                    Layout.preferredWidth: 112
                }

                Slider {
                    from: 0.04
                    to: 0.2
                    value: root.voice ? root.voice.vadThreshold : 0.08
                    enabled: root.voice && root.voice.voiceActivityEnabled
                    Layout.fillWidth: true
                    onMoved: {
                        if (root.voice) {
                            root.voice.vadThreshold = value
                        }
                    }
                }
            }

            Item {
                Layout.fillHeight: true
            }

            Button {
                text: "Close"
                Layout.alignment: Qt.AlignRight
                onClicked: root.hide()
            }
        }
    }
}
