#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QIcon>
#include <QAbstractItemModel>

int main(int argc, char *argv[])
{
    qputenv("QT_QUICK_CONTROLS_MATERIAL_VARIANT", "Dense");
    QGuiApplication app(argc, argv);
    app.setWindowIcon(QIcon(":/icons/icon.png"));
    app.setOrganizationName("Odizinne");
    app.setApplicationName("DNDSummarizer");

    qmlRegisterUncreatableType<QAbstractItemModel>("QtQml", 2, 0, "QAbstractItemModel", "QAbstractItemModel is abstract");

    QQmlApplicationEngine engine;
    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);
    engine.loadFromModule("Odizinne.DNDSummarizer", "Main");

    return app.exec();
}
