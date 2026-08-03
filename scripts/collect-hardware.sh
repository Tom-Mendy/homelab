#!/usr/bin/env bash

set -u

sudo apt update && sudo apt install -y lshw dmidecode pciutils usbutils ethtool smartmontools nvme-cli lm-sensors

OUTPUT="hardware-$(hostname)-$(date +%Y%m%d-%H%M%S).txt"

{
    echo "============================================================"
    echo "HARDWARE REPORT"
    echo "============================================================"
    echo "Hostname: $(hostname)"
    echo "Date: $(date --iso-8601=seconds)"
    echo

    echo "============================================================"
    echo "OPERATING SYSTEM"
    echo "============================================================"
    cat /etc/os-release 2>/dev/null || true
    uname -a
    echo

    echo "============================================================"
    echo "SYSTEM AND MOTHERBOARD"
    echo "============================================================"
    sudo dmidecode -t system 2>/dev/null || true
    sudo dmidecode -t baseboard 2>/dev/null || true
    sudo dmidecode -t bios 2>/dev/null || true
    echo

    echo "============================================================"
    echo "CPU"
    echo "============================================================"
    lscpu
    echo

    echo "============================================================"
    echo "MEMORY SUMMARY"
    echo "============================================================"
    free -h
    echo

    echo "============================================================"
    echo "MEMORY MODULES"
    echo "============================================================"
    sudo dmidecode -t memory 2>/dev/null || true
    echo

    echo "============================================================"
    echo "STORAGE"
    echo "============================================================"
    lsblk -o NAME,MODEL,SERIAL,SIZE,TYPE,FSTYPE,MOUNTPOINTS,TRAN
    echo

    if command -v nvme >/dev/null 2>&1; then
        echo "============================================================"
        echo "NVME DEVICES"
        echo "============================================================"
        sudo nvme list
        echo
    fi

    echo "============================================================"
    echo "PCI DEVICES AND DRIVERS"
    echo "============================================================"
    lspci -nnk
    echo

    echo "============================================================"
    echo "PCI TREE"
    echo "============================================================"
    lspci -tv
    echo

    echo "============================================================"
    echo "NETWORK"
    echo "============================================================"
    ip -br address
    echo
    sudo lshw -class network 2>/dev/null || true
    echo

    echo "============================================================"
    echo "USB"
    echo "============================================================"
    lsusb
    echo
    lsusb -t
    echo

    echo "============================================================"
    echo "TEMPERATURES"
    echo "============================================================"
    if command -v sensors >/dev/null 2>&1; then
        sensors
    else
        echo "lm-sensors is not installed."
    fi
    echo

    echo "============================================================"
    echo "HARDWARE SUMMARY"
    echo "============================================================"
    sudo lshw -short 2>/dev/null || true
} > "$OUTPUT"

echo "Report generated: $OUTPUT"
