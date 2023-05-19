#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import subprocess
import sys
import typing

logger = logging.getLogger(__name__)

MACHINE_SETS = {
    "single": ["bsbt1"],  # This is how it is saved in my ssh_config
}

PARSER = argparse.ArgumentParser(
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
PARSER.add_argument(
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
PARSER.add_argument(
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
PARSER.add_argument(
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
PARSER.add_argument(
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
PARSER.add_argument(
    "--repository-root",
    help=" ".join(
        [
            "The root of the repository. By default the root is searched by walking up",
            "the filetree until the `.git' directory is found.",
        ]
    ),
)
PARSER.add_argument(
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
PARSER.add_argument(
    "-c",
    "--skip-install-check",
    help="Skip the check if the package is installed on the machines.",
    action="store_true",
)
PARSER.add_argument(
    "-l",
    "--log-level",
    default=logging.INFO,
    help=" ".join(
        [
            "Set the levels of logging which should get printed to stdout. The lower the more",
            "messages you will see. Default: %(default)s.",
        ]
    ),
    choices=[
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ],
    type=int,
)


class Configuration(typing.NamedTuple):
    """The central place for application configuration.

    Holds all the data needed to run the application in an easily processible structure.

    """

    repository_root: pathlib.Path
    # The branch_name is not used here, but was of use in other scripts. So I'll leave it here for
    # convenience.
    branch_name: str
    machines: typing.List[str]
    docker_image: str
    folders: typing.List[str]
    skip_build: bool
    skip_check: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        """Instantiate from an `argparse.Namespace` object."""
        if args.repository_root is not None:
            repo_root = pathlib.Path(args.repository_root).resolve()
        else:
            repo_root = cls.search_repository_root(pathlib.Path(".").resolve())
        git_rev_parse = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
        )
        branch_name = git_rev_parse.stdout.decode().strip()
        if args.machines is None:
            logger.error('No MACHINES provdided. See the "--machines" option.')
            sys.exit(1)
        machines = [
            args.prefix + machine
            for machine in MACHINE_SETS.get(args.machines, args.machines.split(","))
        ]
        if args.docker_image is None:
            logger.error('No Docker image provided. See the "--docker-image" option.')
            sys.exit(1)
        return cls(
            repository_root=repo_root,
            branch_name=branch_name,
            machines=machines,
            docker_image=args.docker_image,
            folders=args.folders,
            skip_build=args.skip_package_build,
            skip_check=args.skip_install_check,
        )

    @classmethod
    def search_repository_root(cls, current: pathlib.Path) -> pathlib.Path:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            raise Exception("Could not find repository root!")
        return cls.search_repository_root(current.parent)


def main(args: argparse.Namespace):
    cfg = Configuration.from_args(args)
    logger.info(f"Configuration is:\n{cfg}")
    pkg_files = build_packages_and_get_paths(cfg)
    update_packages(cfg, pkg_files)


def build_packages_and_get_paths(cfg: Configuration) -> typing.List[pathlib.Path]:
    result = []
    for directory in cfg.folders:
        dir_abs = cfg.repository_root / directory
        if cfg.skip_build:
            for pkg_file in dir_abs.glob("*.deb"):
                result.append(pkg_file)
        else:
            proc = build_packages(cfg, directory)
            for pkg_file in get_package_from_stdout(proc):
                result.append(dir_abs / pkg_file)
    return result


def build_packages(cfg: Configuration, directory: str) -> subprocess.CompletedProcess:
    logger.info(f"Building packages in {directory}")
    cmd = [
        "docker",
        "run",
        "--rm",
        "-it",
        # Eventually we need sys_admin to do fancy things in the Docker container, like chrooting
        #'--cap-add=sys_admin',
        f"--volume={cfg.repository_root / directory}:/source",
        cfg.docker_image,
    ]
    proc = None
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
    for machine in cfg.machines:
        logger.info(f"Updating packages on {machine}")
        to_install = []
        for pkg in packages:
            name = pkg.name.split("_", 1)[0]
            logger.info(f"Checking if {name} has to be installed:")
            if cfg.skip_check or is_package_installed(machine, name):
                logger.info(f"Package is installed. Updating!")
                copy_package(machine, pkg)
                to_install.append(pkg.name)
            else:
                logger.info("Skipped!")
        install_packages(machine, to_install)


def copy_package(machine: str, pkg_path: pathlib.Path) -> None:
    logger.debug("Copying over the package")
    subprocess.run(
        ["scp", str(pkg_path), f"root@{machine}:{pkg_path.name}"], check=True
    )


def install_packages(machine: str, pkg_paths: typing.List[str]) -> None:
    if pkg_paths == []:
        logger.info("No packages to install!")
        return

    logger.debug("Running dpkg-install")
    pkgs = " ".join(pkg_path for pkg_path in pkg_paths)
    subprocess.run(["ssh", f"root@{machine}", f"dpkg --install {pkgs}"], check=True)


def is_package_installed(machine: str, package: str) -> bool:
    result = subprocess.run(
        ["ssh", f"root@{machine}", f"dpkg-query --status {package}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode > 1:
        result.check_returncode()
    return result.returncode == 0


if __name__ == "__main__":
    args = PARSER.parse_args()
    logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    logger.setLevel(args.log_level)
    main(args)
