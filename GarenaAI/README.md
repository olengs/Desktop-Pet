# Garena AI Service

This service exposes the existing pet AI over the desktop pet gRPC contract.

## Run gRPC For Desktop Pet

```bash
cd /Users/jc/Desktop/SMU/CCA_Stuff/GarenaHack/GarenaAI
python -m pip install -r requirements.txt
python main.py
```

The gRPC server defaults to:

```text
127.0.0.1:50051
```

Override the bind address with:

```bash
GARENA_PET_GRPC_BIND=127.0.0.1:50051 python main.py
```

The desktop pet defaults to the same target. To override the pet target:

```bash
GARENA_PET_GRPC_TARGET=127.0.0.1:50051 ./DesktopPet/bin/GarenaPet
```

## Optional Audio Replies

Text replies work without TTS. To include `AudioPayload` responses for desktop playback, set:

```bash
GARENA_PET_GRPC_TTS=1
```

TTS also requires `FISH_AUDIO_API_KEY`.

## Save Incoming WAV Files

To save every WAV clip received from the desktop pet's `SendVoice` call into the repo root `test/` folder, set:

```bash
GARENA_PET_SAVE_WAV=1
```

Saved files use timestamped names like:

```text
test/20260809-104500-demo-player-request-id.wav
```

Saved voice files are normalized to `16 kHz`, `16-bit`, mono WAV before transcription. Fish TTS replies are requested as MP3 at `44.1 kHz` and `128 kbps`.
