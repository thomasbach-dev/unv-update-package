ARG UCS_BASE
ARG UCS_BASE_ERRATA=latest
FROM unv-${UCS_BASE}:${UCS_BASE_ERRATA}

RUN env LANG=C apt-get update \
    && env LANG=C DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
      build-essential:native \
      debhelper \
      dh-virtualenv \
      dpkg-dev \
      python3-dev \
      python3-pip \
      python3-venv \
      ucslint \
      univention-config-dev \
      univention-management-console-dev \
    && apt-get clean

COPY build.sh /
VOLUME /source
WORKDIR /source

CMD ["/build.sh"]
