import argparse
import logging
from pathlib import Path
from subprocess import run, PIPE
import tomli

_LOGGER = logging.getLogger(__name__)


def generate_autorest(folder: Path) -> None:

    readme_path = folder / "swagger" / "README.md"
    completed_process = run(f"autorest {readme_path} --python-sdks-folder=../../", cwd=folder, shell=True)

    if completed_process.returncode != 0:
        raise ValueError("Something happened with autorest: " + str(completed_process))
    _LOGGER.info("Autorest done")


def generate_typespec(folder: Path) -> None:
    tsp_location_path = folder / "tsp-location.yaml"

    if not tsp_location_path.exists():
        raise ValueError(
            "Didn't find a tsp_location.yaml in local directory. Please make sure a valid "
            "tsp-location.yaml file exists before running this command, for more information "
            "on how to create one, see: "
            "https://github.com/Azure/azure-sdk-tools/tree/main/tools/tsp-client/README.md"
        )

    completed_process = run("tsp-client update", cwd=folder, shell=True, stderr=PIPE)
    if completed_process.returncode != 0:
        if "'tsp-client' is not recognized" in completed_process.stderr.decode("utf-8"):
            raise ValueError(
                "tsp-client is not installed. Please run: npm install -g @azure-tools/typespec-client-generator-cli"
                )
        raise ValueError("Something happened with tsp-client update step: " + str(completed_process))

    _LOGGER.info("TypeSpec generate done")

def generate(folder: Path = Path(".")) -> None:
    if (folder / "swagger" / "README.md").exists():
        generate_autorest(folder)
    elif (folder / "tsp-location.yaml").exists():
        generate_typespec(folder)
    else:
        raise ValueError("Didn't find swagger/README.md nor tsp_location.yaml")

def generate_main() -> None:
    """Main method"""

    parser = argparse.ArgumentParser(
        description="Build SDK using Codegen.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Verbosity in INFO mode",
    )
    parser.add_argument("--debug", dest="debug", action="store_true", help="Verbosity in DEBUG mode")

    args = parser.parse_args()
    main_logger = logging.getLogger()
    if args.verbose or args.debug:
        logging.basicConfig()
        main_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    generate()


if __name__ == "__main__":
    generate_main()
