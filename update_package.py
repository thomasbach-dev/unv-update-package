#!/usr/bin/env python3
import argparse
import dataclasses
import logging
import os
import pathlib
import subprocess
import sys
import typing

logger = logging.getLogger(__name__)
_LOG_LEVEL_NAMES = [
    logging.getLevelName(level)
    for level in [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    ]
]

MACHINE_SETS = {
    "single": ["bsbt1"],  # This is how it is saved in my ssh_config
}


def make_arg_parser():
    parser = argparse.ArgumentParser(
        description=" ".join(
            [
                "Build and update packages.",
                "Build packages for each FOLDER, copy them over to the given MACHINES and update them.",
                "Package buildings is done via Docker.",
                "Note that packages are only updated, i.e. if they are not installed the package will not",
                "be installed on the target machine.",
                'You can skip the check if the package is installed using "-c".',
                "The script is supposed to run anywhere in a git repository",
                "and FOLDER has to be relative to the root of the repo.",
            ]
        ),
        epilog="\n".join(
            [
                "These are the configured predefined sets of machines:",
            ]
            + [f'{key}: {",".join(machines)}' for key, machines in MACHINE_SETS.items()]
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folders",
        metavar="FOLDER",
        nargs="+",
        help=" ".join(
            [
                'The name of the folders to build (or -if "-b" is given- search) packages for.',
                "You have to pass in the relative name from the repository root",
                "Note that more than one package can stem from the same folder.",
            ]
        ),
    )
    parser.add_argument(
        "-m",
        "--machines",
        default=os.environ.get("UP_MACHINES"),
        help=" ".join(
            [
                "The set of machines to update the packages on.",
                "This has to be a comma separated list.",
                'You can also set this argument via the "UP_MACHINES" environment variable.',
            ]
        ),
    )
    parser.add_argument(
        "--ssh-config",
        default=os.environ.get("UP_SSH_CONFIG"),
        help=" ".join(
            [
                "A ssh configuration file to pass on to ssh via the '-F' option.",
                'You can also set this argument via the "UP_SSH_CONFIG" environment variable.',
            ]
        ),
    )
    parser.add_argument(
        "-i",
        "--docker-image",
        metavar="IMG",
        default=os.environ.get("UP_DOCKER_IMAGE"),
        help=" ".join(
            [
                "Use IMG to build packages.",
                'You can also set this argument via the "UP_DOCKER_IMAGE" environment variable.',
            ]
        ),
    )
    parser.add_argument(
        "-p",
        "--prefix",
        default="",
        help=" ".join(
            [
                "Prefix all machines with the given string.",
                "Empty by default.",
            ]
        ),
    )
    parser.add_argument(
        "--repository-root",
        help=" ".join(
            [
                "The root of the repository. By default the root is searched by walking up",
                "the filetree until the `.git' directory is found.",
            ]
        ),
    )
    parser.add_argument(
        "-b",
        "--skip-package-build",
        help=" ".join(
            [
                "Skip the build of the package before distributing it. Note that this results in a",
                "slightly different behaviour: the `FOLDER's are now simply searched for `.deb' files",
                "which are then assumed to be distributed. Make sure to clean up built packages!.",
            ]
        ),
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--skip-install-check",
        help="Skip the check if the package is installed on the machines.",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default=logging.INFO,
        help=" ".join(
            [
                "Set the levels of logging which should get printed to stdout. The lower the more",
                "messages you will see. Default: %(default)s.",
            ]
        ),
        choices=_LOG_LEVEL_NAMES,
    )
    return parser


@dataclasses.dataclass(frozen=True)
class BaseConfiguration:
    repository_root: pathlib.Path
    docker_image: str

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        if args.repository_root is not None:
            repo_root = pathlib.Path(args.repository_root).resolve()
        else:
            repo_root = cls.search_repository_root(pathlib.Path(".").resolve())

        if args.docker_image is None:
            logger.error('No Docker image provided. See the "--docker-image" option.')
            sys.exit(1)

        return cls(repo_root, args.docker_image)

    @classmethod
    def search_repository_root(cls, current: pathlib.Path) -> pathlib.Path:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            raise Exception("Could not find repository root!")
        return cls.search_repository_root(current.parent)


class Configuration(typing.NamedTuple):
    """The central place for application configuration.

    Holds all the data needed to run the application in an easily processible structure.

    """

    base_config: BaseConfiguration
    # The branch_name is not used here, but was of use in other scripts. So I'll leave it here for
    # convenience.
    machines: typing.List[str]
    ssh_config: str
    folders: typing.List[str]
    skip_build: bool
    skip_check: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        """Instantiate from an `argparse.Namespace` object."""
        base_config = BaseConfiguration.from_args(args)
        if args.machines is None:
            logger.error('No MACHINES provdided. See the "--machines" option.')
            sys.exit(1)
        machines = [
            args.prefix + machine
            for machine in MACHINE_SETS.get(args.machines, args.machines.split(","))
        ]
        return cls(
            base_config,
            machines=machines,
            ssh_config=args.ssh_config,
            folders=args.folders,
            skip_build=args.skip_package_build,
            skip_check=args.skip_install_check,
        )

    def run(self):
        pkg_files = build_packages_and_get_paths(self)
        update_packages(self, pkg_files)


def main(argv=sys.argv[1:]):
    parser = make_arg_parser()
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    logger.debug("Passed command line arguments: %s", argv)

    cfg = Configuration.from_args(args)
    logger.info(f"Configuration is:\n{cfg}")
    cfg.run()


def build_packages_and_get_paths(cfg: Configuration) -> typing.List[pathlib.Path]:
    result = []
    for directory in cfg.folders:
        dir_abs = cfg.base_config.repository_root / directory
        if cfg.skip_build:
            for pkg_file in dir_abs.glob("*.deb"):
                result.append(pkg_file)
        else:
            proc = build_packages(cfg.base_config, directory)
            for pkg_file in get_package_from_stdout(proc):
                result.append(dir_abs / pkg_file)
    return result


_BUILD_SCRIPT = """
#!/bin/bash
set -ex
#
#export LC_ALL="en_US.UTF-8"
##ucslint 1>&2
#
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
"""


def build_packages(
    cfg: BaseConfiguration, directory: str
) -> subprocess.CompletedProcess:
    logger.info(f"Building packages in {directory}")
    cmd = [
        "docker",
        "run",
        "--rm",
        "-it",
        # Eventually we need sys_admin to do fancy things in the Docker container, like chrooting
        #'--cap-add=sys_admin',
        f"--volume={cfg.repository_root / directory}:/source",
        "--workdir=/source",
        cfg.docker_image,
        f"/bin/bash",
        "-c",
        _BUILD_SCRIPT,
    ]
    proc = None
    logger.debug(f"Command is:\n%s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as proc:
        logger.error(proc.stdout.decode())
        raise
    logger.debug(f"Output is:\n{proc.stdout.decode()}")
    return proc


def get_package_from_stdout(proc: subprocess.CompletedProcess) -> typing.Iterable[str]:
    for line in proc.stdout.decode().splitlines():
        if line.startswith("PKG_FILE="):
            pkg_file = line[len("PKG_FILE=") :]
            logger.info(f"Succesfully built package {pkg_file}")
            yield pkg_file


def update_packages(cfg: Configuration, packages: typing.List[pathlib.Path]) -> None:
    ssh_ops = SSHOperations(cfg.ssh_config)
    for machine in cfg.machines:
        logger.info(f"Updating packages on {machine}")
        to_install = []
        for pkg in packages:
            name = pkg.name.split("_", 1)[0]
            logger.info(f"Checking if {name} has to be installed:")
            if cfg.skip_check or is_package_installed(ssh_ops, machine, name):
                logger.info(f"Package is installed. Updating!")
                copy_package(ssh_ops, machine, pkg)
                to_install.append(pkg.name)
            else:
                logger.info("Skipped!")
        install_packages(ssh_ops, machine, to_install)


@dataclasses.dataclass(frozen=True)
class SSHOperations:
    ssh_config: typing.Optional[str]

    def scp(self, src: str, dest: str) -> subprocess.CompletedProcess:
        cmd = self._add_ssh_config_if_needed(["scp"])
        cmd.extend([src, dest])
        logger.debug("Running %r", cmd)
        return subprocess.run(cmd, check=True)

    def ssh(
        self, machine: str, remote_cmd: str, *args, **kwargs
    ) -> subprocess.CompletedProcess:
        cmd = self._add_ssh_config_if_needed(["ssh"])
        cmd.extend([machine, remote_cmd])
        logger.debug("Running %r", cmd)
        return subprocess.run(cmd, *args, **kwargs)

    def _add_ssh_config_if_needed(self, cmd):
        if self.ssh_config is not None:
            cmd.extend(["-F", self.ssh_config])
        return cmd


def copy_package(ssh_ops: SSHOperations, machine: str, pkg_path: pathlib.Path) -> None:
    logger.debug("Copying over the package")
    ssh_ops.scp(str(pkg_path), f"{machine}:{pkg_path.name}")


def install_packages(
    ssh_ops: SSHOperations, machine: str, pkg_paths: typing.List[str]
) -> None:
    if pkg_paths == []:
        logger.info("No packages to install!")
        return

    logger.debug("Running dpkg-install")
    pkgs = " ".join(pkg_path for pkg_path in pkg_paths)
    ssh_ops.ssh(machine, f"dpkg --install {pkgs}", check=True)


def is_package_installed(ssh_ops: SSHOperations, machine: str, package: str) -> bool:
    result = ssh_ops.ssh(
        machine,
        f"dpkg-query --status {package}",
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode > 1:
        result.check_returncode()
    return result.returncode == 0


if __name__ == "__main__":
    main()
