cmake_minimum_required(VERSION 3.21)

project(GarenaPet
    VERSION 0.1.0
    DESCRIPTION "Cross-platform floating desktop pet prototype"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")

set(CMAKE_PREFIX_PATH ${CMAKE_CURRENT_SOURCE_DIR}/grpc)
find_package(Protobuf CONFIG REQUIRED)
find_package(gRPC CONFIG REQUIRED)

set(MACOSX_BUNDLE_EXECUTABLE_NAME GarenaPet)
set(MACOSX_BUNDLE_GUI_IDENTIFIER com.garena.mvp.pet)
set(MACOSX_BUNDLE_BUNDLE_NAME GarenaPet)
set(MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION})
set(MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION})

find_package(Qt6 6.5 REQUIRED COMPONENTS
    Quick
    QuickControls2
    Multimedia
)

qt_standard_project_setup(REQUIRES 6.5)

set(GARENA_PET_PROTO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/proto/garena_pet.proto")
set(GARENA_PET_GENERATED_PROTO_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY "${GARENA_PET_GENERATED_PROTO_DIR}")

protobuf_generate(
    OUT_VAR GARENA_PET_PROTO_SRCS
    LANGUAGE cpp
    PROTOS "${GARENA_PET_PROTO_FILE}"
    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    PROTOC_OUT_DIR "${GARENA_PET_GENERATED_PROTO_DIR}"
)

protobuf_generate(
    OUT_VAR GARENA_PET_GRPC_SRCS
    LANGUAGE grpc
    GENERATE_EXTENSIONS .grpc.pb.h .grpc.pb.cc
    PLUGIN "protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>"
    PROTOS "${GARENA_PET_PROTO_FILE}"
    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    PROTOC_OUT_DIR "${GARENA_PET_GENERATED_PROTO_DIR}"
)

add_library(GarenaPetProto STATIC
    ${GARENA_PET_PROTO_SRCS}
    ${GARENA_PET_GRPC_SRCS}
)

target_include_directories(GarenaPetProto
    PUBLIC
        "${GARENA_PET_GENERATED_PROTO_DIR}"
)

target_link_libraries(GarenaPetProto
    PUBLIC
        protobuf::libprotobuf
        gRPC::grpc++
)

set_source_files_properties(qml/Main.qml PROPERTIES
    QT_RESOURCE_ALIAS Main.qml
)
set_source_files_properties(qml/components/PetSprite.qml PROPERTIES
    QT_RESOURCE_ALIAS PetSprite.qml
)
set_source_files_properties(qml/components/PetBehaviorController.qml PROPERTIES
    QT_RESOURCE_ALIAS PetBehaviorController.qml
)
set_source_files_properties(qml/components/IconBubbleButton.qml PROPERTIES
    QT_RESOURCE_ALIAS IconBubbleButton.qml
)
set_source_files_properties(qml/components/ChatWindow.qml PROPERTIES
    QT_RESOURCE_ALIAS ChatWindow.qml
)
set_source_files_properties(qml/components/SettingsWindow.qml PROPERTIES
    QT_RESOURCE_ALIAS SettingsWindow.qml
)

qt_add_executable(GarenaPet
    src/main.cpp
    src/backendclient.cpp
    src/backendclient.h
    src/petgrpcclient.cpp
    src/petgrpcclient.h
    src/voicerecorder.cpp
    src/voicerecorder.h
)

qt_add_qml_module(GarenaPet
    URI GarenaPet
    VERSION 1.0
    QML_FILES
        qml/Main.qml
        qml/components/ChatWindow.qml
        qml/components/IconBubbleButton.qml
        qml/components/PetBehaviorController.qml
        qml/components/PetSprite.qml
        qml/components/SettingsWindow.qml
)

target_include_directories(GarenaPet
    BEFORE
    PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/grpc/include"
        "${GARENA_PET_GENERATED_PROTO_DIR}"
)

target_link_libraries(GarenaPet
    PRIVATE
        GarenaPetProto
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::Multimedia
)

set_target_properties(GarenaPet PROPERTIES
    MACOSX_BUNDLE FALSE
    WIN32_EXECUTABLE TRUE
)

if(APPLE)
    set(GARENA_PET_INFO_PLIST "${CMAKE_CURRENT_BINARY_DIR}/GarenaPet-Info.plist")
    configure_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/cmake/macos/Info.plist.in"
        "${GARENA_PET_INFO_PLIST}"
        @ONLY
    )

    set_target_properties(GarenaPet PROPERTIES
        MACOSX_BUNDLE_INFO_PLIST "${GARENA_PET_INFO_PLIST}"
    )

    target_link_options(GarenaPet PRIVATE
        "LINKER:-sectcreate,__TEXT,__info_plist,${GARENA_PET_INFO_PLIST}"
    )
endif()

if(WIN32)
    target_compile_definitions(GarenaPet PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
endif()
