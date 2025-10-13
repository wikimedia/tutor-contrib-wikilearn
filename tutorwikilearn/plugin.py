import os
from glob import glob

import click
import subprocess
import importlib_resources
from tutor import hooks
from tutor import plugins
from tutormfe.hooks import MFE_APPS

from tutormfe.hooks import PLUGIN_SLOTS

from .__about__ import __version__


########################################
# CONFIGURATION
########################################

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        # Prefix your setting names with 'WIKILEARN_'.
        ("WIKILEARN_VERSION", __version__),
    ]
)

hooks.Filters.CONFIG_UNIQUE.add_items(
    [
        # Add settings that don't have a reasonable default for all users here.
        # For instance: passwords, secret keys, etc.
        # Each new setting is a pair: (setting_name, unique_generated_value).
        # Prefix your setting names with 'WIKILEARN_'.
        # For example:
        ### ("WIKILEARN_SECRET_KEY", "{{ 24|random_string }}"),
    ]
)

hooks.Filters.CONFIG_OVERRIDES.add_items(
    [
        # Override any default setting values here.
    ]
)


hooks.Filters.ENV_PATCHES.add_items(
    [
#         (
#             f"mfe-dockerfile-post-npm-install-discussions",
#             """
# RUN npm install git+https://${GITHUB_TOKEN}:x-oauth-basic@github.com/edly-io/frontend-plugins-wikilearn.git


# """,
#         ),
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
# INITIALIZATION TASKS
########################################

# To add a custom initialization task, create a bash script template under:
# wikilearn/templates/wikilearn/tasks/
# and then add it to the MY_INIT_TASKS list. Each task is in the format:
# ("<service>", ("<path>", "<to>", "<script>", "<template>"))
MY_INIT_TASKS: list[tuple[str, tuple[str, ...]]] = [
    # For example, to add LMS initialization steps, you could add the script template at:
    # wikilearn/templates/wikilearn/tasks/lms/init.sh
    # And then add the line:
    ### ("lms", ("wikilearn", "tasks", "lms", "init.sh")),
]


# For each task added to MY_INIT_TASKS, we load the task template
# and add it to the CLI_DO_INIT_TASKS filter, which tells Tutor to
# run it as part of the `init` job.
for service, template_path in MY_INIT_TASKS:
    full_path: str = str(
        importlib_resources.files("wikilearn")
        / os.path.join("templates", *template_path)
    )
    with open(full_path, encoding="utf-8") as init_task_file:
        init_task: str = init_task_file.read()
    hooks.Filters.CLI_DO_INIT_TASKS.add_item((service, init_task))


########################################
# DOCKER IMAGE MANAGEMENT
########################################


# Images to be built by `tutor images build`.
# Each item is a quadruple in the form:
#     ("<tutor_image_name>", ("path", "to", "build", "dir"), "<docker_image_tag>", "<build_args>")
hooks.Filters.IMAGES_BUILD.add_items(
    [
        # To build `myimage` with `tutor images build myimage`,
        # you would add a Dockerfile to templates/wikilearn/build/myimage,
        # and then write:
        ### (
        ###     "myimage",
        ###     ("plugins", "wikilearn", "build", "myimage"),
        ###     "docker.io/myimage:{{ WIKILEARN_VERSION }}",
        ###     (),
        ### ),
    ]
)


# Images to be pulled as part of `tutor images pull`.
# Each item is a pair in the form:
#     ("<tutor_image_name>", "<docker_image_tag>")
hooks.Filters.IMAGES_PULL.add_items(
    [
        # To pull `myimage` with `tutor images pull myimage`, you would write:
        ### (
        ###     "myimage",
        ###     "docker.io/myimage:{{ WIKILEARN_VERSION }}",
        ### ),
    ]
)


# Images to be pushed as part of `tutor images push`.
# Each item is a pair in the form:
#     ("<tutor_image_name>", "<docker_image_tag>")
hooks.Filters.IMAGES_PUSH.add_items(
    [
        # To push `myimage` with `tutor images push myimage`, you would write:
        ### (
        ###     "myimage",
        ###     "docker.io/myimage:{{ WIKILEARN_VERSION }}",
        ### ),
    ]
)


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


########################################
# CUSTOM JOBS (a.k.a. "do-commands")
########################################

# A job is a set of tasks, each of which run inside a certain container.
# Jobs are invoked using the `do` command, for example: `tutor local do importdemocourse`.
# A few jobs are built in to Tutor, such as `init` and `createuser`.
# You can also add your own custom jobs:


# To add a custom job, define a Click command that returns a list of tasks,
# where each task is a pair in the form ("<service>", "<shell_command>").
# For example:
### @click.command()
### @click.option("-n", "--name", default="plugin developer")
### def say_hi(name: str) -> list[tuple[str, str]]:
###     """
###     An example job that just prints 'hello' from within both LMS and CMS.
###     """
###     return [
###         ("lms", f"echo 'Hello from LMS, {name}!'"),
###         ("cms", f"echo 'Hello from CMS, {name}!'"),
###     ]


# Then, add the command function to CLI_DO_COMMANDS:
## hooks.Filters.CLI_DO_COMMANDS.add_item(say_hi)

# Now, you can run your job like this:
#   $ tutor local do say-hi --name="Ahmed Khalid"


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
        "repository": "https://github.com/eemaanamir/frontend-app-messenger.git",
        "port": 2010,
        "version": "develop",
    }
    return mfes
