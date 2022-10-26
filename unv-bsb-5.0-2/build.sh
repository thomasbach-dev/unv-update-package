#!/bin/bash

set -ex

export LC_ALL="en_US.UTF-8"
#ucslint 1>&2

tmpdir="$(mktemp -d)"

pkg_dir="$(pwd)"
orig_uid=$(stat -c %u "${pkg_dir}")
orig_gid=$(stat -c %g "${pkg_dir}")
echo "Copying package files to ${tmpdir}"
cp -av "${pkg_dir}"/* "${tmpdir}"

cd "${tmpdir}"

dpkg-buildpackage --build=binary

for pkg_file in "${tmpdir}"/../*.deb; do
    cp "${pkg_file}" "${pkg_dir}"
    pkg=$(basename "${pkg_file}")
    chown ${orig_uid}:${orig_gid} "${pkg_dir}/${pkg}"
    echo "PKG_FILE=${pkg}"
done
