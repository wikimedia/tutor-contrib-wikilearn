import os
import requests
import typing as t

from hatchling.metadata.plugin.interface import MetadataHookInterface

HERE = os.path.dirname(__file__)


class MetaDataHook(MetadataHookInterface):
    """Hook to dynamically update project metadata during build.

    This hook:
      - Reads version information from tutor/__about__.py
      - Sets base dependencies from requirements/base.in
      - Defines two optional dependency groups:
          * "dev": development dependencies + custom plugins from `custom.txt`
          * "release": custom plugins pinned to the latest GitHub release tags
    """

    def update(self, metadata: dict[str, t.Any]) -> None:
        about = load_about()
        metadata["version"] = about["__version__"]
        metadata["dependencies"] = load_requirements("base.in")
        metadata["optional-dependencies"] = {
            "release": get_latest_release_for_custom_dependencies(),
        }


def load_about() -> dict[str, str]:
    """Load package metadata from tutorwikilearn/__about__.py.

    Returns:
        A dictionary containing the variables defined in __about__.py
        (e.g., {"__package_version__": "x.y.z"}).
    """
    about: dict[str, str] = {}
    with open(os.path.join(HERE, "tutorwikilearn", "__about__.py"), "rt", encoding="utf-8") as f:
        exec(f.read(), about)  # pylint: disable=exec-used
    return about


def get_latest_release_for_custom_dependencies() -> list[str]:
    """Convert custom plugin dependencies to point to latest GitHub releases.

    Reads dependencies from `requirements/dev.in` and replaces any
    `@develop` branch references with the latest release tag found
    via the GitHub releases API redirect.

    Returns:
        A list of dependency strings where custom plugins are pinned
        to their latest release tags.
    """
    deps = load_requirements("dev.in")

    github_urls = []
    for dep in deps:
        # Extract repo name from URL string
        try:
            repo_name = dep.split("@")[0]
        except IndexError:
            raise ValueError(f"Invalid dependency format in custom.txt: {dep}")

        # Fetch latest release tag
        latest_tag = get_latest_release_tag(repo_name)

        # Replace develop with latest tag
        dep_latest = dep.replace("@develop", f"@{latest_tag}")
        github_urls.append(dep_latest)

    return github_urls


def load_requirements(filename: str) -> list[str]:
    """Read and parse requirements from a file in the `requirements/` directory.

    Args:
        filename: The name of the requirements file (e.g., "base.in").

    Returns:
        A list of requirement strings, ignoring comments and blank lines.
    """
    requirements = []
    with open(os.path.join(HERE, "requirements", filename), "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line != "" and not line.startswith("#"):
                requirements.append(line)
    return requirements


def get_latest_release_tag(repo_name: str) -> str:
    """Fetch the latest GitHub release tag for a given Wikimedia repository.

    Args:
        repo_name: The repository name, e.g., "tutor-indigo-wikilearn".

    Returns:
        The latest release tag string (e.g., "v1.2.3").

    Note:
        This relies on GitHub's `/releases/latest` redirect behavior.
    """
    response = requests.get(
        f"https://github.com/wikimedia/{repo_name}/releases/latest", allow_redirects=True, timeout=10
    )
    # Final URL after redirects
    tag_url = response.url
    return tag_url.rstrip("/").split("/")[-1]
