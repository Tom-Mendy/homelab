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
    if ! command -v t3 >/dev/null 2>&1 || ! (cd "$(npm root --global)/t3" && node -e "require('node-pty')"); then
      npm_config_build_from_source=true npm install --global t3
    fi
    cd "$(npm root --global)/t3"
    node -e "const p=require('node-pty'); const t=p.spawn('sh', [], {cols:80, rows:24}); t.kill()"
    mkdir -p "$HOME/project" "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keyscan -H forgejo.forgejo.svc.cluster.local >> "$HOME/.ssh/known_hosts" 2>/dev/null || true
    sort -u "$HOME/.ssh/known_hosts" -o "$HOME/.ssh/known_hosts"
    if [ ! -d "$HOME/project/.git" ]; then
      GIT_SSH_COMMAND="coder gitssh" git clone ssh://git@forgejo.forgejo.svc.cluster.local/Tom-Mendy/homelab.git "$HOME/project" || {
        echo "Forgejo has not accepted the Coder-managed SSH key yet. Add the public key printed by coder gitssh above, then clone again."
      }
    fi
  EOT

  metadata {
    display_name = "T3 version"
    key          = "t3-version"
    script       = "t3 --version"
    interval     = 300
    timeout      = 5
  }

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
}

resource "kubernetes_persistent_volume_claim_v1" "home" {
  metadata {
    name      = "coder-${data.coder_workspace.me.id}-t3"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name"   = "t3code-workspace"
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
    name      = "t3-${data.coder_workspace.me.id}"
    namespace = "coder-workspaces"
    labels = {
      "app.kubernetes.io/name" = "t3code-workspace"
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
          "app.kubernetes.io/name" = "t3code-workspace"
          "com.coder.workspace.id" = data.coder_workspace.me.id
        }
      }
      spec {
        automount_service_account_token = false
        security_context {
          run_as_user     = 1000
          run_as_group    = 1000
          fs_group        = 1000
          run_as_non_root = true
          seccomp_profile { type = "RuntimeDefault" }
        }
        container {
          name              = "workspace"
          image             = "codercom/example-universal@sha256:411973a25007c309162e36958038ccf0f93d7cb48bf295f3da16bd30658c3ca7"
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
          resources {
            requests = { cpu = "500m", memory = "2Gi" }
            limits   = { cpu = "2", memory = "6Gi" }
          }
          volume_mount {
            name       = "home"
            mount_path = "/home/coder"
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
