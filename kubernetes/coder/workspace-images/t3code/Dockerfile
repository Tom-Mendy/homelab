FROM codercom/example-universal@sha256:411973a25007c309162e36958038ccf0f93d7cb48bf295f3da16bd30658c3ca7

USER root

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends --yes buildah \
    && rm -rf /var/lib/apt/lists/*

USER 1000:1000
