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

## Settings Files

Use `.env` only for secrets:

```text
OPENAI_API_KEY=...
FISH_AUDIO_API_KEY=...
GARENA_DB_PASSWORD=...
```

Use `.config` for non-secret runtime settings such as OpenAI model choices, response token budget, Fish TTS format, local debug toggles, and PostgreSQL host/user/database settings.

## PostgreSQL Connection

The AI service loads PostgreSQL settings from `.config` and reads the database password from `.env`. To test the connection without touching `main.py`, run:

```bash
python -m GarenaAI.test_db_connection
```

`pgConnect.json` is still supported as a fallback, but new non-secret DB settings should live in `.config`.

Before using persistent memory, create the tables:

```bash
python -m GarenaAI.initialize_db
```

This runs [initializedb.sql](initializedb.sql) through the same psycopg3 connection settings as the AI service.

To remove the AI chat tables during cleanup, run [destroydb.sql](destroydb.sql) with any Postgres SQL client connected to the same database. It also drops old prototype game/memory tables if they exist.

## Memory Settings

The desktop pet uses database-backed recent chat context when `GARENA_MEMORY_ENABLED=1`. These `.config` values control how much stored conversation is sent to the OpenAI model:

```text
GARENA_MEMORY_ENABLED=1
GARENA_MEMORY_SAVE_CHAT_HISTORY=1
GARENA_MEMORY_MAX_CHAT_MESSAGES=8
GARENA_MEMORY_MAX_CONTEXT_CHARS=6000
```

Lower `GARENA_MEMORY_MAX_CHAT_MESSAGES` to reduce input token cost. The active schema only creates `ai_users` and `ai_chat_messages`; the desktop gRPC contract carries conversation data only.

## Optional Audio Replies

Text replies work without TTS. To include `AudioPayload` responses for desktop playback, set this in `.config`:

```text
GARENA_PET_GRPC_TTS=1
```

TTS also requires `FISH_AUDIO_API_KEY`.

TTS is currently off by default with `GARENA_PET_GRPC_TTS=0`, so the desktop pet receives text replies without waiting for speech synthesis.

For voice messages, `SendVoice` streams a transcript response as soon as STT finishes, then streams the final text/audio reply after AI generation. Text messages still use a single `SendText` response. The desktop client allows up to 25 seconds for each gRPC request.

## Save Incoming WAV Files

To save every WAV clip received from the desktop pet's `SendVoice` call into the repo root `test/` folder, set:

```text
GARENA_PET_SAVE_WAV=1
```

Saved files use timestamped names like:

```text
test/20260809-104500-demo-player-request-id.wav
```

Saved voice files are normalized to `16 kHz`, `16-bit`, mono WAV before transcription. Fish TTS replies are requested as WAV at `44.1 kHz`.

To save Mimo's generated TTS replies in the same `test/` folder, set:

```text
GARENA_PET_SAVE_TTS_WAV=1
FISH_TTS_FORMAT=wav
```
