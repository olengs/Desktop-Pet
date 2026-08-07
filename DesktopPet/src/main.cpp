#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QScreen>
#include <QTimer>
#include <QWindow>

#include "backendclient.h"
#include "voicerecorder.h"

namespace {
void showRootWindow(QQmlApplicationEngine *engine)
{
    if (engine->rootObjects().isEmpty()) {
        return;
    }

    auto *window = qobject_cast<QWindow *>(engine->rootObjects().constFirst());
    if (!window) {
        return;
    }

    auto showWindow = [window]() {
        QScreen *screen = window->screen();
        if (!screen) {
            screen = QGuiApplication::primaryScreen();
        }

        if (screen) {
            const QRect available = screen->availableGeometry();
            const QSize size = window->size();
            const int x = qMax(available.left(), available.left() + available.width() - size.width() - 28);
            const int y = qMax(available.top(), available.top() + available.height() - size.height() - 36);
            window->setPosition(x, y);
        }

        window->show();
        window->raise();
        window->requestActivate();
    };

    showWindow();
    QTimer::singleShot(150, window, showWindow);
}
}

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("Garena Pet"));
    QCoreApplication::setOrganizationName(QStringLiteral("GarenaHack"));

    QQuickStyle::setStyle(QStringLiteral("Basic"));

    BackendClient backendClient;
    VoiceRecorder voiceRecorder;
    const QByteArray configuredBackendTarget = qgetenv("GARENA_PET_GRPC_TARGET");
    if (!configuredBackendTarget.isEmpty()) {
        backendClient.setBackendTarget(QString::fromUtf8(configuredBackendTarget));
    }

    QObject::connect(
        &voiceRecorder,
        &VoiceRecorder::recordingFinished,
        &backendClient,
        &BackendClient::uploadVoiceRecording);

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("backendClient"), &backendClient);
    engine.rootContext()->setContextProperty(QStringLiteral("voiceRecorder"), &voiceRecorder);

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);

    engine.loadFromModule(QStringLiteral("GarenaPet"), QStringLiteral("Main"));
    showRootWindow(&engine);
    return app.exec();
}
