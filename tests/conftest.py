import pytest

from titlecheck.i18n import set_lang


@pytest.fixture(autouse=True)
def english_by_default():
    """Each test starts in English, even if an earlier test's page request switched the language."""
    set_lang("en")
    yield
    set_lang("en")
