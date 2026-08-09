pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    property var backend
    property var voice
    property var messageModel
    property color ink: "#18212f"
    property color panel: "#fbfcff"
    property color line: "#d9e2ef"

    signal sendTextRequested(string text)

    width: 620
    height: 640
    minimumWidth: 520
    minimumHeight: 520
    visible: false
    color: "#f5f7fb"
    title: "Mimo Chat"
    flags: Qt.Window | Qt.WindowStaysOnTopHint

    onVisibleChanged: {
        if (visible) {
            Qt.callLater(root.scrollToEnd)
        }
    }

    onClosing: function(close) {
        close.accepted = false
        root.hide()
    }

    function scrollToEnd() {
        if (root.messageModel && root.messageModel.count > 0) {
            messageList.currentIndex = root.messageModel.count - 1
        }
    }

    function requestSend(text) {
        const trimmed = text.trim()
        if (trimmed.length === 0) {
            return
        }
        root.sendTextRequested(trimmed)
    }

    Rectangle {
        anchors.fill: parent
        color: root.panel
        border.color: root.line

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "Mimo"
                        color: root.ink
                        font.pixelSize: 22
                        font.bold: true
                    }

                    Text {
                        text: root.voice ? root.voice.statusText : "Voice ready"
                        color: "#667085"
                        font.pixelSize: 15
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 116
                    Layout.preferredHeight: 14
                    radius: 7
                    color: "#edf2f8"
                    border.color: "#d3deeb"

                    Rectangle {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(6, parent.width * (root.voice ? root.voice.level : 0))
                        height: parent.height
                        radius: 5
                        color: root.voice && root.voice.recording ? "#ff6f9f" : "#65d6a6"
                    }
                }
            }

            ListView {
                id: messageList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 12
                model: root.messageModel

                delegate: Item {
                    id: messageDelegate
                    required property string sender
                    required property string text

                    width: messageList.width
                    height: messageBox.implicitHeight

                    Rectangle {
                        id: messageBox
                        readonly property real maxBubbleWidth: parent.width * 0.86
                        readonly property real horizontalPadding: 22
                        readonly property real verticalPadding: 22

                        width: Math.min(messageText.implicitWidth + horizontalPadding, maxBubbleWidth)
                        implicitHeight: messageText.implicitHeight + verticalPadding
                        height: implicitHeight
                        radius: 16
                        color: messageDelegate.sender === "user" ? "#1f6feb" : messageDelegate.sender === "memory" ? "#eef6ef" : "#fff3c7"
                        border.color: messageDelegate.sender === "memory" ? "#cfe3d2" : "transparent"
                        anchors.right: messageDelegate.sender === "user" ? parent.right : undefined
                        anchors.left: messageDelegate.sender === "user" ? undefined : parent.left

                        Text {
                            id: messageText
                            width: messageBox.width - messageBox.horizontalPadding
                            anchors.centerIn: parent
                            text: messageDelegate.text
                            color: messageDelegate.sender === "user" ? "white" : root.ink
                            font.pixelSize: 17
                            lineHeight: 1.14
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8

                Button {
                    text: "How am I playing?"
                    font.pixelSize: 14
                    onClicked: root.requestSend(text)
                }

                Button {
                    text: "What do you remember?"
                    font.pixelSize: 14
                    onClicked: root.requestSend(text)
                }

                Button {
                    text: "Find a teammate"
                    font.pixelSize: 14
                    onClicked: root.requestSend(text)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: messageInput
                    Layout.fillWidth: true
                    placeholderText: "Talk to Mimo"
                    font.pixelSize: 17
                    selectByMouse: true
                    background: Rectangle {
                        radius: 16
                        color: "#f5f7fb"
                        border.color: messageInput.activeFocus ? "#7ba7ff" : root.line
                    }
                    onAccepted: sendButton.clicked()
                }

                Button {
                    id: sendButton
                    text: "Send"
                    font.pixelSize: 15
                    enabled: messageInput.text.trim().length > 0
                    onClicked: {
                        root.requestSend(messageInput.text)
                        messageInput.text = ""
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Button {
                    id: holdToTalkButton
                    text: root.voice && root.voice.voiceActivityEnabled
                        ? "Listening"
                        : root.voice && root.voice.recording ? "Talking" : "Hold"
                    font.pixelSize: 15
                    enabled: root.voice && !root.voice.voiceActivityEnabled
                    Layout.fillWidth: true
                    ToolTip.visible: hovered
                    ToolTip.text: root.voice && root.voice.voiceActivityEnabled
                        ? "Voice mode is set in settings"
                        : "Hold to record one voice message"
                    onPressedChanged: {
                        if (!root.voice || root.voice.voiceActivityEnabled) {
                            return
                        }
                        if (pressed) {
                            root.voice.startPushToTalk()
                        } else {
                            root.voice.stopPushToTalk()
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 132
                    Layout.preferredHeight: 34
                    radius: 17
                    color: root.voice && root.voice.voiceActivityEnabled ? "#e8fff3" : "#edf2f8"
                    border.color: root.voice && root.voice.voiceActivityEnabled ? "#9fe2bd" : "#c7d2df"

                    Text {
                        anchors.centerIn: parent
                        text: root.voice && root.voice.voiceActivityEnabled ? "Voice activation" : "Push to talk"
                        color: root.ink
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        width: parent.width - 18
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
