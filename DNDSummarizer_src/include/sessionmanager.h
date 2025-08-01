#pragma once

#include <QObject>
#include <QStringListModel>
#include <QStandardItemModel>
#include <QAbstractItemModel>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTimer>
#include <QFileInfo>
#include <QDir>
#include <QStandardPaths>
#include <QQmlEngine>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include "dndsummarizer.h"

class SessionManager : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

    Q_PROPERTY(QAbstractItemModel* folderModel READ folderModel CONSTANT)
    Q_PROPERTY(QAbstractItemModel* fileModel READ fileModel CONSTANT)
    Q_PROPERTY(QString currentFolder READ currentFolder WRITE setCurrentFolder NOTIFY currentFolderChanged)
    Q_PROPERTY(bool isProcessing READ isProcessing NOTIFY isProcessingChanged)
    Q_PROPERTY(QString processingStatus READ processingStatus NOTIFY processingStatusChanged)
    Q_PROPERTY(QString ollamaModel READ ollamaModel WRITE setOllamaModel NOTIFY ollamaModelChanged)
    Q_PROPERTY(bool ollamaConnected READ ollamaConnected NOTIFY ollamaConnectedChanged)
    Q_PROPERTY(QStringList selectedFiles READ selectedFiles NOTIFY selectedFilesChanged)
    Q_PROPERTY(QString chunkPrompt READ chunkPrompt WRITE setChunkPrompt NOTIFY chunkPromptChanged)
    Q_PROPERTY(QString finalPrompt READ finalPrompt WRITE setFinalPrompt NOTIFY finalPromptChanged)

public:
    static SessionManager* create(QQmlEngine *qmlEngine, QJSEngine *jsEngine);
    static SessionManager* instance();

    QAbstractItemModel* folderModel() const { return m_folderModel; }
    QAbstractItemModel* fileModel() const { return m_fileModel; }

    QString currentFolder() const { return m_currentFolder; }
    void setCurrentFolder(const QString &folder);

    bool isProcessing() const { return m_isProcessing; }
    QString processingStatus() const { return m_processingStatus; }

    QString ollamaModel() const { return m_ollamaModel; }
    void setOllamaModel(const QString &model);

    bool ollamaConnected() const { return m_ollamaConnected; }
    QStringList selectedFiles() const { return m_selectedFiles; }

    QString chunkPrompt() const { return m_chunkPrompt; }
    void setChunkPrompt(const QString &prompt);

    QString finalPrompt() const { return m_finalPrompt; }
    void setFinalPrompt(const QString &prompt);

public slots:
    void refreshFolders();
    void refreshFiles();
    void checkOllamaConnection();
    void pullModelIfNeeded();
    void summarizeSelectedFiles();
    void saveNarrativeToFile(const QUrl &fileUrl, const QString &summary);
    void toggleFileSelection(int index);
    void selectAllFiles(bool select);
    void resetPromptsToDefault();
    QString getDefaultSaveFileName() const;

signals:
    void currentFolderChanged();
    void isProcessingChanged();
    void processingStatusChanged();
    void ollamaModelChanged();
    void ollamaConnectedChanged();
    void selectedFilesChanged();
    void chunkPromptChanged();
    void finalPromptChanged();
    void summaryReady(const QString &summary);
    void errorOccurred(const QString &error);
    void modelPullProgress(const QString &status);

private slots:
    void onOllamaCheckFinished();
    void onModelListFinished();
    void onModelPullFinished();
    void onSummaryFinished(const QString &summary);
    void onSummaryError(const QString &error);

private:
    explicit SessionManager(QObject *parent = nullptr);
    void setProcessingStatus(const QString &status);
    void setIsProcessing(bool processing);
    void setOllamaConnected(bool connected);
    QString getYxobDataPath() const;
    QStringList getSelectedFilePaths() const;
    QString getDefaultChunkPrompt() const;
    QString getDefaultFinalPrompt() const;

    static SessionManager* s_instance;

    QStringListModel* m_folderModel;
    QStandardItemModel* m_fileModel;
    QString m_currentFolder;
    bool m_isProcessing;
    QString m_processingStatus;
    QString m_ollamaModel;
    bool m_ollamaConnected;
    QStringList m_selectedFiles;
    QString m_chunkPrompt;
    QString m_finalPrompt;

    QNetworkAccessManager* m_networkManager;
    DnDSummarizer* m_summarizer;
    QString m_yxobPath;
    QTimer* m_connectionTimer;
};
