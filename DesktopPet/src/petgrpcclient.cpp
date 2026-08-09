#include "petgrpcclient.h"

#include "garena_pet.grpc.pb.h"

#include <QMetaObject>
#include <QPointer>
#include <QUuid>
#include <QUrl>

#include <grpcpp/channel.h>
#include <grpcpp/client_context.h>
#include <grpcpp/create_channel.h>
#include <grpcpp/security/credentials.h>
#include <grpcpp/support/status.h>

#include <algorithm>
#include <chrono>

namespace {
using garena::pet::v1::AudioPayload;
using garena::pet::v1::GameEventReply;
using garena::pet::v1::GameEventRequest;
using garena::pet::v1::GarenaPetService;
using garena::pet::v1::MessageBatch;
using garena::pet::v1::PetResponse;
using garena::pet::v1::PetServerMessage;
using garena::pet::v1::PlayerContext;
using garena::pet::v1::PullMessagesRequest;
using garena::pet::v1::SubscribeRequest;
using garena::pet::v1::TextRequest;
using garena::pet::v1::TraitScores;
using garena::pet::v1::VoiceRequest;

constexpr int UnaryDeadlineSeconds = 25;

std::string toStdString(const QString &value)
{
    const QByteArray bytes = value.toUtf8();
    return {bytes.constData(), static_cast<std::size_t>(bytes.size())};
}

QString toQString(const std::string &value)
{
    return QString::fromUtf8(value.data(), static_cast<qsizetype>(value.size()));
}

QByteArray toQByteArray(const std::string &value)
{
    return QByteArray(value.data(), static_cast<qsizetype>(value.size()));
}

QString statusMessage(const grpc::Status &status)
{
    const QString detail = toQString(status.error_message());
    if (!detail.isEmpty()) {
        return detail;
    }

    return QStringLiteral("gRPC call failed with code %1").arg(static_cast<int>(status.error_code()));
}

std::string requestId()
{
    return toStdString(QUuid::createUuid().toString(QUuid::WithoutBraces));
}

void applyTraits(TraitScores *target, const PetGrpcClient::TraitSnapshot &traits)
{
    target->set_teamwork(traits.teamwork);
    target->set_aggression(traits.aggression);
    target->set_loyalty(traits.loyalty);
    target->set_leadership(traits.leadership);
    target->set_risk_taking(traits.riskTaking);
}

void applyContext(
    PlayerContext *target,
    const QString &playerId,
    const QStringList &memoryContext,
    const PetGrpcClient::TraitSnapshot &traits)
{
    target->set_player_id(toStdString(playerId));
    for (const QString &memory : memoryContext) {
        target->add_memory_context(toStdString(memory));
    }
    applyTraits(target->mutable_local_traits(), traits);
}

void applyUnaryDeadline(grpc::ClientContext *context)
{
    context->set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(UnaryDeadlineSeconds));
}

QString moodOrDefault(const QString &mood)
{
    return mood.isEmpty() ? QStringLiteral("thinking") : mood;
}

struct MessageParts {
    QString text;
    QString mood;
    QByteArray audio;
    QString audioMimeType;
    bool gameEvent = false;
};

MessageParts partsForMessage(const PetServerMessage &message)
{
    MessageParts parts;
    parts.mood = moodOrDefault(toQString(message.mood()));

    if (message.has_text()) {
        parts.text = toQString(message.text().text());
        return parts;
    }

    if (message.has_audio()) {
        const AudioPayload &audio = message.audio();
        parts.text = toQString(audio.text());
        if (parts.text.isEmpty()) {
            parts.text = toQString(audio.transcript());
        }
        parts.audio = toQByteArray(audio.audio());
        parts.audioMimeType = toQString(audio.mime_type());
        return parts;
    }

    if (message.has_game_event()) {
        parts.text = toQString(message.game_event().summary());
        parts.gameEvent = true;
    }

    return parts;
}

void emitServerMessage(PetGrpcClient *client, const PetServerMessage &message)
{
    const MessageParts parts = partsForMessage(message);
    QMetaObject::invokeMethod(
        client,
        [client, parts]() {
            if (parts.gameEvent) {
                emit client->gameEventAccepted(parts.text, parts.mood);
                return;
            }

            emit client->backendMessageReceived(parts.text, parts.mood, parts.audio, parts.audioMimeType);
        },
        Qt::QueuedConnection);
}

void emitExtraMessages(PetGrpcClient *client, const google::protobuf::RepeatedPtrField<PetServerMessage> &messages)
{
    if (!client) {
        return;
    }

    for (const PetServerMessage &message : messages) {
        emitServerMessage(client, message);
    }
}
}

PetGrpcClient::PetGrpcClient(QObject *parent)
    : QObject(parent)
{
    setTarget(m_target);
}

PetGrpcClient::~PetGrpcClient()
{
    disconnectMessageStream();
}

QString PetGrpcClient::target() const
{
    std::lock_guard lock(m_channelMutex);
    return m_target;
}

QString PetGrpcClient::normalizeTarget(QString target)
{
    target = target.trimmed();
    if (target.isEmpty()) {
        return QStringLiteral("127.0.0.1:50051");
    }

    if (target.startsWith(QStringLiteral("grpc://"))) {
        target.remove(0, 7);
    }

    const QUrl url(target);
    if (url.isValid() && !url.scheme().isEmpty() && !url.host().isEmpty()) {
        const int port = url.port(50051);
        return QStringLiteral("%1:%2").arg(url.host()).arg(port);
    }

    return target;
}

void PetGrpcClient::setTarget(const QString &target)
{
    const QString normalized = normalizeTarget(target);

    std::lock_guard lock(m_channelMutex);
    if (m_target == normalized && m_channel) {
        return;
    }

    m_target = normalized;
    m_channel = grpc::CreateChannel(toStdString(m_target), grpc::InsecureChannelCredentials());
}

bool PetGrpcClient::streamConnected() const
{
    return m_streamConnected.load();
}

void PetGrpcClient::sendText(
    const QString &playerId,
    const QString &message,
    const QStringList &memoryContext,
    const TraitSnapshot &traits)
{
    const QPointer<PetGrpcClient> self(this);
    const auto grpcChannel = channel();

    std::thread([self, grpcChannel, playerId, message, memoryContext, traits]() {
        if (!self || !grpcChannel) {
            return;
        }

        TextRequest request;
        request.set_request_id(requestId());
        request.set_message(toStdString(message));
        applyContext(request.mutable_context(), playerId, memoryContext, traits);

        PetResponse response;
        grpc::ClientContext context;
        applyUnaryDeadline(&context);
        const grpc::Status status = GarenaPetService::NewStub(grpcChannel)->SendText(&context, request, &response);

        if (!self) {
            return;
        }

        if (!status.ok()) {
            const QString error = statusMessage(status);
            QMetaObject::invokeMethod(
                self,
                [self, message, error]() {
                    emit self->textRequestFailed(message, error);
                },
                Qt::QueuedConnection);
            return;
        }

        const QString reply = toQString(response.reply());
        const QString mood = moodOrDefault(toQString(response.mood()));
        const QByteArray audio = response.has_audio() ? toQByteArray(response.audio().audio()) : QByteArray();
        const QString audioMimeType = response.has_audio() ? toQString(response.audio().mime_type()) : QString();

        QMetaObject::invokeMethod(
            self,
            [self, reply, mood, audio, audioMimeType]() {
                emit self->textReplyReceived(reply, mood, audio, audioMimeType);
            },
            Qt::QueuedConnection);

        emitExtraMessages(self, response.extra_messages());
    }).detach();
}

void PetGrpcClient::sendVoice(
    const QString &playerId,
    const QByteArray &wavData,
    int durationMs,
    const QString &mode,
    const QStringList &memoryContext,
    const TraitSnapshot &traits)
{
    const QPointer<PetGrpcClient> self(this);
    const auto grpcChannel = channel();

    std::thread([self, grpcChannel, playerId, wavData, durationMs, mode, memoryContext, traits]() {
        if (!self || !grpcChannel) {
            return;
        }

        VoiceRequest request;
        request.set_request_id(requestId());
        applyContext(request.mutable_context(), playerId, memoryContext, traits);
        request.set_wav_audio(std::string(wavData.constData(), static_cast<std::size_t>(wavData.size())));
        request.set_duration_ms(durationMs);
        request.set_mode(toStdString(mode));
        request.set_mime_type("audio/wav");

        PetResponse response;
        grpc::ClientContext context;
        applyUnaryDeadline(&context);
        const grpc::Status status = GarenaPetService::NewStub(grpcChannel)->SendVoice(&context, request, &response);

        if (!self) {
            return;
        }

        if (!status.ok()) {
            const QString error = statusMessage(status);
            QMetaObject::invokeMethod(
                self,
                [self, error]() {
                    emit self->voiceRequestFailed(error);
                },
                Qt::QueuedConnection);
            return;
        }

        const QString transcript = toQString(response.transcript());
        const QString reply = toQString(response.reply());
        const QString mood = moodOrDefault(toQString(response.mood()));
        const QByteArray audio = response.has_audio() ? toQByteArray(response.audio().audio()) : QByteArray();
        const QString audioMimeType = response.has_audio() ? toQString(response.audio().mime_type()) : QString();

        QMetaObject::invokeMethod(
            self,
            [self, transcript, reply, mood, audio, audioMimeType]() {
                emit self->voiceReplyReceived(transcript, reply, mood, audio, audioMimeType);
            },
            Qt::QueuedConnection);

        emitExtraMessages(self, response.extra_messages());
    }).detach();
}

void PetGrpcClient::sendGameEvent(
    const QString &playerId,
    const QString &game,
    const QString &eventType,
    const QString &summary,
    const TraitSnapshot &impact)
{
    const QPointer<PetGrpcClient> self(this);
    const auto grpcChannel = channel();

    std::thread([self, grpcChannel, playerId, game, eventType, summary, impact]() {
        if (!self || !grpcChannel) {
            return;
        }

        GameEventRequest request;
        request.set_request_id(requestId());
        request.mutable_context()->set_player_id(toStdString(playerId));
        request.set_game(toStdString(game));
        request.set_event_type(toStdString(eventType));
        request.set_summary(toStdString(summary));
        applyTraits(request.mutable_impact(), impact);

        GameEventReply response;
        grpc::ClientContext context;
        applyUnaryDeadline(&context);
        const grpc::Status status = GarenaPetService::NewStub(grpcChannel)->SendGameEvent(&context, request, &response);

        if (!self) {
            return;
        }

        if (!status.ok()) {
            const QString error = statusMessage(status);
            QMetaObject::invokeMethod(
                self,
                [self, summary, error]() {
                    emit self->gameEventRequestFailed(summary, error);
                },
                Qt::QueuedConnection);
            return;
        }

        const QString acceptedSummary = toQString(response.summary()).isEmpty()
            ? summary
            : toQString(response.summary());
        const QString mood = moodOrDefault(toQString(response.mood()));
        QMetaObject::invokeMethod(
            self,
            [self, acceptedSummary, mood]() {
                emit self->gameEventAccepted(acceptedSummary, mood);
            },
            Qt::QueuedConnection);

        emitExtraMessages(self, response.extra_messages());
    }).detach();
}

void PetGrpcClient::pullMessages(const QString &playerId, int maxMessages)
{
    const QPointer<PetGrpcClient> self(this);
    const auto grpcChannel = channel();
    maxMessages = std::clamp(maxMessages, 1, 50);

    std::thread([self, grpcChannel, playerId, maxMessages]() {
        if (!self || !grpcChannel) {
            return;
        }

        PullMessagesRequest request;
        request.set_player_id(toStdString(playerId));
        request.set_max_messages(maxMessages);

        MessageBatch response;
        grpc::ClientContext context;
        applyUnaryDeadline(&context);
        const grpc::Status status = GarenaPetService::NewStub(grpcChannel)->PullMessages(&context, request, &response);

        if (!self) {
            return;
        }

        if (!status.ok()) {
            const QString error = statusMessage(status);
            QMetaObject::invokeMethod(
                self,
                [self, error]() {
                    emit self->pullMessagesFailed(error);
                },
                Qt::QueuedConnection);
            return;
        }

        for (const PetServerMessage &message : response.messages()) {
            emitServerMessage(self, message);
        }

        const int count = response.messages_size();
        QMetaObject::invokeMethod(
            self,
            [self, count]() {
                emit self->pullMessagesFinished(count);
            },
            Qt::QueuedConnection);
    }).detach();
}

void PetGrpcClient::connectMessageStream(const QString &playerId)
{
    if (m_streamThread.joinable()) {
        if (m_streamConnected.load()) {
            return;
        }
        disconnectMessageStream();
    }

    m_streamStopRequested.store(false);
    const QPointer<PetGrpcClient> self(this);
    const auto grpcChannel = channel();

    m_streamThread = std::thread([this, self, grpcChannel, playerId]() {
        if (!self || !grpcChannel) {
            return;
        }

        auto context = std::make_unique<grpc::ClientContext>();
        grpc::ClientContext *rawContext = context.get();
        {
            std::lock_guard lock(m_streamMutex);
            m_streamContext = std::move(context);
        }

        SubscribeRequest request;
        request.set_player_id(toStdString(playerId));
        request.add_accepted_mime_types("audio/wav");
        request.add_accepted_mime_types("audio/mpeg");

        auto reader = GarenaPetService::NewStub(grpcChannel)->SubscribeMessages(rawContext, request);
        if (self) {
            QMetaObject::invokeMethod(
                self,
                [self]() {
                    self->setStreamConnected(true);
                },
                Qt::QueuedConnection);
        }

        PetServerMessage message;
        while (!m_streamStopRequested.load() && reader->Read(&message)) {
            if (!self) {
                break;
            }
            emitServerMessage(self, message);
        }

        const grpc::Status status = reader->Finish();
        {
            std::lock_guard lock(m_streamMutex);
            m_streamContext.reset();
        }

        if (self) {
            QMetaObject::invokeMethod(
                self,
                [self]() {
                    self->setStreamConnected(false);
                },
                Qt::QueuedConnection);

            if (!m_streamStopRequested.load() && !status.ok()) {
                const QString error = statusMessage(status);
                QMetaObject::invokeMethod(
                    self,
                    [self, error]() {
                        emit self->streamFailed(error);
                    },
                    Qt::QueuedConnection);
            }
        }
    });
}

void PetGrpcClient::disconnectMessageStream()
{
    m_streamStopRequested.store(true);
    {
        std::lock_guard lock(m_streamMutex);
        if (m_streamContext) {
            m_streamContext->TryCancel();
        }
    }

    if (m_streamThread.joinable()) {
        m_streamThread.join();
    }

    setStreamConnected(false);
}

std::shared_ptr<grpc::Channel> PetGrpcClient::channel() const
{
    std::lock_guard lock(m_channelMutex);
    return m_channel;
}

void PetGrpcClient::setStreamConnected(bool connected)
{
    if (m_streamConnected.exchange(connected) == connected) {
        return;
    }

    emit streamConnectedChanged(connected);
}
