import pytest
from bs4 import BeautifulSoup
from pathlib import Path
from app.scraper.game import Game


@pytest.fixture
def mock_game(request):

    test_html = request.param
    # Dummy values for testing
    game = Game(
        pid=10,
        session=None,
        BASE_URL="https://www.pcgamingwiki.com/",
        API="https://www.pcgamingwiki.com/w/api.php",
    )

    # Load the saved HTML fixture
    fixture_path = Path(__file__).parent / "fixtures" / test_html
    html_content = fixture_path.read_text(encoding="utf-8")

    game._soup = BeautifulSoup(html_content, "html.parser")
    game._title = "Test Game"
    game._page_loaded = True

    return game


@pytest.mark.parametrize(
    "mock_game,e_feature,e_state,e_notes",
    [
        ("cp_2077.html", "anisotropic-filtering-af", "Native support", "Up to 16x."),
        (
            "cp_2077.html",
            "multi-monitor",
            "Unknown",
            "The horizontal camera axis is constrained in dialogue. UI cropping issues.",
        ),
        (
            "cp_2077.html",
            "ultra-widescreen",
            "Limited native support",
            "[Hor+](https://www.pcgamingwiki.com/wiki/Glossary:Scaling)",
        ),
        (
            "cp_2077.html",
            "anti-aliasing-aa",
            "Always on (no native option)",
            "[TAA](https://www.pcgamingwiki.com/wiki/TAA)",
        ),
        (
            "doom_2016.html",
            "multi-monitor",
            "Hackable",
            "Use [Flawless Widescreen](https://www.flawlesswidescreen.org) with the [32:9/Surround Fix script](https://community.pcgamingwiki.com/files/file/1861-doom2016-aspect-ratio-329surround-fix/) for proper aspect ratio and FOV.",
        ),
        (
            "doom_2016.html",
            "color-blind-mode",
            "No native support",
            "Deuteranopia, Protanopia, and Tritanopia [Incorrect implementation, Applies filter to simulate colorblindness]",
        ),
        (
            "stardew_valley.html",
            "field-of-view-fov",
            "Not applicable",
            "You can choose to zoom in and out in the menus to see more stuff on screen.",
        ),
    ],
    indirect=["mock_game"],
)
def test_video_extraction(mock_game, e_feature, e_state, e_notes):
    result = mock_game.video()

    assert "video" in result

    video_data = result["video"]

    assert e_feature in video_data
    assert video_data[e_feature]["state"] == e_state
    assert e_notes in video_data[e_feature]["notes"]


@pytest.mark.parametrize(
    "mock_game, e_feature, e_state, e_notes",
    [
        (
            "stardew_valley.html",
            "separate-volume-controls",
            "Native support",
            "Music, Sound, Ambient, Footstep",
        ),
        (
            "stardew_valley.html",
            "surround-sound",
            "Always on (no native option)",
            "7.1",
        ),
        (
            "stardew_valley.html",
            "subtitles",
            "Not applicable",
            "All dialogue is text-only.",
        ),
        ("stardew_valley.html", "closed-captions", "No native support", None),
        (
            "stardew_valley.html",
            "royalty-free-audio",
            "Unknown",
            None,
        ),
    ],
    indirect=["mock_game"],
)
def test_audio_extraction(mock_game, e_feature, e_state, e_notes):
    result = mock_game.audio()

    assert "audio" in result
    audio_data = result["audio"]

    assert e_feature in audio_data
    assert audio_data[e_feature]["state"] == e_state
    audio_notes = audio_data[e_feature]["notes"]
    assert audio_notes is None if e_notes is None else e_notes in audio_notes


@pytest.mark.parametrize(
    "mock_game, e_type, e_system, e_location",
    [
        (
            "cp_2077.html",
            "Config_File_Location",
            "Windows",
            "[%LOCALAPPDATA%](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#User_application_data)\CD Projekt Red\Cyberpunk 2077",
        ),
        (
            "cp_2077.html",
            "Config_File_Location",
            "macOS (OS X)",
            "[$HOME](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#macOS_.28OS_X.29_paths)/Library/Application Support/CD Projekt Red/Cyberpunk 2077",
        ),
        (
            "cp_2077.html",
            "Config_File_Location",
            "Steam Play (Linux)",
            "[<SteamLibrary-folder>](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#Steam_client)/steamapps/compatdata/1091500/pfx/",
        ),
        (
            "cp_2077.html",
            "Save_Game_File_Location",
            "Windows",
            "[%USERPROFILE%](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#User_profile)\Saved Games\CD Projekt Red\Cyberpunk 2077",
        ),
        (
            "cp_2077.html",
            "Save_Game_File_Location",
            "macOS (OS X)",
            "[$HOME](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#macOS_.28OS_X.29_paths)/Library/Application Support/CD Projekt Red/Cyberpunk 2077/saves",
        ),
        (
            "cp_2077.html",
            "Save_Game_File_Location",
            "Steam Play (Linux)",
            "[<SteamLibrary-folder>](https://www.pcgamingwiki.com/wiki/Glossary:Game_data#Steam_client)/steamapps/compatdata/1091500/pfx/",
        ),
    ],
    indirect=["mock_game"],
)
def test_game_data(mock_game, e_type, e_system, e_location):
    result = mock_game.game_data()

    assert e_type in result

    location_map = dict(result[e_type])
    assert e_system in location_map
    assert location_map[e_system] == e_location


@pytest.mark.parametrize(
    "mock_game, e_type, e_name, e_support, e_notes",
    [
        (
            "cp_2077.html",
            "api",
            "direct3d",
            ("support", 12),
            "Uses D3D12on7 under Windows 7.",
        ),
        (
            "cp_2077.html",
            "api",
            "metal",
            ("support", "Native support"),
            "Metal support introduced in Update 2.3.",
        ),
        ("cp_2077.html", "executable", "windows", ("version", ["64-bit"]), None),
        (
            "cp_2077.html",
            "executable",
            "macos-os-x",
            ("version", ["ARM"]),
            "ARM support introduced in Update 2.3.",
        ),
        (
            "cp_2077.html",
            "middleware",
            "physics",
            (
                "middleware",
                "[PhysX](https://www.pcgamingwiki.com/wiki/PhysX) , [SpeedTree](https://www.pcgamingwiki.com/wiki/SpeedTree)",
            ),
            None,
        ),
        (
            "cp_2077.html",
            "middleware",
            "audio",
            ("middleware", "[Wwise](https://www.pcgamingwiki.com/wiki/Wwise)"),
            None,
        ),
        ("cp_2077.html", "middleware", "interface", ("middleware", "FreeType"), None),
        (
            "cp_2077.html",
            "middleware",
            "cutscenes",
            (
                "middleware",
                "[Bink Video](https://www.pcgamingwiki.com/wiki/Bink_Video)",
            ),
            None,
        ),
        ("stardew_valley.html", "api", "direct3d", ("support", "9.0c"), None),
        ("stardew_valley.html", "api", "opengl", ("support", "2.0"), None),
        (
            "stardew_valley.html",
            "executable",
            "windows",
            ("version", ["32-bit", "64-bit"]),
            "The legacy compatibility version on Steam is 32-bit.",
        ),
        (
            "stardew_valley.html",
            "executable",
            "linux",
            ("version", ["64-bit", "ARM (Hackable)"]),
            "ARM support: see [ValleyCore](https://github.com/a9ix/ValleyCore)",
        ),
    ],
    indirect=["mock_game"],
)
def test_api_mw(mock_game, e_type, e_name, e_support, e_notes):
    result = mock_game.api_middleware()

    assert e_type in result
    e_type_data = result[e_type]
    assert e_name in e_type_data
    e_feature = e_type_data[e_name]
    assert e_feature[e_support[0]] == e_support[1]
    assert e_notes in e_feature["notes"] if e_notes else e_notes is None
