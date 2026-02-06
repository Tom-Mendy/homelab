#!/usr/bin/env bash

set -euo pipefail

# Ensure we are in the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
INSTALL_STAMP="$VENV_DIR/.install_stamp"
PLAYBOOKS_DIR="playbooks"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if we should skip updates
FORCE_UPDATE=false
if [[ "${1:-}" == "--update" || "${1:-}" == "-u" ]]; then
    FORCE_UPDATE=true
    shift # Remove the flag from arguments
fi

# Only run installs if requirements changed or force update requested
if [[ "$FORCE_UPDATE" == "true" ]] ||    [[ ! -f "$INSTALL_STAMP" ]] ||    [[ "requirements.txt" -nt "$INSTALL_STAMP" ]] ||    [[ "requirements.yml" -nt "$INSTALL_STAMP" ]]; then

    echo "Syncing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    if [ -f "requirements.yml" ]; then
        echo "Updating Ansible collections..."
        ansible-galaxy collection install -r requirements.yml --upgrade
    fi

    # Check for Kubespray specific requirements
    KUBESPRAY_DIR="${HOME}/.ansible/collections/ansible_collections/kubernetes_sigs/kubespray"
    if [ -d "$KUBESPRAY_DIR" ] && [ -f "$KUBESPRAY_DIR/requirements.txt" ]; then
        pip install -r "$KUBESPRAY_DIR/requirements.txt"
    fi

    touch "$INSTALL_STAMP"
else
    echo "Using cached dependencies (Last sync: $(date -r "$INSTALL_STAMP"))"
    echo "Hint: Use './run.sh --update' to force a sync."
fi

# Determine playbook to run
INPUT_PLAYBOOK="${1:-}"

if [ -z "$INPUT_PLAYBOOK" ]; then
    echo "Available playbooks:"
    ls "$PLAYBOOKS_DIR"/*.yml | sed "s|^$PLAYBOOKS_DIR/|  - |"
    read -p "Enter the name of the playbook to run: " INPUT_PLAYBOOK
fi

# Resolve playbook path (check root and playbooks/)
if [ -f "$INPUT_PLAYBOOK" ]; then
    PLAYBOOK="$INPUT_PLAYBOOK"
elif [ -f "$PLAYBOOKS_DIR/$INPUT_PLAYBOOK" ]; then
    PLAYBOOK="$PLAYBOOKS_DIR/$INPUT_PLAYBOOK"
else
    echo "Error: Playbook '$INPUT_PLAYBOOK' not found."
    exit 1
fi

echo "Running playbook: $PLAYBOOK"
# Use inventory.ini by default if it exists
if [ -f "inventory.ini" ]; then
    ansible-playbook -i inventory.ini "$PLAYBOOK" "${@:2}"
else
    ansible-playbook "$PLAYBOOK" "${@:2}"
fi
