cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(ham_lab_powermeter)
target_sources(app PRIVATE src/main.c src/curves/curves_core.c src/curves/curves_store.c src/network/network.c src/network/tcp_console.c src/network/ntp_clock.c)
