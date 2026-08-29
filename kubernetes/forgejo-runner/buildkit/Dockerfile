FROM node:26-alpine AS node

FROM moby/buildkit:v0.33.0-rc1-rootless@sha256:30fa7f6ebbbf482ba76d6a4ed63a7db0786dc43b81dd57fb62436a69d5ba84ab

USER root
RUN apk add --no-cache bash ca-certificates git
# Forgejo actions need Node.js, not npm. Copying the complete Node image also
# imports npm's third-party packages and their avoidable vulnerability surface.
COPY --from=node /usr/local/bin/node /usr/local/bin/node

USER 1000:1000
LABEL org.opencontainers.image.title="Forgejo BuildKit rootless job image"
LABEL org.opencontainers.image.source="https://forgejo.tom-mendy.com/Tom-Mendy/homelab"
LABEL org.opencontainers.image.version="1"
ENTRYPOINT []
CMD ["/bin/sh"]
