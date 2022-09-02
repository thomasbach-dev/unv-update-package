ARG UCS_BASE
FROM unv-${UCS_BASE}:latest

ARG UCS_TARGET
ARG ERRATA_LEVEL

RUN echo "Updating to ${UCS_TARGET} errata ${ERRATA_LEVEL}"
RUN univention-upgrade \
      --disable-app-updates \
      --ignoreterm \
      --noninteractive \
      --updateto=${UCS_TARGET} \
      || (cat /var/log/univention/updater.log && exit 1)
RUN apt-get clean
RUN apt-get --purge --yes autoremove
