#! /use/bin/env python3

from argparse import ArgumentParser
from pathlib import Path
import subprocess
import shutil
import json
import re

# List of Swift Packages
SWIFT_PACKAGES: list[str] = [
    "Bookings",
    "Buildings",
    "CommonUI",
    "DevSocAPI",
    "FreeroomsIntents",
    "Location",
    "Networking",
    "Persistence",
    "Rooms",
]

# List of .xcodeproj
PROJECTS: list[str] = [
    "Freerooms",
]

def print_list(items: list[str]) -> None:
    for item in items:
        print(f"* {item}")

def find_archives(derived_data_path: str) -> list[str]:
    """
    Find all documentation archives

    Documentation archives are directories that end with .doccarchive
    """
    archive_find_result = subprocess.run(
        [
            'find', 
            derived_data_path, 
            '-type', 'd', 
            '-name', '*.doccarchive',
        ],
        capture_output=True,
        text=True
    )
    return str(archive_find_result.stdout).split('\n')[:-1]

def scan_package_targets(package_name: str) -> list[str]:
    """
    Gets all non-test targets for a package
    """

    # Make sure the package exists first
    package_path = Path(f"./{package_name}")
    assert package_path.is_dir(), f"Package {package_name} not found"

    # Check package info
    package_info_result = subprocess.run(
        [
            'swift', 'package',
            '--package-path', package_path.absolute(),
            'describe',
            '--type', 'json'
        ],
        capture_output=True,
        text=True
    )

    # Parse package description
    package_targets: list[str] = []
    package_description = json.loads(package_info_result.stdout)
    for target_description in package_description["targets"]:
        target_name = target_description["name"]
        target_type = target_description["type"]

        # Ignore test targets
        if target_type == "test":
            continue

        package_targets.append(target_name)

    # Return list of descriptions
    return package_targets

def combine_docs(archive_paths: list[str], output_path: str) -> None:
    """
    Combines docs into a single archive
    """

    path = Path(output_path)

    # Delete directory if it already exists
    shutil.rmtree(path)

    # Create destination if it doesn't exist
    path.mkdir(parents=True)

    # Combine docs to destination
    subprocess.run(
        ['xcrun', 'docc', 'merge'] + 
        archive_paths +
        ['--output-path', output_path]
    )

def main() -> None:
    argument_parser = ArgumentParser()
    argument_parser.add_argument("--derived-data-path", default="./.build")
    argument_parser.add_argument("--output-path", default="./docs/ios")

    args = argument_parser.parse_args()
    derived_data_path = str(args.derived_data_path)
    output_path = str(args.output_path)

    # Make sure we are running from the ios directory
    current_dir_path = Path.cwd()
    assert current_dir_path.name == "ios", "Must run from the ios directory"

    # Search for archives
    print(f"Scanning for documentation archives in '{derived_data_path}'...")
    found_archives = find_archives(derived_data_path)
    print(f"Found {len(found_archives)} archive(s):")

    # Extract target names from archive paths
    archive_target_names: list[str] = []
    for path in found_archives:
        potential_match = re.match(r"^\.\/.+\/(\w+).doccarchive$", path)
        assert potential_match is not None, f"Failed to extract target name from documentation path: {path}"
        archive_target_names.append(potential_match.group(1))
    print_list(archive_target_names)

    # Handle all packages
    for package_name in SWIFT_PACKAGES:
        print()

        # Scan for targets
        print(f"Scanning targets for package '{package_name}'...")
        targets = scan_package_targets(package_name)
        print(f"Targets for package '{package_name}':")
        print_list(targets)

        # Get the documetation archive for each target
        archive_paths: list[str] = []
        for target in targets:

            # Get the index of the target
            try:
                target_index = archive_target_names.index(target)
            except ValueError:
                print(f"WARNING: Target '{target}' does not have a .doccarchive")
                continue

            # Add it to the list of traced targets
            archive_paths.append(found_archives[target_index])

        # Combine documentation
        package_output_path = f"{output_path}/{package_name}"
        print(f"Combining documentation for package...")
        combine_docs(archive_paths, package_output_path)
        print(f"Combined documentation at {package_output_path}")

if __name__ == "__main__":
    main()
