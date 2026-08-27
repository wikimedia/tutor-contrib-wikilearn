import os
from glob import glob

import click
import subprocess
import importlib_resources
from tutor import hooks
from tutormfe.hooks import MFE_APPS

from tutormfe.hooks import PLUGIN_SLOTS

from .__about__ import __version__
from .constants import *


########################################
# CONFIGURATION
########################################

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        # Prefix your setting names with 'WIKILEARN_'.
        ("WIKILEARN_VERSION", __version__),
        ("WIKILEARN_EDX_FEATURES_VERSION", WIKILEARN_EDX_FEATURES_VERSION),
        ("EMAIL_ADMIN", 'email_admin'),
        # Wiki Meta translation bot password. Default is the dev/test-wiki
        # credential; override in the environment's config.yml on prod.
        ("WIKILEARN_WIKI_META_API_PASSWORD", "3dlyW!k!L3@rn#2020"),
        # --- Credentials / verifiable-credentials sync (see the `sync-credentials`
        # do-command below) ---
        # Discovery partner code, passed to `refresh_course_metadata`. It is
        # environment-specific: "openedx" for `tutor local`/prod, "dev" for
        # `tutor dev`. The default matches prod; override it in the dev config.yml
        # (WIKILEARN_CREDENTIALS_SYNC_PARTNER_CODE: dev) when testing there.
        ("WIKILEARN_CREDENTIALS_SYNC_PARTNER_CODE", "openedx"),
        # How many days back the certificate backfill (`notify_credentials`)
        # re-sends. Keep this >= the cron interval so that a single missed/failed
        # run self-heals on the next one (a daily cron with a 2-day window overlaps).
        ("WIKILEARN_CREDENTIALS_SYNC_LOOKBACK_DAYS", 2),
        # Whether to render the k8s CronJob that runs `sync-credentials` on a
        # schedule (see patches/k8s-deployments). Only has any effect under
        # `tutor k8s` (staging/prod); ignored by local/dev docker-compose. Set to
        # false to disable the scheduled sync for an environment.
        ("WIKILEARN_CREDENTIALS_SYNC_ENABLED", True),
        # Cron schedule (UTC) for the k8s Credentials-sync CronJob. Default: daily
        # at 02:00. Must stay narrower than LOOKBACK_DAYS so runs overlap.
        ("WIKILEARN_CREDENTIALS_SYNC_SCHEDULE", "0 2 * * *"),
    ]
)

hooks.Filters.CONFIG_OVERRIDES.add_items(
    [
        # Override any default setting values here.
        ("EDX_PLATFORM_REPOSITORY", "https://github.com/wikimedia/edx-platform.git"),
        ("EDX_PLATFORM_VERSION", WIKILEARN_EDX_PLATFORM_VERSION),
        ("DEV_PROJECT_NAME", "wikilearn-dev"),
        # Pull translations from the Wikimedia fork (upstream + custom overrides,
        # e.g. the ar_MA / Moroccan Arabic locale) instead of openedx/openedx-translations.
        ("ATLAS_REPOSITORY", "wikimedia/openedx-translations"),
        ("ATLAS_REVISION", "release/teak"),
    ]
)

hooks.Filters.ENV_PATTERNS_IGNORE.add_items([
    r"(.*/)?ace_common/edx_ace/common/base_body.html(/.*)?"
])

hooks.Filters.ENV_PATCHES.add_items(
    [
        (
            "mfe-dockerfile-post-npm-install-discussions",
            f"""
RUN npm install frontend-plugins-wikilearn@{WIKILEARN_FRONTEND_PLUGINS_VERSION}
""",
        ),
        (
            "mfe-env-config-runtime-definitions-discussions",
            """
const { UsernameMention } = await import('frontend-plugins-wikilearn');
""",
        ),
    ]
)


PLUGIN_SLOTS.add_items(
    [
        (
            "discussions",
            "user_mention_plugin",
            """
        {
          op: PLUGIN_OPERATIONS.Insert,
          widget: {
            id: 'user_mention_plugin',
            type: DIRECT_PLUGIN,
            priority: 60,
            RenderWidget: UsernameMention,
          },
        }""",
        )
    ]
)


########################################
# INIT TASKS
########################################

# WikiLearn sets COURSE_DISCOVERY_FILTERS = ["language", "pace_type", "topic"]
# (see patches/openedx-lms-common-settings), but edx-search hardcodes the
# `course_info` Meilisearch index filterable attributes and does NOT include
# `pace_type`/`topic`. Without this, the catalog page fails with:
#   MeilisearchApiError: attributes `pace_type, topic` are not filterable
# This init task adds them on every `tutor ... do init`. It is idempotent:
# update_index_filterables() unions (never removes), and get_or_create makes
# it safe whether or not the index already exists.
hooks.Filters.CLI_DO_INIT_TASKS.add_item(
    (
        "lms",
        """
echo "WikiLearn: ensuring course_info filterable attributes (pace_type, topic)..."
./manage.py lms shell -c "
from search.meilisearch import (
    get_meilisearch_client,
    get_meilisearch_index_name,
    get_or_create_meilisearch_index,
    update_index_filterables,
)
client = get_meilisearch_client()
index = get_or_create_meilisearch_index(client, get_meilisearch_index_name('course_info'))
update_index_filterables(client, index, ['pace_type', 'topic'])
print('WikiLearn: course_info filterable attributes ensured.')
"
""",
    )
)

# Verifiable-credential issuance is gated behind a CredentialsApiConfig row in the
# LMS (openedx.core.djangoapps.credentials). Without it, every certificate ->
# Credentials signal handler (award_course_certificate, etc.) and the event-bus
# consumers silently no-op, so no credential is ever created. This is a core LMS
# model, so the task is safe even when the `credentials` plugin is disabled; it only
# has an effect once the Credentials service is running. Idempotent: it only creates
# the row when issuance is not already enabled, so it is safe on every `... do init`.
hooks.Filters.CLI_DO_INIT_TASKS.add_item(
    (
        "lms",
        """
echo "WikiLearn: enabling Credentials issuance (CredentialsApiConfig)..."
./manage.py lms shell -c "
from openedx.core.djangoapps.credentials.models import CredentialsApiConfig
config = CredentialsApiConfig.current()
if not (config.enabled and config.enable_learner_issuance):
    CredentialsApiConfig.objects.create(enabled=True, enable_learner_issuance=True)
print('WikiLearn: CredentialsApiConfig.is_learner_issuance_enabled =', CredentialsApiConfig.current().is_learner_issuance_enabled)
"
""",
    )
)


#######################################
# CUSTOM "do" JOBS (run inside containers)
#######################################

# `tutor <local|dev|k8s> do sync-credentials`
#
# Syncs the course catalog LMS -> Discovery -> Credentials, then backfills any
# certificate credentials the real-time signal / event-bus path may have missed.
# This is the single unit the nightly cron runs on staging/prod (see README).
#
# Steps run in order because each feeds the next:
#   1. Discovery pulls courses/course-runs from the LMS.
#   2. LMS refreshes its program cache from Discovery.
#   3. Credentials pulls the catalog from Discovery. Issuance FAILS for a course
#      run that is not in the Credentials catalog ("CourseRun doesn't exist in the
#      catalog"), so this must run before / alongside issuance.
#   4. LMS re-sends certificate changes from the last N days as a safety net for
#      anything the live signal / event-bus path dropped.
#
# Tutor renders each returned command string as a Jinja template (with the full
# config) before running it, so the config values below are substituted at run time.
@click.command(
    name="sync-credentials",
    help="Sync catalog (LMS->Discovery->Credentials) and backfill certificate credentials.",
)
def sync_credentials():
    return [
        (
            "discovery",
            "./manage.py refresh_course_metadata"
            " --partner_code={{ WIKILEARN_CREDENTIALS_SYNC_PARTNER_CODE }}",
        ),
        ("lms", "./manage.py lms cache_programs"),
        ("credentials", "./manage.py copy_catalog"),
        (
            "lms",
            "./manage.py lms notify_credentials --start-date"
            " \"$(date -u -d '{{ WIKILEARN_CREDENTIALS_SYNC_LOOKBACK_DAYS }} days ago' +%Y-%m-%d)\"",
        ),
    ]


hooks.Filters.CLI_DO_COMMANDS.add_item(sync_credentials)


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
            "tutor plugins enable mfe indigo notes forum credentials",
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


@MFE_APPS.add()
def _add_my_mfe(mfes):  # type: ignore[no-untyped-def]
    mfes["messenger"] = {
        "repository": "https://github.com/wikimedia/frontend-app-messenger.git",
        "port": 2010,
        "version": WIKILEARN_MESSENGER_MFE_VERSION,
    }
    mfes["discussions"] = {
        "repository": "https://github.com/edly-io/frontend-app-discussions.git",
        "port": 2002,
        "version": WIKILEARN_DISCUSSIONS_MFE_VERSION,
    }
    mfes["account"] = {
        "repository": "https://github.com/edly-io/frontend-app-account.git",
        "port": 1997,
        "version": WIKILEARN_ACCOUNT_MFE_VERSION,
    }
    mfes["learning"] = {
        "repository": "https://github.com/wikimedia/edx-frontend-app-learning.git",
        "port": 2000,
        "version": WIKILEARN_LEARNING_MFE_VERSION,
    }
    mfes["authoring"] = {
        "repository": "https://github.com/edly-io/frontend-app-authoring.git",
        "port": 2001,
        "version": WIKILEARN_AUTHORING_MFE_VERSION,
    }
    mfes["gradebook"] = {
        "repository": "https://github.com/edly-io/frontend-app-gradebook.git",
        "port": 1994,
        "version": WIKILEARN_GRADEBOOK_MFE_VERSION,
    }
    mfes.pop("authn")
    return mfes
