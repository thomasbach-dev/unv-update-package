ARG UCS_BASE
FROM univention/ucs-generic-amd64:${UCS_BASE}

ARG UCS_TARGET
ARG ERRATA_LEVEL

COPY univention-archive-key-ucs-5x.gpg /etc/apt/trusted.gpg.d/
RUN ucr set repository/online=yes \
      repository/online/unmaintained=yes \
      repository/online/verify=no
RUN rm -v /etc/apt/sources.list.d/05univention-system-setup.list

# Fetch the currently configured nameserver and set it in UCR. The update process will trigger a
# rebuild of configuration files and /etc/resolv.conf will be overwritten in this process. This is
# the nasty workaround:
RUN ucr set nameserver1=$(grep nameserver /etc/resolv.conf | cut -d' ' -f2 | head -n1) \
      && cat /etc/resolv.conf

RUN echo "Updating to ${UCS_TARGET} errata ${ERRATA_LEVEL}"
RUN univention-upgrade \
      --disable-app-updates \
      --ignoreterm \
      --noninteractive \
      --updateto=${UCS_TARGET} \
      || (cat /var/log/univention/updater.log && exit 1)
RUN ucr commit /etc/apt/sources.list.d/15_ucs-online-version.list
RUN apt-get clean
RUN apt-get --purge --yes autoremove
