FROM node:24-alpine AS node

FROM moby/buildkit:rootless

USER root
RUN apk add --no-cache bash ca-certificates git
COPY --from=node /usr/local/ /usr/local/

USER 1000:1000
ENTRYPOINT []
CMD ["/bin/sh"]
