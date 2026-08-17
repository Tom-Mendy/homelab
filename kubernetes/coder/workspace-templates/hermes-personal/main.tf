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
    mkdir -p "$HERMES_HOME/logs"
    if [ -f "$HERMES_HOME/config.yaml" ]; then
      nohup hermes gateway run >"$HERMES_HOME/logs/gateway-coder.log" 2>&1 &
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
        security_context {
          run_as_user     = 10000
          run_as_group    = 10000
          fs_group        = 10000
          run_as_non_root = true
          seccomp_profile { type = "RuntimeDefault" }
        }
        container {
          name              = "hermes"
          image             = "nousresearch/hermes-agent@sha256:b6c019227889e6675424a2b6223b2cafdd36bf7d1048d1ddd8e043b880d6cc0f"
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
            name  = "MATRIX_HOMESERVER"
            value = "https://matrix.tom-mendy.com"
          }
          env {
            name  = "MATRIX_USER_ID"
            value = "@hermes-bot:matrix.tom-mendy.com"
          }
          env {
            name  = "MATRIX_DEVICE_ID"
            value = "HERMES_BOT"
          }
          env {
            name  = "MATRIX_E2EE_MODE"
            value = "optional"
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
          resources {
            requests = { cpu = "750m", memory = "4Gi" }
            limits   = { cpu = "2", memory = "8Gi" }
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
