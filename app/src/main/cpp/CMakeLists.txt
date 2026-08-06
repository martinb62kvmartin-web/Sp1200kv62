cmake_minimum_required(VERSION 3.22.1)
project(sp1200_clone)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

set(OBOE_BUILD_SAMPLES OFF CACHE BOOL "" FORCE)
set(OBOE_BUILD_TESTS OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
        oboe
        GIT_REPOSITORY https://github.com/google/oboe.git
        GIT_TAG main
)

FetchContent_MakeAvailable(oboe)

add_library(
        native-lib
        SHARED
        native-lib.cpp
        audio_engine.cpp
)

target_include_directories(
        native-lib
        PRIVATE
        ${oboe_SOURCE_DIR}/include
)

find_library(log-lib log)

target_link_libraries(
        native-lib
        oboe
        android
        ${log-lib}
)
