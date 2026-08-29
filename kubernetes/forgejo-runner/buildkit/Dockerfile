FROM node:26-alpine AS node

FROM moby/buildkit:rootless

USER root
RUN apk add --no-cache bash ca-certificates git
COPY --from=node /usr/local/ /usr/local/

USER 1000:1000
LABEL org.opencontainers.image.title="Forgejo BuildKit rootless job image"
LABEL org.opencontainers.image.source="https://forgejo.tom-mendy.com/Tom-Mendy/homelab"
LABEL org.opencontainers.image.version="1"
ENTRYPOINT []
CMD ["/bin/sh"]
