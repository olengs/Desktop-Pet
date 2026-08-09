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

The desktop pet uses database-backed conversation memory when `GARENA_MEMORY_ENABLED=1`. The incoming gRPC `player_id` string is treated as `ai_users.display_name`; `ai_users.user_id` is an internal UUID primary key used by chat and summary tables. Raw chat turns are saved in `ai_chat_messages`; once the unsummarized turn count reaches `GARENA_MEMORY_SUMMARIZE_EVERY_MESSAGES`, GarenaAI asks OpenAI to fold those turns into a new rolling `ai_chat_summaries` row.

```text
GARENA_MEMORY_ENABLED=1
GARENA_MEMORY_SAVE_CHAT_HISTORY=1
GARENA_MEMORY_MAX_CHAT_MESSAGES=8
GARENA_MEMORY_SUMMARIZE_EVERY_MESSAGES=8
GARENA_MEMORY_SUMMARY_MAX_OUTPUT_TOKENS=360
GARENA_MEMORY_MAX_CONTEXT_CHARS=6000
```

`GARENA_MEMORY_MAX_CHAT_MESSAGES` controls the maximum unsummarized recent chat turns included in each reply prompt, fetched by `created_at` descending. The latest rolling summary is also included when present. Each new summary is generated through OpenAI Chat Completions from the previous summary plus the latest unsummarized batch, then inserted as a new `ai_chat_summaries` row. Summarized chat rows are kept for debugging/recovery and marked with `summarized_at`; the desktop gRPC contract still carries conversation data only.

## Optional Audio Replies

Text replies work without TTS, but the demo config currently includes `AudioPayload` responses for desktop playback:

```text
GARENA_PET_GRPC_TTS=1
```

TTS also requires `FISH_AUDIO_API_KEY`.

Fish TTS accepts up to 500 characters per request. GarenaAI normalizes and clamps the spoken text before calling Fish, while the desktop pet displays the regular text reply and plays the returned audio payload.

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
