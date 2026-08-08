pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property string mood: "idle"
    property string pose: mood
    property bool compact: false
    property bool idleBounceEnabled: true
    property url spriteSheetSource: ""
    property url compactIconSource: ""
    property int spriteFrameWidth: 0
    property int spriteFrameHeight: 0
    property int spriteFrameCount: 4
    property int spriteFrameDuration: 120
    property int spriteIdleRow: 0
    property int spriteHappyRow: 1
    property int spriteThinkingRow: 2
    property int spriteAnnoyedRow: 3
    property int spriteSitRow: 4
    property int spriteSleepRow: 5
    property int spriteStretchRow: 6
    readonly property bool hasSpriteSheet: spriteSheetSource.toString().length > 0
        && spriteFrameWidth > 0
        && spriteFrameHeight > 0
    readonly property bool hasCompactIcon: compact
        && compactIconSource.toString().length > 0
        && !hasSpriteSheet
    readonly property bool sleeping: pose === "sleep"
    readonly property bool sitting: pose === "sit"
    readonly property bool stretching: pose === "stretch"
    property color bodyColor: {
        if (sleeping) return "#9bc7ff"
        if (sitting) return "#75d2cf"
        if (stretching) return "#8fe0b0"
        if (mood === "happy") return "#65d6a6"
        if (mood === "annoyed") return "#ff9a7b"
        if (mood === "thinking") return "#83bbff"
        return "#75d2cf"
    }
    property color accentColor: mood === "annoyed" ? "#ffd25a" : "#ff8eb7"

    onMoodChanged: {
        if (mouthCanvas) {
            mouthCanvas.requestPaint()
        }
    }

    onPoseChanged: {
        if (mouthCanvas) {
            mouthCanvas.requestPaint()
        }
    }

    function spriteRowForPose() {
        if (pose === "sit") return spriteSitRow
        if (pose === "sleep") return spriteSleepRow
        if (pose === "stretch") return spriteStretchRow
        if (pose === "happy") return spriteHappyRow
        if (pose === "thinking") return spriteThinkingRow
        if (pose === "annoyed") return spriteAnnoyedRow
        return spriteIdleRow
    }

    AnimatedSprite {
        id: spriteSheetPet
        anchors.fill: parent
        visible: root.hasSpriteSheet
        source: root.spriteSheetSource
        frameWidth: root.spriteFrameWidth
        frameHeight: root.spriteFrameHeight
        frameX: 0
        frameY: root.spriteRowForPose() * root.spriteFrameHeight
        frameCount: Math.max(1, root.spriteFrameCount)
        frameDuration: root.spriteFrameDuration
        interpolate: false
        running: visible
        loops: Animation.Infinite
    }

    Image {
        anchors.fill: parent
        visible: root.hasCompactIcon
        source: root.compactIconSource
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    Item {
        id: petCore
        visible: !root.hasSpriteSheet && !root.hasCompactIcon
        width: parent.width
        height: parent.height
        y: 0
        transformOrigin: Item.Center
        readonly property bool shouldIdleBounce: root.idleBounceEnabled
            && root.mood !== "annoyed"
            && !root.sleeping

        onShouldIdleBounceChanged: {
            if (!shouldIdleBounce) {
                y = 0
            }
        }

        SequentialAnimation on y {
            running: petCore.shouldIdleBounce
            loops: Animation.Infinite
            NumberAnimation { from: root.sitting ? 4 : 2; to: root.sitting ? -2 : -8; duration: root.mood === "happy" ? 520 : 1300; easing.type: Easing.InOutQuad }
            NumberAnimation { from: root.sitting ? -2 : -8; to: root.sitting ? 4 : 2; duration: root.mood === "happy" ? 520 : 1300; easing.type: Easing.InOutQuad }
        }

        SequentialAnimation on rotation {
            running: root.mood === "annoyed"
            loops: Animation.Infinite
            NumberAnimation { from: -4; to: 4; duration: 90; easing.type: Easing.InOutQuad }
            NumberAnimation { from: 4; to: -4; duration: 90; easing.type: Easing.InOutQuad }
        }

        SequentialAnimation on scale {
            running: root.mood === "happy" && !root.compact
            loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 1.045; duration: 360; easing.type: Easing.InOutQuad }
            NumberAnimation { from: 1.045; to: 1.0; duration: 420; easing.type: Easing.InOutQuad }
        }

        Rectangle {
            id: leftEar
            width: parent.width * 0.26
            height: parent.height * 0.26
            radius: width * 0.36
            color: Qt.darker(root.bodyColor, 1.08)
            rotation: root.sleeping ? -36 : root.stretching ? -8 : -23
            anchors.left: body.left
            anchors.leftMargin: 14
            anchors.top: body.top
            anchors.topMargin: root.sleeping ? 4 : -16
        }

        Rectangle {
            width: leftEar.width * 0.48
            height: leftEar.height * 0.48
            radius: width * 0.34
            color: "#ffd9e6"
            rotation: leftEar.rotation
            anchors.centerIn: leftEar
            anchors.horizontalCenterOffset: 5
            anchors.verticalCenterOffset: 5
        }

        Rectangle {
            id: rightEar
            width: leftEar.width
            height: leftEar.height
            radius: leftEar.radius
            color: Qt.darker(root.bodyColor, 1.08)
            rotation: root.sleeping ? 36 : root.stretching ? 8 : 23
            anchors.right: body.right
            anchors.rightMargin: 14
            anchors.top: body.top
            anchors.topMargin: root.sleeping ? 4 : -16
        }

        Rectangle {
            width: rightEar.width * 0.48
            height: rightEar.height * 0.48
            radius: width * 0.34
            color: "#ffd9e6"
            rotation: rightEar.rotation
            anchors.centerIn: rightEar
            anchors.horizontalCenterOffset: -5
            anchors.verticalCenterOffset: 5
        }

        Rectangle {
            id: tail
            width: body.width * 0.34
            height: body.height * 0.22
            radius: height / 2
            color: Qt.darker(root.bodyColor, 1.04)
            border.width: 2
            border.color: "#286c72"
            rotation: root.sleeping ? -24 : root.sitting ? 10 : root.mood === "happy" ? 18 : -8
            anchors.right: body.right
            anchors.rightMargin: -32
            anchors.bottom: body.bottom
            anchors.bottomMargin: 36
        }

        SequentialAnimation {
            running: root.mood === "happy" && !root.compact
            loops: Animation.Infinite
            NumberAnimation { target: tail; property: "rotation"; from: 8; to: 24; duration: 260; easing.type: Easing.InOutQuad }
            NumberAnimation { target: tail; property: "rotation"; from: 24; to: 8; duration: 320; easing.type: Easing.InOutQuad }
        }

        Rectangle {
            id: body
            width: parent.width * (root.sleeping ? 0.88 : root.stretching ? 0.7 : 0.76)
            height: parent.height * (root.sleeping ? 0.46 : root.sitting ? 0.6 : 0.68)
            radius: width * 0.45
            color: root.bodyColor
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.sleeping ? 28 : root.sitting ? 8 : 16
            border.width: 2
            border.color: "#286c72"
        }

        Rectangle {
            width: body.width * 0.6
            height: body.height * 0.52
            radius: width * 0.42
            color: "#f3fff7"
            opacity: 0.78
            anchors.horizontalCenter: body.horizontalCenter
            anchors.bottom: body.bottom
            anchors.bottomMargin: 10
        }

        Rectangle {
            width: body.width * 0.82
            height: body.height * 0.58
            radius: width * 0.42
            color: Qt.lighter(root.bodyColor, 1.1)
            anchors.horizontalCenter: body.horizontalCenter
            anchors.top: body.top
            anchors.topMargin: 20
        }

        Rectangle {
            width: 12
            height: 30
            radius: 6
            color: Qt.lighter(root.bodyColor, 1.18)
            rotation: -16
            anchors.horizontalCenter: body.horizontalCenter
            anchors.top: body.top
            anchors.topMargin: 5
        }

        Rectangle {
            width: 10
            height: 26
            radius: 5
            color: Qt.lighter(root.bodyColor, 1.16)
            rotation: 18
            anchors.horizontalCenter: body.horizontalCenter
            anchors.horizontalCenterOffset: 15
            anchors.top: body.top
            anchors.topMargin: 9
        }

        Rectangle {
            id: leftEye
            width: root.mood === "happy" ? 20 : 17
            height: root.sleeping ? 5 : root.mood === "annoyed" ? 7 : 20
            radius: height / 2
            color: "#16202a"
            anchors.left: body.left
            anchors.leftMargin: root.sleeping ? 54 : 46
            anchors.top: body.top
            anchors.topMargin: root.sleeping ? 46 : root.sitting ? 34 : 58
        }

        Rectangle {
            id: rightEye
            width: root.mood === "happy" ? 20 : 17
            height: root.sleeping ? 5 : root.mood === "annoyed" ? 7 : 18
            radius: height / 2
            color: "#16202a"
            anchors.right: body.right
            anchors.rightMargin: root.sleeping ? 54 : 46
            anchors.top: leftEye.top
        }

        Rectangle {
            visible: root.mood === "annoyed"
            width: 26
            height: 5
            radius: 3
            color: "#16202a"
            rotation: 18
            anchors.horizontalCenter: leftEye.horizontalCenter
            anchors.bottom: leftEye.top
            anchors.bottomMargin: 8
        }

        Rectangle {
            visible: root.mood === "annoyed"
            width: 26
            height: 5
            radius: 3
            color: "#16202a"
            rotation: -18
            anchors.horizontalCenter: rightEye.horizontalCenter
            anchors.bottom: rightEye.top
            anchors.bottomMargin: 8
        }

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: "#ffffff"
            opacity: root.mood === "annoyed" || root.sleeping ? 0 : 0.85
            anchors.right: leftEye.right
            anchors.rightMargin: 3
            anchors.top: leftEye.top
            anchors.topMargin: 3
        }

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: "#ffffff"
            opacity: root.mood === "annoyed" || root.sleeping ? 0 : 0.85
            anchors.right: rightEye.right
            anchors.rightMargin: 3
            anchors.top: rightEye.top
            anchors.topMargin: 3
        }

        Rectangle {
            width: 24
            height: 12
            radius: 6
            color: "#ff7da2"
            opacity: root.mood === "happy" ? 0.78 : 0.42
            anchors.right: leftEye.left
            anchors.rightMargin: 6
            anchors.verticalCenter: leftEye.verticalCenter
            anchors.verticalCenterOffset: 22
        }

        Rectangle {
            width: 24
            height: 12
            radius: 6
            color: "#ff7da2"
            opacity: root.mood === "happy" ? 0.78 : 0.42
            anchors.left: rightEye.right
            anchors.leftMargin: 6
            anchors.verticalCenter: rightEye.verticalCenter
            anchors.verticalCenterOffset: 22
        }

        Canvas {
            id: mouthCanvas
            width: 60
            height: 40
            anchors.horizontalCenter: body.horizontalCenter
            anchors.top: leftEye.bottom
            anchors.topMargin: 8

            onPaint: {
                const ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = "#16202a"
                ctx.lineWidth = 4
                ctx.lineCap = "round"
                ctx.beginPath()

                if (root.sleeping) {
                    ctx.moveTo(22, 22)
                    ctx.quadraticCurveTo(30, 26, 38, 22)
                } else if (root.mood === "happy") {
                    ctx.arc(width / 2, 5, 18, 0.16 * Math.PI, 0.84 * Math.PI)
                } else if (root.mood === "annoyed") {
                    ctx.moveTo(18, 25)
                    ctx.lineTo(42, 25)
                } else if (root.mood === "thinking") {
                    ctx.arc(width / 2, 21, 7, 0, 2 * Math.PI)
                } else {
                    ctx.arc(width / 2, 12, 13, 0.18 * Math.PI, 0.82 * Math.PI)
                }
                ctx.stroke()
            }
        }

        Rectangle {
            width: body.width * 0.5
            height: 12
            radius: 6
            color: root.accentColor
            opacity: root.sleeping ? 0 : 0.92
            anchors.horizontalCenter: body.horizontalCenter
            anchors.top: mouthCanvas.bottom
            anchors.topMargin: 10
        }

        Rectangle {
            width: 28
            height: 28
            radius: 14
            color: "#fff8d9"
            border.width: 2
            border.color: "#e6b852"
            anchors.horizontalCenter: body.horizontalCenter
            anchors.top: mouthCanvas.bottom
            anchors.topMargin: 4
            opacity: root.sleeping ? 0 : 1

            Text {
                anchors.centerIn: parent
                text: "M"
                color: "#6f4a00"
                font.bold: true
                font.pixelSize: 14
            }
        }

        Row {
            visible: root.mood === "thinking" && !root.compact
            spacing: 5
            anchors.left: body.right
            anchors.leftMargin: 4
            anchors.top: body.top
            anchors.topMargin: 18

            Repeater {
                model: 3
                Rectangle {
                    id: thoughtDot
                    required property int index

                    width: 8
                    height: 8
                    radius: 4
                    color: "#ffffff"
                    border.color: "#3874b6"
                    opacity: 0.35

                    SequentialAnimation on opacity {
                        running: root.mood === "thinking"
                        loops: Animation.Infinite
                        PauseAnimation { duration: thoughtDot.index * 130 }
                        NumberAnimation { from: 0.25; to: 1; duration: 260 }
                        NumberAnimation { from: 1; to: 0.25; duration: 360 }
                    }
                }
            }
        }

        Rectangle {
            width: body.width * 0.24
            height: body.height * 0.28
            radius: width * 0.45
            color: Qt.darker(root.bodyColor, 1.05)
            rotation: -18
            anchors.left: body.left
            anchors.leftMargin: -4
            anchors.bottom: body.bottom
            anchors.bottomMargin: 22
        }

        Rectangle {
            width: body.width * 0.24
            height: body.height * 0.28
            radius: width * 0.45
            color: Qt.darker(root.bodyColor, 1.05)
            rotation: 18
            anchors.right: body.right
            anchors.rightMargin: -4
            anchors.bottom: body.bottom
            anchors.bottomMargin: 22
        }

        Rectangle {
            width: 28
            height: 18
            radius: 9
            color: "#f3fff7"
            border.color: "#286c72"
            rotation: -8
            anchors.left: body.left
            anchors.leftMargin: 24
            anchors.bottom: body.bottom
            anchors.bottomMargin: -4
        }

        Rectangle {
            width: 28
            height: 18
            radius: 9
            color: "#f3fff7"
            border.color: "#286c72"
            rotation: 8
            anchors.right: body.right
            anchors.rightMargin: 24
            anchors.bottom: body.bottom
            anchors.bottomMargin: -4
        }

        Canvas {
            id: tinyHeart
            visible: root.mood === "happy" && !root.compact
            width: 28
            height: 26
            anchors.left: body.right
            anchors.leftMargin: 2
            anchors.top: body.top
            anchors.topMargin: -2
            opacity: 0.9

            SequentialAnimation on scale {
                running: root.mood === "happy"
                loops: Animation.Infinite
                NumberAnimation { from: 0.88; to: 1.08; duration: 620; easing.type: Easing.InOutQuad }
                NumberAnimation { from: 1.08; to: 0.88; duration: 720; easing.type: Easing.InOutQuad }
            }

            onPaint: {
                const ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.fillStyle = "#ff6f9f"
                ctx.beginPath()
                ctx.moveTo(14, 23)
                ctx.bezierCurveTo(4, 15, 1, 10, 4, 5)
                ctx.bezierCurveTo(7, 1, 12, 3, 14, 7)
                ctx.bezierCurveTo(16, 3, 21, 1, 24, 5)
                ctx.bezierCurveTo(27, 10, 24, 15, 14, 23)
                ctx.fill()
            }
        }

        Item {
            visible: root.mood === "idle" && !root.compact
            width: 36
            height: 36
            anchors.right: body.right
            anchors.rightMargin: -10
            anchors.top: body.top
            anchors.topMargin: 2
            opacity: 0.72

            Rectangle {
                width: 4
                height: 18
                radius: 2
                color: "#fff8d9"
                anchors.centerIn: parent
            }

            Rectangle {
                width: 18
                height: 4
                radius: 2
                color: "#fff8d9"
                anchors.centerIn: parent
            }
        }

        Column {
            visible: root.sleeping
            spacing: 1
            anchors.left: body.right
            anchors.leftMargin: -6
            anchors.top: body.top
            anchors.topMargin: -14
            opacity: 0.74

            Text {
                text: "Z"
                color: "#4f7fc4"
                font.bold: true
                font.pixelSize: 20
            }

            Text {
                text: "z"
                color: "#4f7fc4"
                font.bold: true
                font.pixelSize: 14
                x: 14
            }
        }
    }
}
