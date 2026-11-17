import os

import pytest

from titlecheck.i18n import set_lang

# The tests describe the combined app. A deployment's own site settings (the separate HomeKeep Pro project sets
# PRO_SITE=on) must not leak into them, so they're cleared before any test module imports the app.
for _name in ("PRO_SITE", "HOMEKEEP_FREE_URL", "PRO_SIGNUP", "PRO_DEMO"):
    os.environ.pop(_name, None)


@pytest.fixture(autouse=True)
def english_by_default():
    """Each test starts in English, even if an earlier test's page request switched the language."""
    set_lang("en")
    yield
    set_lang("en")
