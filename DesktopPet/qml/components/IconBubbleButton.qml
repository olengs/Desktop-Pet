pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: root

    property string icon: "chat"
    property string tooltipText: ""
    readonly property bool hovered: mouseArea.containsMouse

    signal clicked()

    width: 44
    height: 44
    z: 2

    scale: mouseArea.pressed ? 0.96 : mouseArea.containsMouse ? 1.04 : 1.0

    Behavior on scale {
        NumberAnimation {
            duration: 110
            easing.type: Easing.OutQuad
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: mouseArea.containsMouse ? "#ffffff" : "#f7f9fd"
        border.width: 1
        border.color: mouseArea.containsMouse ? "#8fb7ff" : "#c9d6e6"

        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: width / 2
            color: "transparent"
            border.color: "#ffffff"
            opacity: 0.8
        }
    }

    Canvas {
        id: iconCanvas
        anchors.centerIn: parent
        width: 25
        height: 25

        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "#18212f"
            ctx.fillStyle = "#18212f"
            ctx.lineWidth = 2.2
            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            if (root.icon === "settings") {
                const cx = width / 2
                const cy = height / 2
                for (let i = 0; i < 8; ++i) {
                    const angle = i * Math.PI / 4
                    ctx.beginPath()
                    ctx.moveTo(cx + Math.cos(angle) * 8, cy + Math.sin(angle) * 8)
                    ctx.lineTo(cx + Math.cos(angle) * 10.5, cy + Math.sin(angle) * 10.5)
                    ctx.stroke()
                }
                ctx.beginPath()
                ctx.arc(cx, cy, 7, 0, Math.PI * 2)
                ctx.stroke()
                ctx.beginPath()
                ctx.arc(cx, cy, 2.4, 0, Math.PI * 2)
                ctx.fill()
                return
            }

            ctx.beginPath()
            ctx.moveTo(6, 7)
            ctx.lineTo(19, 7)
            ctx.quadraticCurveTo(22, 7, 22, 10)
            ctx.lineTo(22, 15)
            ctx.quadraticCurveTo(22, 18, 19, 18)
            ctx.lineTo(13, 18)
            ctx.lineTo(8, 22)
            ctx.lineTo(9, 18)
            ctx.lineTo(6, 18)
            ctx.quadraticCurveTo(3, 18, 3, 15)
            ctx.lineTo(3, 10)
            ctx.quadraticCurveTo(3, 7, 6, 7)
            ctx.stroke()
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    ToolTip.visible: root.enabled && mouseArea.containsMouse
    ToolTip.text: root.tooltipText
    ToolTip.delay: 350

    onIconChanged: iconCanvas.requestPaint()
}
