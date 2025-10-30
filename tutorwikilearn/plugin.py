import os
from dotenv import load_dotenv
from glob import glob

import click
import subprocess
import importlib_resources
from tutor import hooks
from tutormfe.hooks import MFE_APPS

from tutormfe.hooks import PLUGIN_SLOTS

from .__about__ import __version__

load_dotenv()


########################################
# CONFIGURATION
########################################

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        # Prefix your setting names with 'WIKILEARN_'.
        ("WIKILEARN_VERSION", __version__),
        ("WIKILEARN_EDX_FEATURES_VERSION", os.getenv("WIKILEARN_EDX_FEATURES_VERSION")),
    ]
)

hooks.Filters.CONFIG_OVERRIDES.add_items(
    [
        # Override any default setting values here.
        ("EDX_PLATFORM_REPOSITORY", "https://github.com/wikimedia/edx-platform.git"),
        ("EDX_PLATFORM_VERSION", os.getenv("WIKILEARN_EDX_PLATFORM_VERSION")),
    ]
)

hooks.Filters.ENV_PATTERNS_IGNORE.add_items([
    r"(.*/)?ace_common/edx_ace/common/base_body.html(/.*)?"
])

FRONTEND_PLUGINS_WIKILEARN_VERSION = os.getenv("WIKILEARN_FRONTEND_PLUGINS_VERSION", "master")

hooks.Filters.ENV_PATCHES.add_items(
    [
        (
            f"mfe-dockerfile-post-npm-install-discussions",
            """
RUN npm install git+https://github.com/wikimedia/frontend-plugins-wikilearn.git#{FRONTEND_PLUGINS_WIKILEARN_VERSION}
""",
        ),
        (
            f"mfe-env-config-runtime-definitions-discussions",
            """
    const { UsernameMention } = require('frontend-plugins-wikilearn');
""",
        ),
    ]
)


PLUGIN_SLOTS.add_items([
    (
        "discussions",
        "org.openedx.frontend.discussions.user_mention_plugin.v1",
        """
        {
          op: PLUGIN_OPERATIONS.Insert,
          widget: {
            id: 'user_mention_plugin',
            type: DIRECT_PLUGIN,
            priority: 10,
            RenderWidget: UsernameMention,
          },
        }"""
    )
])



########################################
# TEMPLATE RENDERING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

hooks.Filters.ENV_TEMPLATE_ROOTS.add_items(
    # Root paths for template files, relative to the project root.
    [
        str(importlib_resources.files("tutorwikilearn") / "templates"),
    ]
)

hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    # For each pair (source_path, destination_path):
    # templates at ``source_path`` (relative to your ENV_TEMPLATE_ROOTS) will be
    # rendered to ``source_path/destination_path`` (relative to your Tutor environment).
    # For example, ``wikilearn/templates/wikilearn/build``
    # will be rendered to ``$(tutor config printroot)/env/plugins/wikilearn/build``.
    [
        ("wikilearn/build", "plugins"),
        ("wikilearn/apps", "plugins"),
    ],
)


########################################
# PATCH LOADING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

# For each file in wikilearn/patches,
# apply a patch based on the file's name and contents.
for path in glob(str(importlib_resources.files("tutorwikilearn") / "patches" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))



#######################################
# CUSTOM CLI COMMANDS
#######################################

# Your plugin can also add custom commands directly to the Tutor CLI.
# These commands are run directly on the user's host computer
# (unlike jobs, which are run in containers).

# To define a command group for your plugin, you would define a Click
# group and then add it to CLI_COMMANDS:


@click.group()
def wikilearn() -> None:
    """WikiLearn plugin commands."""
    pass


hooks.Filters.CLI_COMMANDS.add_item(wikilearn)


@wikilearn.command()
def enable() -> None:
    """Enable all required plugins for WikiLearn."""
    try:
        click.echo("Enabling WikiLearn required plugins...")

        result = subprocess.run(
            "tutor plugins enable mfe indigo notes forum aspects",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
        )

        click.echo("✓ Successfully enabled all plugins")
        if result.stdout:
            click.echo(f"Output: {result.stdout}")

    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Command failed: {e.stderr}", err=True)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {str(e)}", err=True)

    click.echo("\nAll plugins have been processed.")
    click.echo("Run 'tutor plugins list' to verify the enabled plugins.")


@MFE_APPS.add()
def _add_my_mfe(mfes):  # type: ignore[no-untyped-def]
    mfes["messenger"] = {
        "repository": "https://github.com/wikimedia/frontend-app-messenger.git",
        "port": 2010,
        "version": os.getenv("WIKILEARN_MESSENGER_MFE_VERSION"),
    }
    mfes["discussions"] = {
        "repository": "https://github.com/edly-io/frontend-app-discussions.git",
        "port": 2002,
        "version": os.getenv("WIKILEARN_DISCUSSIONS_MFE_VERSION"),
    }
    mfes.pop("authn")
    return mfes
