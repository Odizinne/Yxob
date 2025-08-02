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
#include <QProcess>
#include <QThread>
#include <QMessageBox>
#include <QStandardPaths>
#include <QDir>
#include <QCoreApplication>
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

#ifndef Q_OS_WIN
bool isOllamaInstalled()
{
    QProcess checkProcess;
    checkProcess.start("which", QStringList() << "ollama");
    checkProcess.waitForFinished(3000);

    bool installed = (checkProcess.exitCode() == 0);
    qDebug() << "Ollama installed:" << installed;

    if (installed) {
        QString output = checkProcess.readAllStandardOutput().trimmed();
        qDebug() << "Ollama found at:" << output;
    }

    return installed;
}

bool tryStartOllama()
{
    qDebug() << "Attempting to start Ollama...";

    // First check if it's installed
    if (!isOllamaInstalled()) {
        qDebug() << "Ollama is not installed";
        return false;
    }

    // Try to start ollama serve in the background
    QProcess* ollamaProcess = new QProcess();

    // Set up the process to run detached so it continues after our app closes
    QStringList arguments;
    arguments << "serve";

    // Try to start the process
    bool started = ollamaProcess->startDetached("ollama", arguments);

    if (!started) {
        qDebug() << "Failed to start ollama serve";
        ollamaProcess->deleteLater();
        return false;
    }

    qDebug() << "Started ollama serve, waiting for it to be ready...";
    ollamaProcess->deleteLater();

    // Wait for the service to start up and be available
    for (int i = 0; i < 10; ++i) {
        QThread::msleep(1000); // Wait 1 second
        QCoreApplication::processEvents(); // Keep UI responsive

        if (checkOllamaAvailable()) {
            qDebug() << "Ollama is now running after" << (i + 1) << "seconds";
            return true;
        }
    }

    qDebug() << "Ollama failed to start within 10 seconds";
    return false;
}

void showLinuxOllamaHelp()
{
    QString message;

    if (isOllamaInstalled()) {
        message = "Ollama is installed but couldn't be started automatically.\n\n"
                  "Please open a terminal and run:\n"
                  "ollama serve\n\n"
                  "Keep the terminal open and restart this application.";
    } else {
        message = "Ollama is not installed.\n\n"
                  "Please install it first:\n"
                  "curl -fsSL https://ollama.ai/install.sh | sh\n\n"
                  "Then restart this application.";
    }

    QMessageBox::information(nullptr, "Ollama Required", message);
}
#endif

int main(int argc, char *argv[])
{
    qputenv("QT_QUICK_CONTROLS_MATERIAL_VARIANT", "Dense");
    QGuiApplication app(argc, argv);
    app.setWindowIcon(QIcon(":/icons/icon.png"));
    app.setOrganizationName("Odizinne");
    app.setApplicationName("Yxob");
    qmlRegisterUncreatableType<QAbstractItemModel>("QtQml", 2, 0, "QAbstractItemModel", "QAbstractItemModel is abstract");
    QQmlApplicationEngine engine;

    // Check if Ollama is available
    bool ollamaAvailable = checkOllamaAvailable();

#ifndef Q_OS_WIN
    // On Linux, if Ollama isn't running, try to start it
    if (!ollamaAvailable) {
        qDebug() << "Ollama not running on Linux, attempting to start it...";
        ollamaAvailable = tryStartOllama();
    }
#endif

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
        qDebug() << "Loading OllamaSetup interface - Ollama not detected on Windows";
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
        qDebug() << "Could not get Ollama running on Linux";
        showLinuxOllamaHelp();
        return -1;
#endif
    }

    return app.exec();
}
