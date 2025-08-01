#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QIcon>
#include <QAbstractItemModel>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QEventLoop>
#include <QTimer>
#include <QDebug>
#include "sessionmanager.h"

bool checkOllamaAvailable()
{
    QNetworkAccessManager manager;
    QNetworkRequest request(QUrl("http://localhost:11434/api/version"));
    request.setTransferTimeout(2000); // 2 second timeout

    QNetworkReply* reply = manager.get(request);

    QEventLoop loop;
    bool timedOut = false;

    // Connect reply finished signal
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);

    // Create timeout timer
    QTimer timeoutTimer;
    timeoutTimer.setSingleShot(true);
    timeoutTimer.setInterval(2000); // 2 seconds timeout
    QObject::connect(&timeoutTimer, &QTimer::timeout, [&loop, &timedOut]() {
        timedOut = true;
        loop.quit();
    });

    timeoutTimer.start();
    loop.exec();

    bool available = false;

    if (timedOut) {
        qDebug() << "Ollama check timed out";
        reply->abort();
        available = false;
    } else {
        // Check for successful response
        if (reply->error() == QNetworkReply::NoError) {
            // Also verify we got a reasonable response
            QByteArray response = reply->readAll();
            available = !response.isEmpty();
            qDebug() << "Ollama responded successfully:" << response;
        } else {
            qDebug() << "Ollama connection error:" << reply->errorString();
            available = false;
        }
    }

    reply->deleteLater();
    qDebug() << "Ollama available:" << available;
    return available;
}

int main(int argc, char *argv[])
{
    qputenv("QT_QUICK_CONTROLS_MATERIAL_VARIANT", "Dense");
    QGuiApplication app(argc, argv);
    app.setWindowIcon(QIcon(":/icons/icon.png"));
    app.setOrganizationName("Odizinne");
    app.setApplicationName("DNDSummarizer");
    qmlRegisterUncreatableType<QAbstractItemModel>("QtQml", 2, 0, "QAbstractItemModel", "QAbstractItemModel is abstract");
    QQmlApplicationEngine engine;

    // Check if Ollama is available
    bool ollamaAvailable = checkOllamaAvailable();

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);

    if (ollamaAvailable) {
        qDebug() << "Loading Main interface - Ollama is available";
        engine.loadFromModule("Odizinne.DNDSummarizer", "Main");
    } else {
#ifdef Q_OS_WIN
        qDebug() << "Loading OllamaSetup interface - Ollama not detected";
        // Load setup window instead
        engine.loadFromModule("Odizinne.DNDSummarizer", "OllamaSetup");
        // Connect to SessionManager's signal instead of trying to connect to QML object
        SessionManager* sessionManager = SessionManager::instance();
        QObject::connect(sessionManager, &SessionManager::ollamaInstallationDetected, &engine, [&engine]() {
            qDebug() << "Ollama installation detected, switching to Main interface";
            engine.clearComponentCache();
            engine.loadFromModule("Odizinne.DNDSummarizer", "Main");
        });
#else
        qDebug() << "Ollama could not be found in path";
        return -1;
#endif
    }

    return app.exec();
}
