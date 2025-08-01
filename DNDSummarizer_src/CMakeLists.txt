cmake_minimum_required(VERSION 3.16)
project(DNDSummarizer VERSION 0.1 LANGUAGES CXX)

set(CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}/install" CACHE PATH "Installation directory" FORCE)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(QT_QML_GENERATE_QMLLS_INI ON)

find_package(Qt6 REQUIRED COMPONENTS Core Quick Network Widgets)
qt_standard_project_setup(REQUIRES 6.8)

set(SOURCES
    src/main.cpp
    src/sessionmanager.cpp
    src/dndsummarizer.cpp
    src/textprocessor.cpp
)

set(HEADERS
    include/sessionmanager.h
    include/dndsummarizer.h
    include/textprocessor.h
)

qt_add_executable(DNDSummarizer WIN32
    ${SOURCES}
    ${HEADERS}
    win/appicon.rc
    resources/icons/icons.qrc
)

set(QML_FILES
    qml/Main.qml
)

set(QML_SINGLETONS
    qml/Singletons/UserSettings.qml
    qml/Singletons/Colors.qml
)

set_source_files_properties(${QML_SINGLETONS}
    PROPERTIES QT_QML_SINGLETON_TYPE TRUE
)

qt_add_qml_module(DNDSummarizer
    URI Odizinne.DNDSummarizer
    VERSION 1.0
    QML_FILES ${QML_FILES} ${QML_SINGLETONS}
    QML_FILES qml/OllamaSetup.qml
)

target_include_directories(DNDSummarizer PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(DNDSummarizer PRIVATE
    Qt6::Core
    Qt6::Quick
    Qt6::Network
    Qt6::Widgets
)

set_target_properties(DNDSummarizer PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

include(GNUInstallDirs)
install(TARGETS DNDSummarizer
    BUNDLE DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

qt_generate_deploy_qml_app_script(
    TARGET DNDSummarizer
    OUTPUT_SCRIPT deploy_script
    NO_TRANSLATIONS
    DEPLOY_TOOL_OPTIONS --no-compiler-runtime --no-opengl-sw --no-system-dxc-compiler --no-system-d3d-compiler --skip-plugin-types designer,iconengines,qmllint,generic,networkinformation,help,qmltooling,sqldrivers,qmlls
)
install(SCRIPT ${deploy_script})
