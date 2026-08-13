"""`.adalab/` folder integrity — the checks AdaLab's own tooling runs before a deploy.

These exist because every one of them fails *late*: at build or deploy time, often in front of
a class. Running them as tests means a broken manifest can't leave the repo.

The rules encoded here (from the AdaLab app-builder guidance):

* `project.json` exists, parses, and declares `type: "appBuilder"`.
* `app.json` exists and parses; `app_url` matches the platform regex and length limit.
* Every container filename's integer suffix **equals the `uid` inside it** — a file named
  after the image instead of the uid is the documented cause of duplicate-container deploys.
* `uid`s and `container_image_name`s are unique across all container files.
* Exactly one container is `primary_container: true` (the API rejects anything else).
* No reserved environment-variable names (the platform injects those itself).
* Resource requests stay inside the platform caps, and are big enough for this app.
* `volume_mounts` paths are relative to `/asv-mnt/` with no leading or trailing slash.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ADALAB = Path(__file__).resolve().parent.parent / ".adalab"

APP_URL_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
IMAGE_NAME_RE = re.compile(r"^[a-zA-Z0-9_:-]{2,255}$")
RESERVED_ENV = {"_UA_CLIENT_ID", "_UA_CLIENT_SECRET", "_NAMESPACE"}
CONTAINER_RE = re.compile(r"^(local|external)_container_(\d+)\.json$")
# Platform caps.
MAX_CPU_CAP, MAX_RAM_CAP = 2, 2000
# This app runs Streamlit + pandas + plotly + reportlab in one container; 500 MB (the
# scaffold default) is not enough headroom for report rendering.
MIN_SENSIBLE_RAM = 1000


def _load(name: str) -> dict:
    path = ADALAB / name
    assert path.is_file(), f".adalab/{name} is missing"
    return json.loads(path.read_text(encoding="utf-8"))


def container_files() -> list[Path]:
    return sorted(p for p in ADALAB.glob("*_container_*.json"))


# --- project.json -----------------------------------------------------------
def test_project_json_declares_app_builder():
    data = _load("project.json")
    assert data["type"] == "appBuilder"
    assert "id" in data and data["id"] is None
    assert "author" in data, "project.json should record the owning AdaLab user"


# --- app.json ---------------------------------------------------------------
def test_app_json_shape():
    app = _load("app.json")
    for key in ("app_id", "app_name", "app_description", "app_url", "stripped_prefix",
                "access_level", "acl_userlist", "acl_group_names", "idp_enabled",
                "idp_scope", "maintainers"):
        assert key in app, f"app.json is missing {key}"
    assert app["app_id"] is None, "app_id is managed by the deploy flow; ship it null"


def test_app_url_is_valid_and_within_limits():
    app_url = _load("app.json")["app_url"]
    assert APP_URL_RE.match(app_url), f"app_url {app_url!r} breaks the platform regex"
    assert len(app_url) <= 63, "app_url must be 63 characters or fewer"


def test_access_control_is_coherent():
    app = _load("app.json")
    # Students have no AdaLab accounts — the course password is the gate (Addendum B §B2).
    assert app["access_level"] == "public"
    assert app["acl_userlist"] == [], "acl_userlist must be empty unless access_level=userlist"
    assert app["acl_group_names"] == [], "acl_group_names must be empty unless access_level=group"
    assert app["idp_enabled"] is False and app["idp_scope"] is None


def test_stripped_prefix_matches_how_streamlit_is_served():
    """Streamlit is run with --server.baseUrlPath, so the prefix must NOT be stripped.

    The platform's rule is: either the app is prefix-aware and stripped_prefix is false, or it
    serves at the root and stripped_prefix is true — never mixed. Mixing gives 404s on assets
    and a websocket that will not connect. See HANDOVER §B1.
    """
    assert _load("app.json")["stripped_prefix"] is False
    containerfile = (ADALAB.parent / "Containerfile").read_text(encoding="utf-8")
    assert "--server.baseUrlPath" in containerfile, (
        "stripped_prefix is false, so the app must be told its prefix")


# --- container files --------------------------------------------------------
def test_at_least_one_container_file_exists():
    assert container_files(), ".adalab needs at least one container file"


def test_filename_suffix_equals_uid():
    """A file named after the image instead of the uid causes duplicate-container deploys."""
    for path in container_files():
        match = CONTAINER_RE.match(path.name)
        assert match, (
            f"{path.name} must be named <local|external>_container_<uid>.json with an "
            f"INTEGER suffix matching its uid field")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data["uid"], int), f"{path.name}: uid must be a number, not a string"
        assert int(match.group(2)) == data["uid"], (
            f"{path.name}: filename suffix {match.group(2)} != uid {data['uid']}")


def test_uids_and_image_names_are_unique():
    uids, names = [], []
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        uids.append(data["uid"])
        names.append(data["container_image_name"])
    assert len(uids) == len(set(uids)), f"duplicate uid across container files: {uids}"
    assert len(names) == len(set(names)), f"duplicate container_image_name: {names}"


def test_exactly_one_primary_container():
    primaries = [p.name for p in container_files()
                 if json.loads(p.read_text(encoding="utf-8")).get("primary_container")]
    assert len(primaries) == 1, f"exactly one primary container required, found {primaries}"


def test_image_name_and_build_inputs_are_valid():
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert IMAGE_NAME_RE.match(data["container_image_name"]), \
            f"{path.name}: container_image_name breaks the registry regex"
        if path.name.startswith("local_container_"):
            container_file = ADALAB.parent / data["container_file"]
            assert container_file.is_file(), (
                f"{path.name}: container_file {data['container_file']!r} does not exist "
                f"(path is relative to the repo root)")
            assert (ADALAB.parent / data["build_context"]).is_dir()
            assert data["metadata_id"] is None, "metadata_id is managed by the deploy flow"
            assert data["image_version"]["current_image_version"] is None


def test_primary_container_port_matches_the_app():
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("primary_container"):
            assert data["port"] == 8000, "the app serves on 8000 (Addendum A §A1)"


def test_resources_are_within_caps_and_adequate():
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert 0 <= data["min_cpu"] <= data["max_cpu"] <= MAX_CPU_CAP
        assert 0 <= data["min_ram"] <= data["max_ram"] <= MAX_RAM_CAP
        if data.get("primary_container"):
            assert data["max_ram"] >= MIN_SENSIBLE_RAM, (
                f"{path.name}: {data['max_ram']} MB is tight for Streamlit + pandas + plotly "
                f"+ PDF rendering; raise it (cap is {MAX_RAM_CAP})")


def test_no_reserved_environment_variables():
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = {e["key"] for e in data.get("environment_variables", [])}
        clash = keys & RESERVED_ENV
        assert not clash, f"{path.name}: {clash} are injected by the platform — remove them"


def test_secrets_are_not_committed_in_the_manifest():
    """COURSE_PASSWORD / ADMIN_PASSWORD are set in the deploy wizard, never in git."""
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("environment_variables", []):
            assert "PASSWORD" not in entry["key"].upper() or not entry["value"], (
                f"{path.name}: {entry['key']} has a value committed to the repo")


def test_volume_mount_paths_are_relative_to_asv_mnt():
    """mount_path is the part AFTER /asv-mnt/ — a leading slash doubles it, a trailing slash
    is rejected outright by the API."""
    for path in container_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for mount in data.get("volume_mounts", []):
            mp = mount["mount_path"]
            assert not mp.startswith("/"), f"{path.name}: mount_path {mp!r} must not start with /"
            assert not mp.endswith("/"), f"{path.name}: mount_path {mp!r} must not end with /"
        directs = [m for m in data.get("volume_mounts", []) if m.get("direct")]
        assert len(directs) <= 1, "at most one Fast Mount per app"


def test_data_dir_default_matches_the_documented_mount_path():
    """DATA_DIR must line up with /asv-mnt/<mount_path> or the app fails loud on first run."""
    from core.config import DEFAULT_DATA_DIR

    assert DEFAULT_DATA_DIR.startswith("/asv-mnt/"), DEFAULT_DATA_DIR
    mount_path = DEFAULT_DATA_DIR[len("/asv-mnt/"):]
    assert mount_path and "/" not in mount_path.rstrip("/"), (
        "the mount_path to enter in the deploy wizard should be a single path segment")
