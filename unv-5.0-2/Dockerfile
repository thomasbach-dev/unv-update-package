ARG UCS_BASE
ARG UCS_BASE_ERRATA=latest
FROM unv-${UCS_BASE}:${UCS_BASE_ERRATA}

ARG UCS_TARGET
ARG ERRATA_LEVEL

RUN echo "Updating to ${UCS_TARGET} errata ${ERRATA_LEVEL}"
# We have to enable app updates. Otherwise we get this error:
#   […]
#   Checking required_ucsschool_version ...           Traceback (most recent call last):
#     File "<string>", line 7, in <module>
#   AttributeError: 'NoneType' object has no attribute 'is_installed'
#   FAIL
#   […]
#   required_ucsschool_version:
#   UCS@school is installed. To upgrade to UCS 5.0-2 as least UCS@school 5.0 v2 is required.
#   Please upgrade the UCS@school app first!
RUN univention-upgrade \
      --enable-app-updates \
      --ignoreterm \
      --noninteractive \
      --updateto=${UCS_TARGET} \
      || (cat /var/log/univention/updater.log && exit 1)
RUN apt-get clean
RUN apt-get --purge --yes autoremove
