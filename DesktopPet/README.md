# Garena Pet Desktop MVP

Cross-platform Qt/QML desktop pet prototype for the hackathon MVP. The core app is C++23, QML handles the animated pet layer, and the Python AI backend communicates with the client over gRPC.

## What Is Built

- Transparent always-on-top pet window for macOS and Windows.
- Dragging by grabbing the pet body.
- Compact pet-only mode with idle sleep and disturbed/angry wake behavior.
- QML pet sprite with `idle`, `happy`, `annoyed`, `thinking`, `sit`, `sleep`, and `stretch` poses.
- Chat and settings windows opened from icon buttons around Mimo.
- Player login in settings so each tester can use a separate backend chat-memory key.
- Closing chat/settings leaves Mimo running on the desktop.
- Push-to-talk and voice activity microphone modes.
- C++ gRPC backend client for:
  - direct text send through `SendText`
  - direct WAV voice send through `SendVoice`
  - direct receive through `PullMessages`
  - streaming receive through `SubscribeMessages`
- Text and audio replies from the backend.
- Offline conversational fallback, so the pet can still respond before the backend is running.
- Conversation-only desktop behavior; game data is not sent or simulated by the desktop pet.

## Project Layout

```text
.
|-- CMakeLists.txt
|-- proto
|   `-- garena_pet.proto
|-- qml
|   |-- Main.qml
|   `-- components
|       |-- ChatWindow.qml
|       |-- IconBubbleButton.qml
|       |-- PetBehaviorController.qml
|       |-- PetSprite.qml
|       `-- SettingsWindow.qml
`-- src
    |-- backendclient.cpp
    |-- backendclient.h
    |-- main.cpp
    |-- petgrpcclient.cpp
    |-- petgrpcclient.h
    |-- voicerecorder.cpp
    `-- voicerecorder.h
```

## Requirements

- CMake 3.21+
- Qt 6.5+ with these modules:
  - Qt Quick
  - Qt Quick Controls 2
  - Qt Multimedia
- Local gRPC/protobuf package in `grpc/`.
- A C++23-capable compiler:
  - macOS: Apple Clang through Xcode Command Line Tools
  - Windows: MSVC 2022 or MinGW supported by your Qt install

## Build On macOS

Install Qt 6 through the Qt installer or Homebrew. With Homebrew:

```bash
brew install qt cmake ninja
cmake -S . -B build -G Ninja \
  -DQt6_DIR="$(brew --prefix qt)/lib/cmake/Qt6"
cmake --build build
./bin/GarenaPet
```

If you installed Qt through the Qt installer, point `Qt6_DIR` at your Qt kit's Qt6 CMake package, for example:

```bash
cmake -S . -B build -G Ninja \
  -DQt6_DIR="$HOME/Qt/6.7.2/macos/lib/cmake/Qt6"
cmake --build build
./bin/GarenaPet
```

## Build On Windows

Run from a Developer PowerShell or terminal where CMake can see your compiler:

```powershell
cmake -S . -B build -G Ninja -DQt6_DIR="C:\Qt\6.7.2\msvc2022_64\lib\cmake\Qt6"
cmake --build build
.\bin\GarenaPet.exe
```

Adjust the Qt path to match the kit installed on your machine.

## Backend Configuration

The desktop pet defaults to:

```text
127.0.0.1:50051
```

Override the target with `GARENA_PET_GRPC_TARGET`.

macOS/Linux:

```bash
GARENA_PET_GRPC_TARGET=127.0.0.1:50051 ./bin/GarenaPet
```

The desktop client waits up to the unary gRPC timeout set in `DesktopPet/CMakeLists.txt`. The project currently sets it to 120 seconds, which gives slower Fish TTS responses time to finish. To change it, edit this line in `CMakeLists.txt`, then rerun CMake and rebuild:

```cmake
set(GARENA_PET_GRPC_TIMEOUT_SECONDS 120)
```

Windows PowerShell:

```powershell
$env:GARENA_PET_GRPC_TARGET="127.0.0.1:50051"
.\bin\GarenaPet.exe
```

See [../README.md](../README.md) for the overall architecture and [../GarenaAI/README.md](../GarenaAI/README.md) for the Python gRPC integration.
See [What Is Built](#what-is-built) and [Project Layout](#project-layout) for compact mode and sprite component notes.

Use the settings window's Player Login field to choose a unique player ID before chatting. GarenaAI stores conversation memory by that `player_id`, and the desktop app remembers the selected ID locally between launches.

On macOS, the plain `bin/GarenaPet` executable embeds `NSMicrophoneUsageDescription` at link time. Keep the Apple-specific plist/linker block in `CMakeLists.txt`; without it, Qt cannot load the `QMicrophonePermission` backend for microphone access.

## Backend Contract

The shared protobuf contract lives in [proto/garena_pet.proto](proto/garena_pet.proto).

```proto
service GarenaPetService {
  rpc SendText(TextRequest) returns (PetResponse);
  rpc SendVoice(VoiceRequest) returns (stream PetResponse);
  rpc PullMessages(PullMessagesRequest) returns (MessageBatch);
  rpc SubscribeMessages(SubscribeRequest) returns (stream PetServerMessage);
}
```

`SendVoice` sends completed WAV bytes. The backend streams a transcript response first, then streams the final chat reply after AI generation. Backend responses and streamed messages may include `AudioPayload` bytes plus a MIME type such as `audio/wav` or `audio/mpeg`.

## Demo Flow

1. Launch `GarenaPet`.
2. Drag Mimo to the corner of the screen.
3. Click the chat icon and ask: `How are you?`
4. Hold `Hold` to send a push-to-talk voice note.
5. Click the settings icon to log in with a unique player ID, switch between `Push` and `Listen`, tune voice sensitivity, or click `Pull` for pending backend messages.
6. Confirm the gRPC receive stream is connected; it auto-connects on launch, and the `Stream` button can reconnect it if needed.
7. Close chat/settings and confirm Mimo stays on the desktop.
8. Leave Mimo alone to see the sleep pose, or drag while asleep to briefly annoy Mimo.
