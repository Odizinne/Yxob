#include "dndsummarizer.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>

DnDSummarizer::DnDSummarizer(QObject *parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_textProcessor(new TextProcessor(this))
    , m_totalChunks(0)
    , m_currentChunk(0)
{
}

void DnDSummarizer::setCustomPrompts(const QString &chunkPrompt, const QString &finalPrompt)
{
    m_customChunkPrompt = chunkPrompt;
    m_customFinalPrompt = finalPrompt;
}

void DnDSummarizer::summarizeFiles(const QStringList &filePaths)
{
    if (filePaths.isEmpty()) {
        emit errorOccurred("No files provided");
        return;
    }

    // Reset state
    m_chunkSummaries.clear();
    m_remainingChunks.clear();
    m_currentChunk = 0;
    m_totalChunks = 0;

    emit progressUpdated("Summarizing... You can go grab a coffee or two");

    // Combine all transcript files
    QString combinedText = m_textProcessor->combineTranscripts(filePaths);

    if (combinedText.isEmpty()) {
        emit errorOccurred("Cannot read transcript files");
        return;
    }

    emit progressUpdated("Summarizing... You can go grab a coffee or two");

    // Create chunks
    QStringList chunks = m_textProcessor->createChunks(combinedText, 2000);
    m_remainingChunks = chunks;
    m_totalChunks = chunks.size();

    if (m_totalChunks == 0) {
        emit errorOccurred("No content found");
        return;
    }

    emit progressUpdated("Summarizing... You can go grab a coffee or two");

    // Start processing chunks
    processNextChunk();
}

void DnDSummarizer::processNextChunk()
{
    if (m_remainingChunks.isEmpty()) {
        // All chunks processed, create final summary
        if (m_chunkSummaries.size() > 1) {
            emit progressUpdated("Summarizing... You can go grab a coffee or two");

            QString combinedSummaries = m_chunkSummaries.join("\n\n");
            QString finalPrompt = createPrompt(combinedSummaries, true);

            QJsonObject requestData;
            requestData["model"] = "mistral:7b-instruct";
            requestData["prompt"] = finalPrompt;
            requestData["stream"] = false;

            QJsonObject options;
            options["temperature"] = 0.3;
            options["top_k"] = 40;
            options["top_p"] = 0.9;
            requestData["options"] = options;

            QNetworkRequest request(QUrl("http://localhost:11434/api/generate"));
            request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

            QNetworkReply* reply = m_networkManager->post(request, QJsonDocument(requestData).toJson());
            connect(reply, &QNetworkReply::finished, this, &DnDSummarizer::onSummaryRequestFinished);

        } else if (m_chunkSummaries.size() == 1) {
            // Only one chunk, use it as final summary
            emit summaryReady(m_chunkSummaries.first());
        } else {
            emit errorOccurred("No summary generated");
        }
        return;
    }

    // Process next chunk
    QString currentChunkText = m_remainingChunks.takeFirst();
    m_currentChunk++;

    emit progressUpdated("Summarizing... You can go grab a coffee or two");

    QString prompt = createPrompt(currentChunkText, false);

    QJsonObject requestData;
    requestData["model"] = "mistral:7b-instruct";
    requestData["prompt"] = prompt;
    requestData["stream"] = false;

    QJsonObject options;
    options["temperature"] = 0.4; // Slightly higher for creative narrative
    options["top_k"] = 40;
    options["top_p"] = 0.9;
    requestData["options"] = options;

    QNetworkRequest request(QUrl("http://localhost:11434/api/generate"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply* reply = m_networkManager->post(request, QJsonDocument(requestData).toJson());
    connect(reply, &QNetworkReply::finished, this, &DnDSummarizer::onSummaryRequestFinished);
}

void DnDSummarizer::onSummaryRequestFinished()
{
    QNetworkReply* reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) {
        return;
    }

    reply->deleteLater();

    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred("Network error");
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
    QJsonObject response = doc.object();

    if (response.contains("error")) {
        emit errorOccurred("Ollama error");
        return;
    }

    QString summary = response["response"].toString().trimmed();

    if (summary.isEmpty()) {
        emit errorOccurred("Empty response from Ollama");
        return;
    }

    if (m_remainingChunks.isEmpty() && m_chunkSummaries.size() > 0) {
        // This was the final summary request
        emit summaryReady(summary);
    } else {
        // This was a chunk summary, store it and continue
        m_chunkSummaries.append(summary);
        processNextChunk();
    }
}

QString DnDSummarizer::createPrompt(const QString &text, bool isFinalSummary)
{
    QString promptTemplate;

    if (isFinalSummary) {
        promptTemplate = m_customFinalPrompt.isEmpty() ? getDefaultFinalPrompt() : m_customFinalPrompt;
    } else {
        promptTemplate = m_customChunkPrompt.isEmpty() ? getDefaultChunkPrompt() : m_customChunkPrompt;
    }

    // Replace {TEXT} placeholder with actual text
    return promptTemplate.replace("{TEXT}", text);
}

QString DnDSummarizer::getDefaultChunkPrompt() const
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

QString DnDSummarizer::getDefaultFinalPrompt() const
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
