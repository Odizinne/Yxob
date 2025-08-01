#include "sessionmanager.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QFileDialog>
#include <QDateTime>
#include <QRegularExpression>
#include <QDebug>
#include <QStandardPaths>
#include <QFile>
#include <QTextStream>
#include <QEventLoop>
#include <algorithm>

SessionManager* SessionManager::s_instance = nullptr;

SessionManager* SessionManager::create(QQmlEngine *qmlEngine, QJSEngine *jsEngine)
{
    Q_UNUSED(qmlEngine);
    Q_UNUSED(jsEngine);
    return instance();
}

SessionManager* SessionManager::instance()
{
    if (!s_instance) {
        s_instance = new SessionManager();
    }
    return s_instance;
}

SessionManager::SessionManager(QObject *parent)
    : QObject(parent)
    , m_folderModel(new QStringListModel(this))
    , m_fileModel(new QStandardItemModel(this))
    , m_isProcessing(false)
    , m_ollamaModel("mistral:7b-instruct")
    , m_ollamaConnected(false)
    , m_isDownloadingOllama(false)
    , m_downloadProgress(0.0)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_summarizer(new DnDSummarizer(this))
    , m_connectionTimer(new QTimer(this))
    , m_downloadReply(nullptr)
    , m_installerProcess(nullptr)
{
    m_yxobPath = getYxobDataPath();

    m_fileModel->setHorizontalHeaderLabels({"File", "Selected"});
    m_chunkPrompt = getDefaultChunkPrompt();
    m_finalPrompt = getDefaultFinalPrompt();

    connect(m_summarizer, &DnDSummarizer::summaryReady, this, &SessionManager::onSummaryFinished);
    connect(m_summarizer, &DnDSummarizer::errorOccurred, this, &SessionManager::onSummaryError);
    connect(m_summarizer, &DnDSummarizer::progressUpdated, this, &SessionManager::setProcessingStatus);

    m_connectionTimer->setInterval(5000); // Check every 5 seconds
    connect(m_connectionTimer, &QTimer::timeout, this, &SessionManager::checkOllamaConnection);

    refreshFolders();
    checkOllamaConnection();
    m_connectionTimer->start();
}

QString SessionManager::getYxobDataPath() const
{
    QString roamingPath = qEnvironmentVariable("APPDATA");
    if (roamingPath.isEmpty()) {
        QString homePath = QStandardPaths::writableLocation(QStandardPaths::HomeLocation);
        roamingPath = homePath + "/AppData/Roaming";
    }

    qDebug() << "Roaming path:" << roamingPath;

    QString yxobPath = roamingPath + "/Odizinne/Yxob";
    qDebug() << "Target Yxob path:" << yxobPath;

    QDir yxobDir(yxobPath);
    qDebug() << "Yxob directory exists:" << yxobDir.exists();

    if (yxobDir.exists()) {
        QStringList contents = yxobDir.entryList(QDir::AllEntries | QDir::NoDotAndDotDot);
        qDebug() << "Yxob directory contents:" << contents;
    } else {
        qDebug() << "Yxob directory does not exist at:" << yxobPath;
        qDebug() << "Please run the Yxob application first to create session folders.";
    }

    return yxobPath;
}

QString SessionManager::getDefaultChunkPrompt() const
{
    return R"(Résumez cette session de D&D sous forme de récit narratif. Concentrez-vous sur :

- L'histoire et la progression narrative
- Les actions des personnages et leurs conséquences
- Les rencontres importantes (PNJ, monstres, événements)
- Les éléments de roleplay et développement des personnages
- Les découvertes importantes (objets, indices, révélations)
- Les combats et défis mémorables
- Les décisions cruciales prises par le groupe

Rédigez un récit captivant comme si vous racontiez une aventure épique, en gardant les détails importants pour la continuité de la campagne. Environ 250-400 mots, EN FRANÇAIS.

Session D&D :
{TEXT}

Récit de la session :)";
}

QString SessionManager::getDefaultFinalPrompt() const
{
    return R"(Créez un récit final captivant à partir de ces résumés de parties d'une session D&D :

{TEXT}

Rédigez une narration cohérente et engageante qui :
- Raconte l'histoire complète de la session de manière fluide
- Maintient la chronologie des événements
- Préserve tous les détails importants pour la continuité de la campagne
- Met en valeur les moments héroïques et les développements de personnages
- Capture l'esprit de l'aventure et l'ambiance de la table
- Fait environ 500-800 mots
- EST ÉCRIT EN FRANÇAIS sous forme de récit narratif

Récit complet de la session :)";
}

void SessionManager::setChunkPrompt(const QString &prompt)
{
    if (m_chunkPrompt != prompt) {
        m_chunkPrompt = prompt;
        emit chunkPromptChanged();
    }
}

void SessionManager::setFinalPrompt(const QString &prompt)
{
    if (m_finalPrompt != prompt) {
        m_finalPrompt = prompt;
        emit finalPromptChanged();
    }
}

void SessionManager::resetPromptsToDefault()
{
    setChunkPrompt(getDefaultChunkPrompt());
    setFinalPrompt(getDefaultFinalPrompt());
}

void SessionManager::refreshFolders()
{
    QDir yxobDir(m_yxobPath);
    if (!yxobDir.exists()) {
        m_folderModel->setStringList({});
        return;
    }

    QStringList folders;
    static const QRegularExpression datePattern("^\\d{4}-\\d{2}-\\d{2}$");

    QStringList folderList = yxobDir.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const QString &folder : std::as_const(folderList)) {
        if (datePattern.match(folder).hasMatch()) {
            folders.append(folder);
        }
    }

    std::sort(folders.begin(), folders.end(), std::greater<QString>());
    m_folderModel->setStringList(folders);

    if (!folders.isEmpty() && m_currentFolder.isEmpty()) {
        setCurrentFolder(folders.first());
    }
}

void SessionManager::setCurrentFolder(const QString &folder)
{
    qDebug() << "=== setCurrentFolder() called with:" << folder;
    qDebug() << "Previous folder:" << m_currentFolder;

    if (m_currentFolder != folder) {
        qDebug() << "Folder changed from" << m_currentFolder << "to" << folder;
        m_currentFolder = folder;
        m_selectedFiles.clear();

        qDebug() << "Emitting currentFolderChanged signal";
        emit currentFolderChanged();

        qDebug() << "Emitting selectedFilesChanged signal";
        emit selectedFilesChanged();

        qDebug() << "Calling refreshFiles()";
        refreshFiles();

        qDebug() << "setCurrentFolder() completed";
    } else {
        qDebug() << "Folder unchanged:" << folder;
    }
}

void SessionManager::refreshFiles()
{
    qDebug() << "=== refreshFiles() called ===";
    qDebug() << "Current folder:" << m_currentFolder;

    m_fileModel->clear();
    m_fileModel->setHorizontalHeaderLabels({"File", "Selected"});

    if (m_currentFolder.isEmpty()) {
        qDebug() << "Current folder is empty, nothing to do";
        return;
    }

    QString folderPath = m_yxobPath + "/" + m_currentFolder + "/transcripts";
    qDebug() << "Looking for files in transcripts folder:" << folderPath;

    QDir transcriptsDir(folderPath);
    if (!transcriptsDir.exists()) {
        qDebug() << "Transcripts folder does not exist:" << folderPath;

        QString rootFolderPath = m_yxobPath + "/" + m_currentFolder;
        QDir rootDir(rootFolderPath);
        if (rootDir.exists()) {
            QStringList rootFiles = rootDir.entryList({"*.txt"}, QDir::Files);
            qDebug() << "Files in root date folder:" << rootFiles;
        }
        return;
    }

    QStringList allFiles = transcriptsDir.entryList(QDir::Files);
    qDebug() << "ALL files in transcripts folder:" << allFiles;

    QStringList txtFiles = transcriptsDir.entryList({"*.txt"}, QDir::Files);
    qDebug() << "TXT files found in transcripts:" << txtFiles;

    for (const QString &file : std::as_const(txtFiles)) {
        qDebug() << "Adding file to model:" << file;

        QList<QStandardItem*> row;

        QStandardItem* nameItem = new QStandardItem(file);
        nameItem->setFlags(Qt::ItemIsEnabled | Qt::ItemIsSelectable);

        QStandardItem* selectedItem = new QStandardItem();
        selectedItem->setFlags(Qt::ItemIsEnabled | Qt::ItemIsUserCheckable);
        selectedItem->setCheckState(Qt::Unchecked);

        row << nameItem << selectedItem;
        m_fileModel->appendRow(row);
    }

    qDebug() << "File model now has" << m_fileModel->rowCount() << "rows";
}

void SessionManager::toggleFileSelection(int index)
{
    qDebug() << "toggleFileSelection called with index:" << index;

    if (index < 0 || index >= m_fileModel->rowCount()) {
        qDebug() << "Invalid index:" << index << "Row count:" << m_fileModel->rowCount();
        return;
    }

    QModelIndex checkboxIndex = m_fileModel->index(index, 1);
    QModelIndex nameIndex = m_fileModel->index(index, 0);

    if (!checkboxIndex.isValid() || !nameIndex.isValid()) {
        qDebug() << "Invalid model indices";
        return;
    }

    QVariant currentState = m_fileModel->data(checkboxIndex, Qt::CheckStateRole);
    bool isChecked = (currentState.toInt() == Qt::Checked);

    Qt::CheckState newState = isChecked ? Qt::Unchecked : Qt::Checked;
    m_fileModel->setData(checkboxIndex, newState, Qt::CheckStateRole);

    QString fileName = m_fileModel->data(nameIndex, Qt::DisplayRole).toString();
    qDebug() << "Toggling file:" << fileName << "New state:" << (newState == Qt::Checked ? "checked" : "unchecked");

    if (newState == Qt::Checked) {
        if (!m_selectedFiles.contains(fileName)) {
            m_selectedFiles.append(fileName);
        }
    } else {
        m_selectedFiles.removeAll(fileName);
    }

    qDebug() << "Selected files now:" << m_selectedFiles;
    emit selectedFilesChanged();
}

void SessionManager::selectAllFiles(bool select)
{
    m_selectedFiles.clear();

    for (int i = 0; i < m_fileModel->rowCount(); ++i) {
        QModelIndex checkboxIndex = m_fileModel->index(i, 1);
        QModelIndex nameIndex = m_fileModel->index(i, 0);

        if (checkboxIndex.isValid() && nameIndex.isValid()) {
            Qt::CheckState state = select ? Qt::Checked : Qt::Unchecked;
            m_fileModel->setData(checkboxIndex, state, Qt::CheckStateRole);

            if (select) {
                QString fileName = m_fileModel->data(nameIndex, Qt::DisplayRole).toString();
                m_selectedFiles.append(fileName);
            }
        }
    }

    emit selectedFilesChanged();
}

bool SessionManager::checkOllamaInstallation()
{
    QNetworkRequest request(QUrl("http://localhost:11434/api/version"));

    QNetworkReply* reply = m_networkManager->get(request);

    QEventLoop loop;
    connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);

    QTimer timeoutTimer;
    timeoutTimer.setSingleShot(true);
    timeoutTimer.setInterval(3000);
    connect(&timeoutTimer, &QTimer::timeout, &loop, &QEventLoop::quit);
    timeoutTimer.start();

    loop.exec();

    bool isInstalled = (reply->error() == QNetworkReply::NoError);
    reply->deleteLater();

    if (isInstalled) {
        setOllamaConnected(true);
        emit ollamaInstallationDetected();
    }

    return isInstalled;
}

void SessionManager::downloadOllama()
{
    if (m_isDownloadingOllama) {
        return;
    }

    setIsDownloadingOllama(true);
    setDownloadStatus("Downloading Ollama installer...");
    setDownloadProgress(0.0);

    QString tempDir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    m_installerPath = tempDir + "/OllamaSetup.exe";

    QFile::remove(m_installerPath);

    QNetworkRequest request(QUrl("https://ollama.com/download/OllamaSetup.exe"));
    request.setRawHeader("User-Agent", "DNDSummarizer/1.0");

    m_downloadReply = m_networkManager->get(request);

    connect(m_downloadReply, &QNetworkReply::downloadProgress,
            this, &SessionManager::onOllamaDownloadProgress);
    connect(m_downloadReply, &QNetworkReply::finished,
            this, &SessionManager::onOllamaDownloadFinished);
}

void SessionManager::onOllamaDownloadProgress(qint64 bytesReceived, qint64 bytesTotal)
{
    if (bytesTotal > 0) {
        qreal progress = static_cast<qreal>(bytesReceived) / bytesTotal;
        setDownloadProgress(progress);

        double receivedMB = bytesReceived / (1024.0 * 1024.0);
        double totalMB = bytesTotal / (1024.0 * 1024.0);

        setDownloadStatus(QString("Downloading... %1 MB / %2 MB")
                              .arg(receivedMB, 0, 'f', 1)
                              .arg(totalMB, 0, 'f', 1));
    }
}

void SessionManager::onOllamaDownloadFinished()
{
    if (!m_downloadReply) {
        return;
    }

    if (m_downloadReply->error() != QNetworkReply::NoError) {
        setDownloadStatus("Download failed: " + m_downloadReply->errorString());
        setIsDownloadingOllama(false);
        m_downloadReply->deleteLater();
        m_downloadReply = nullptr;
        return;
    }

    QFile file(m_installerPath);
    if (!file.open(QIODevice::WriteOnly)) {
        setDownloadStatus("Failed to save installer");
        setIsDownloadingOllama(false);
        m_downloadReply->deleteLater();
        m_downloadReply = nullptr;
        return;
    }

    file.write(m_downloadReply->readAll());
    file.close();

    m_downloadReply->deleteLater();
    m_downloadReply = nullptr;

    setDownloadProgress(1.0);
    setDownloadStatus("Starting Ollama setup...");

    QTimer::singleShot(500, this, [this]() {
        launchOllamaInstaller();
    });
}

void SessionManager::launchOllamaInstaller()
{
    if (!QFile::exists(m_installerPath)) {
        setDownloadStatus("Installer file not found");
        setIsDownloadingOllama(false);
        return;
    }

    setDownloadStatus("Please complete the Ollama installation...");
    setDownloadProgress(0.0);

    m_installerProcess = new QProcess(this);

    connect(m_installerProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &SessionManager::onOllamaInstallerFinished);

    connect(m_installerProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        QString errorMsg;
        switch (error) {
        case QProcess::FailedToStart:
            errorMsg = "Failed to start installer";
            break;
        case QProcess::Crashed:
            errorMsg = "Installer crashed";
            break;
        default:
            errorMsg = "Installer error occurred";
            break;
        }
        setDownloadStatus(errorMsg);
        setIsDownloadingOllama(false);

        if (m_installerProcess) {
            m_installerProcess->deleteLater();
            m_installerProcess = nullptr;
        }
    });

    qDebug() << "Starting Ollama installer:" << m_installerPath;
    m_installerProcess->start(m_installerPath);

    if (!m_installerProcess->waitForStarted(5000)) {
        setDownloadStatus("Failed to start installer - please run manually");
        setIsDownloadingOllama(false);
        m_installerProcess->deleteLater();
        m_installerProcess = nullptr;
        return;
    }

    qDebug() << "Ollama installer started successfully, waiting for user to complete setup...";
}

void SessionManager::onOllamaInstallerFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    qDebug() << "Ollama installer finished with exit code:" << exitCode << "status:" << exitStatus;

    setDownloadStatus("Installation completed. Checking Ollama...");

    QFile::remove(m_installerPath);

    if (m_installerProcess) {
        m_installerProcess->deleteLater();
        m_installerProcess = nullptr;
    }

    QTimer::singleShot(3000, this, [this]() {
        checkOllamaAfterInstallation(0);
    });
}

void SessionManager::checkOllamaAfterInstallation(int attempt)
{
    const int maxAttempts = 10;
    const int delayMs = 2000;

    qDebug() << "Checking for Ollama installation, attempt" << (attempt + 1) << "of" << maxAttempts;

    if (checkOllamaInstallation()) {
        setDownloadStatus("Ollama installed successfully!");
        setIsDownloadingOllama(false);
        qDebug() << "Ollama installation detected and confirmed";
        return;
    }

    if (attempt < maxAttempts - 1) {
        setDownloadStatus(QString("Waiting for Ollama to start... (%1/%2)")
                              .arg(attempt + 1)
                              .arg(maxAttempts));

        QTimer::singleShot(delayMs, this, [this, attempt]() {
            checkOllamaAfterInstallation(attempt + 1);
        });
    } else {
        setDownloadStatus("Installation complete. Please restart the application if Ollama doesn't appear to be running.");
        setIsDownloadingOllama(false);
        qDebug() << "Max attempts reached, Ollama may need manual start or app restart";
    }
}

void SessionManager::checkOllamaConnection()
{
    QNetworkRequest request(QUrl("http://localhost:11434/api/tags"));
    QNetworkReply* reply = m_networkManager->get(request);

    connect(reply, &QNetworkReply::finished, this, &SessionManager::onOllamaCheckFinished);
}

void SessionManager::onOllamaCheckFinished()
{
    QNetworkReply* reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    bool connected = (reply->error() == QNetworkReply::NoError);
    setOllamaConnected(connected);

    if (!m_isProcessing) {
        if (connected) {
            QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
            QJsonObject rootObject = doc.object();
            QJsonArray models = rootObject["models"].toArray();

            bool modelFound = false;
            for (const QJsonValue &model : std::as_const(models)) {
                QJsonObject modelObject = model.toObject();
                if (modelObject["name"].toString() == m_ollamaModel) {
                    modelFound = true;
                    break;
                }
            }

            if (!modelFound) {
                setProcessingStatus("Model not found");
            } else {
                setProcessingStatus("Ready");
            }
        } else {
            setProcessingStatus("Ollama not connected");
        }
    }

    reply->deleteLater();
}

void SessionManager::pullModelIfNeeded()
{
    setIsProcessing(true);
    setProcessingStatus("Checking model...");

    QNetworkRequest request(QUrl("http://localhost:11434/api/tags"));
    QNetworkReply* reply = m_networkManager->get(request);

    connect(reply, &QNetworkReply::finished, this, &SessionManager::onModelListFinished);
}

void SessionManager::onModelListFinished()
{
    QNetworkReply* reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred("Cannot connect to Ollama");
        setIsProcessing(false);
        reply->deleteLater();
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
    QJsonObject rootObject = doc.object();
    QJsonArray models = rootObject["models"].toArray();

    bool modelFound = false;
    for (const QJsonValue &model : std::as_const(models)) {
        QJsonObject modelObject = model.toObject();
        if (modelObject["name"].toString() == m_ollamaModel) {
            modelFound = true;
            break;
        }
    }

    if (modelFound) {
        setProcessingStatus("Summarizing...");
        m_summarizer->setCustomPrompts(m_chunkPrompt, m_finalPrompt);
        m_summarizer->summarizeFiles(getSelectedFilePaths());
    } else {
        setProcessingStatus("Downloading model...");

        QJsonObject pullRequest;
        pullRequest["name"] = m_ollamaModel;

        QNetworkRequest request(QUrl("http://localhost:11434/api/pull"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

        QNetworkReply* pullReply = m_networkManager->post(request, QJsonDocument(pullRequest).toJson());
        connect(pullReply, &QNetworkReply::finished, this, &SessionManager::onModelPullFinished);
    }

    reply->deleteLater();
}

void SessionManager::onModelPullFinished()
{
    QNetworkReply* reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred("Model download failed");
        setIsProcessing(false);
    } else {
        setProcessingStatus("Summarizing...");
        m_summarizer->setCustomPrompts(m_chunkPrompt, m_finalPrompt);
        m_summarizer->summarizeFiles(getSelectedFilePaths());
    }

    reply->deleteLater();
}

QStringList SessionManager::getSelectedFilePaths() const
{
    QStringList filePaths;
    QString transcriptsFolderPath = m_yxobPath + "/" + m_currentFolder + "/transcripts";

    qDebug() << "Getting selected file paths from:" << transcriptsFolderPath;
    qDebug() << "Selected files:" << m_selectedFiles;

    for (const QString &fileName : std::as_const(m_selectedFiles)) {
        QString fullPath = transcriptsFolderPath + "/" + fileName;
        filePaths.append(fullPath);
        qDebug() << "Added file path:" << fullPath;
    }

    return filePaths;
}

void SessionManager::summarizeSelectedFiles()
{
    if (m_selectedFiles.isEmpty()) {
        emit errorOccurred("No files selected");
        return;
    }

    if (!m_ollamaConnected) {
        emit errorOccurred("Ollama not connected");
        return;
    }

    pullModelIfNeeded();
}

void SessionManager::onSummaryFinished(const QString &summary)
{
    setIsProcessing(false);
    setProcessingStatus("Summary complete");
    emit summaryReady(summary);
}

void SessionManager::onSummaryError(const QString &error)
{
    setIsProcessing(false);
    setProcessingStatus("Error");
    emit errorOccurred(error);
}

void SessionManager::setProcessingStatus(const QString &status)
{
    if (m_processingStatus != status) {
        m_processingStatus = status;
        emit processingStatusChanged();
    }
}

void SessionManager::setIsProcessing(bool processing)
{
    if (m_isProcessing != processing) {
        m_isProcessing = processing;
        emit isProcessingChanged();
    }
}

void SessionManager::setOllamaConnected(bool connected)
{
    if (m_ollamaConnected != connected) {
        m_ollamaConnected = connected;
        emit ollamaConnectedChanged();
    }
}

void SessionManager::setOllamaModel(const QString &model)
{
    if (m_ollamaModel != model) {
        m_ollamaModel = model;
        emit ollamaModelChanged();
    }
}

void SessionManager::setIsDownloadingOllama(bool downloading)
{
    if (m_isDownloadingOllama != downloading) {
        m_isDownloadingOllama = downloading;
        emit isDownloadingOllamaChanged();
    }
}

void SessionManager::setDownloadStatus(const QString &status)
{
    if (m_downloadStatus != status) {
        m_downloadStatus = status;
        emit downloadStatusChanged();
    }
}

void SessionManager::setDownloadProgress(qreal progress)
{
    if (qAbs(m_downloadProgress - progress) > 0.001) {
        m_downloadProgress = progress;
        emit downloadProgressChanged();
    }
}

QString SessionManager::getDefaultSaveFileName() const
{
    QString fileName = "summary-" + m_currentFolder + ".txt";
    return fileName;
}

void SessionManager::saveNarrativeToFile(const QUrl &fileUrl, const QString &summary)
{
    QString filePath = fileUrl.toLocalFile();
    qDebug() << "Saving narrative to:" << filePath;

    QFile file(filePath);
    if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream stream(&file);
        stream.setEncoding(QStringConverter::Utf8);
        stream << summary;
        file.close();

        qDebug() << "File saved successfully";
        setProcessingStatus("Saved successfully");
    } else {
        qDebug() << "Failed to open file for writing:" << file.errorString();
        emit errorOccurred("Failed to save file");
    }
}
