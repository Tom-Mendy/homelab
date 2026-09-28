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

provider "coder" {}
provider "kubernetes" {}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

resource "coder_agent" "main" {
  os   = "linux"
  arch = "amd64"

  startup_script = <<-EOT
    set -eu
    export HOME="/opt/data"
    export PATH="$HOME/.local/bin:$PATH"
    export DISPLAY="$${DISPLAY:-:1}"
    export XDG_RUNTIME_DIR="$${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"
    mkdir -p "$HOME/.local/bin" "$HOME/projects" "$HOME/.config" "$HOME/.cache"
    /usr/local/bin/start-desktop.sh
  EOT

  metadata {
    display_name = "CPU Usage"
    key          = "cpu"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "memory"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Desktop"
    key          = "desktop"
    script       = "curl --silent --fail --max-time 2 http://127.0.0.1:6080/ >/dev/null && echo ready || echo starting"
    interval     = 10
    timeout      = 3
  }
}

resource "coder_app" "desktop" {
  agent_id     = coder_agent.main.id
  slug         = "desktop"
  display_name = "Desktop"
  icon         = "/icon/desktop.svg"
  url          = "http://127.0.0.1:6080"
  share        = "owner"
  subdomain    = false
}

resource "kubernetes_persistent_volume_claim_v1" "home" {
  metadata {
    name      = "coder-${data.coder_workspace.me.id}-desktop"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name"   = "personal-desktop-workspace"
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
      requests = { storage = "10Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "workspace" {
  count            = data.coder_workspace.me.start_count
  wait_for_rollout = false
  depends_on       = [kubernetes_persistent_volume_claim_v1.home]

  metadata {
    name      = "desktop-${data.coder_workspace.me.id}"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name" = "personal-desktop-workspace"
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
          "app.kubernetes.io/name" = "personal-desktop-workspace"
          "com.coder.workspace.id" = data.coder_workspace.me.id
        }
      }

      spec {
        automount_service_account_token = false

        security_context {
          run_as_user     = 10000
          run_as_group    = 10000
          fs_group        = 10000
          run_as_non_root = true
          seccomp_profile { type = "RuntimeDefault" }
        }

        container {
          name              = "workspace"
            image             = "forgejo.tom-mendy.com/tom-mendy/personal-desktop:v2026.9.15-4"
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
            name  = "SHELL"
            value = "/usr/bin/bash"
          }
          env {
            name  = "DISPLAY"
            value = ":1"
          }
          env {
            name  = "XDG_RUNTIME_DIR"
            value = "/tmp/runtime-10000"
          }

          port {
            name           = "novnc"
            container_port = 6080
          }

          resources {
            requests = { cpu = "500m", memory = "2Gi" }
            limits   = { cpu = "4", memory = "8Gi" }
          }

          volume_mount {
            name       = "home"
            mount_path = "/opt/data"
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
