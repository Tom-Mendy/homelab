terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = "2.18.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.2.1"
    }
  }
}

provider "coder" {
  url = "http://coder.coder.svc.cluster.local"
}
provider "kubernetes" {}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

resource "coder_agent" "main" {
  os   = "linux"
  arch = "amd64"

  startup_script = <<-EOT
    set -eu
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$HOME/.local/bin:/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH"
    if ! command -v bun >/dev/null 2>&1; then
      curl -fsSL https://bun.sh/install | bash
    fi
    UV_CONSTRAINT= uv pip freeze --python /opt/hermes/.venv/bin/python3 | grep -v '^-e ' >"$UV_CONSTRAINT"
    [ ! -f "$HOME/.profile" ] || sed -i '\|runtime-venv-v2026.9.24|d' "$HOME/.profile"
    profile_line='export BUN_INSTALL="$HOME/.bun"; export PATH="$BUN_INSTALL/bin:/opt/hermes/bin:/opt/hermes/.venv/bin:$HOME/.local/bin:$PATH"'
    grep -qxF "$profile_line" "$HOME/.profile" 2>/dev/null || printf '\n%s\n' "$profile_line" >> "$HOME/.profile"
    if ! command -v coder >/dev/null 2>&1; then
      curl -fsSL https://coder.com/install.sh \
        | sh -s -- --version 2.36.4 --method standalone --prefix "$HOME/.local"
    fi
    if ! command -v crane >/dev/null 2>&1; then
      mkdir -p "$HOME/.local/bin"
      curl -fsSL https://github.com/google/go-containerregistry/releases/download/v0.22.1/go-containerregistry_Linux_x86_64.tar.gz \
        | tar -xz -C "$HOME/.local/bin" crane
      chmod 0755 "$HOME/.local/bin/crane"
    fi
    bash_login_line='if [ -x /usr/bin/bash ] && [ -z "$${BASH_VERSION:-}" ] && [ -n "$${SSH_TTY:-}" ]; then exec /usr/bin/bash -l; fi'
    grep -qxF "$bash_login_line" "$HOME/.profile" 2>/dev/null || printf '%s\n' "$bash_login_line" >> "$HOME/.profile"
    mkdir -p "$HERMES_HOME/logs" "$HERMES_HOME/skills/homelab-cluster"
    cat >"$HERMES_HOME/bootstrap-cluster.py" <<'PYTHON'
${file("${path.module}/bootstrap-cluster.py")}
PYTHON
    /opt/hermes/.venv/bin/python3 "$HERMES_HOME/bootstrap-cluster.py"
    cat >"$HERMES_HOME/skills/homelab-cluster/SKILL.md" <<'SKILL'
${file("${path.module}/cluster-operations.md")}
SKILL
    if [ -f "$HERMES_HOME/config.yaml" ]; then
      # Coder starts this supervisor inside the workspace, independently of SSH.
      nohup bash -c 'while true; do hermes gateway run; sleep 10; done' >"$HERMES_HOME/logs/gateway-coder.log" 2>&1 &
    else
      echo "Run 'hermes model' and 'hermes memory setup' once, then restart the workspace."
    fi
  EOT

  metadata {
    display_name = "Hermes version"
    key          = "hermes-version"
    script       = "hermes --version"
    interval     = 300
    timeout      = 5
  }

  metadata {
    display_name = "Bun version"
    key          = "bun-version"
    script       = "export BUN_INSTALL=\"$HOME/.bun\"; export PATH=\"$BUN_INSTALL/bin:$PATH\"; bun --version"
    interval     = 300
    timeout      = 5
  }

  metadata {
    display_name = "Memory"
    key          = "memory"
    script       = "hermes memory status 2>/dev/null | head -1 || echo not-configured"
    interval     = 60
    timeout      = 5
  }
}

resource "kubernetes_persistent_volume_claim_v1" "home" {
  metadata {
    name      = "coder-${data.coder_workspace.me.id}-hermes"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name"   = "hermes-workspace"
      "com.coder.workspace.id"   = data.coder_workspace.me.id
      "com.coder.workspace.name" = data.coder_workspace.me.name
      "com.coder.user.id"        = data.coder_workspace_owner.me.id
    }
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "nfs-k8s"
    resources {
      requests = { storage = "20Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "workspace" {
  count            = data.coder_workspace.me.start_count
  wait_for_rollout = false
  depends_on       = [kubernetes_persistent_volume_claim_v1.home]

  metadata {
    name      = "hermes-${data.coder_workspace.me.id}"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name" = "hermes-workspace"
      "com.coder.workspace.id" = data.coder_workspace.me.id
    }
  }

  spec {
    replicas = 1
    strategy { type = "Recreate" }
    selector {
      match_labels = { "com.coder.workspace.id" = data.coder_workspace.me.id }
    }
    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = "hermes-workspace"
          "com.coder.workspace.id" = data.coder_workspace.me.id
        }
      }
      spec {
        automount_service_account_token = false
        service_account_name            = "hermes"
        image_pull_secrets {
          name = "portfolio-registry-auth"
        }
        security_context {
          run_as_user     = 10000
          run_as_group    = 10000
          fs_group        = 10000
          run_as_non_root = true
          seccomp_profile { type = "RuntimeDefault" }
        }
        container {
          name              = "hermes"
          image             = "harbor.home.tom-mendy.com/homelab/hermes-workspace@sha256:b6ce9d55c6b2d8fff9e6ffb8da930218539c1b4e94eae289b448b7717aa8439c"
          image_pull_policy = "IfNotPresent"
          command           = ["sh", "-c", coder_agent.main.init_script]
          security_context {
            allow_privilege_escalation = false
            run_as_non_root            = true
            capabilities { drop = ["ALL"] }
          }
          env {
            name  = "CODER_AGENT_TOKEN"
            value = coder_agent.main.token
          }
          env {
            name  = "HOME"
            value = "/opt/data"
          }
          env {
            name  = "HERMES_HOME"
            value = "/opt/data"
          }
          env {
            name  = "KUBECONFIG"
            value = "/opt/data/.kube/hermes.config"
          }
          env {
            name  = "TERMINAL_ENV"
            value = "local"
          }
          env {
            name  = "SHELL"
            value = "/usr/bin/bash"
          }
          env {
            name  = "UV_CONSTRAINT"
            value = "/opt/data/.uv-constraints-v2026.9.24.txt"
          }
          env {
            name  = "HINDSIGHT_API_URL"
            value = "http://hindsight.agent.svc.cluster.local:8888"
          }
          env {
            name  = "MATRIX_HOMESERVER"
            value = "https://matrix.tom-mendy.com"
          }
          env {
            name  = "MATRIX_USER_ID"
            value = "@hermes-bot:matrix.tom-mendy.com"
          }
          env {
            name  = "MATRIX_E2EE_MODE"
            value = "required"
          }
          env {
            name = "MATRIX_ACCESS_TOKEN"
            value_from {
              secret_key_ref {
                name = "hermes-matrix"
                key  = "MATRIX_ACCESS_TOKEN"
              }
            }
          }
          env {
            name = "MATRIX_ALLOWED_USERS"
            value_from {
              secret_key_ref {
                name = "hermes-matrix"
                key  = "MATRIX_ALLOWED_USERS"
              }
            }
          }
          env {
            name = "MATRIX_RECOVERY_KEY"
            value_from {
              secret_key_ref {
                name = "hermes-matrix"
                key  = "MATRIX_RECOVERY_KEY"
              }
            }
          }
          resources {
            requests = { cpu = "750m", memory = "4Gi" }
            limits   = { cpu = "2", memory = "8Gi" }
          }
          volume_mount {
            name       = "kubernetes-api"
            mount_path = "/var/run/secrets/kubernetes.io/serviceaccount"
            read_only  = true
          }
          volume_mount {
            name       = "home"
            mount_path = "/opt/data"
          }
        }
        volume {
          name = "kubernetes-api"
          projected {
            sources {
              service_account_token {
                path               = "token"
                expiration_seconds = 3600
              }
            }
            sources {
              config_map {
                name = "kube-root-ca.crt"
                items {
                  key  = "ca.crt"
                  path = "ca.crt"
                }
              }
            }
            sources {
              downward_api {
                items {
                  path = "namespace"
                  field_ref {
                    field_path = "metadata.namespace"
                  }
                }
              }
            }
          }
        }
        volume {
          name = "home"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.home.metadata[0].name
          }
        }
      }
    }
  }
}
