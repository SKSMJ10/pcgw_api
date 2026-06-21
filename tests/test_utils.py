from app.scraper.utils import sluggify


def test_normal_string():
    assert sluggify("Half-Life 2") == "half-life-2"


def test_special_characters():
    assert (
        sluggify("Command & Conquer: Generals – Zero Hour")
        == "command-conquer-generals-zero-hour"
    )
    assert sluggify("007:First Light") == "007-first-light"
    assert sluggify("!@#$%^&*()") == ""


def test_trailing_leading_chars():
    assert sluggify("!Test-String!") == "test-string"
    assert sluggify("-----Test---Dashes-----") == "test-dashes"


def test_empty_string():
    assert sluggify("") == ""


def test_spaces_and_hyphens():
    assert sluggify("A   B---C") == "a-b-c"


def test_numbers():
    assert sluggify("123 456") == "123-456"
