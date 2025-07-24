#!/usr/bin/env bash

set -euo pipefail

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing required Python packages..."
pip install -r requirements.txt

if [ ! -d "${HOME}/.ansible/collections/ansible_collections/kubernetes_sigs/kubespray" ]; then
    if [ ! -f requirements.yml ]; then
        echo "Error: requirements.yml not found"
        exit 1
    fi
    ansible-galaxy collection install -r requirements.yml

    if [ -f "${HOME}/.ansible/collections/ansible_collections/kubernetes_sigs/kubespray/requirements.txt" ]; then
        echo "Installing additional requirements from kubespray collection..."
        pip install -r "${HOME}/.ansible/collections/ansible_collections/kubernetes_sigs/kubespray/requirements.txt"
    else
        echo "Error: requirements.txt not found in kubespray collection"
        exit 1
    fi

fi

ansible-playbook playbooks/install.yml