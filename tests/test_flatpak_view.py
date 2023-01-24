import gi


gi.require_version("Flatpak", "1.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from dataclasses import dataclass
import pytest
import os
from yumex.constants import PKGDATADIR
from yumex.utils.enums import FlatpakLocation
from yumex.backend.flatpak import FlatpakPackage
from .mock import Mock, MockFlatpakRef

pytestmark = pytest.mark.guitest


class MockWindow(Mock):
    def set_needs_attention(self, *args, **kwargs):
        self.set_mock_call("set_needs_attention", *args, **kwargs)

    def confirm_flatpak_transaction(self, *args, **kwargs):
        self.set_mock_call("confirm_flatpak_transaction", args, kwargs)
        return True

    def hide(self):
        self.set_mock_call("progress.hide")


class MockFlatpackBackend(Mock):
    def get_installed(self, *args, **kwargs):
        self.set_mock_call("get_installed", *args, **kwargs)
        return [
            FlatpakPackage(
                MockFlatpakRef(), location=FlatpakLocation.USER, is_update=True
            )
        ]

    def install(self, *args, **kwargs):
        self.set_mock_call("install", *args, **kwargs)
        return [
            FlatpakPackage(
                MockFlatpakRef(), location=FlatpakLocation.USER, is_update=True
            )
        ]

    def number_of_updates(self):
        return 1


@dataclass
class MockFlatpakPackage:
    id: str = "org.gnome.design.Contrast"


@pytest.fixture(autouse=True)
def mock_backend(monkeypatch):
    """use a mock backend"""
    monkeypatch.setattr(
        "yumex.backend.flatpak.backend.FlatpakBackend", MockFlatpackBackend
    )


@pytest.fixture
def window():
    """use a mock window"""
    return MockWindow()


@pytest.fixture
def flatpak_view(window):
    """setup ressources and create a YumexFlatpakView object"""
    from gi.repository import Gio

    resource = Gio.Resource.load(os.path.join(PKGDATADIR, "yumex.gresource"))
    Gio.Resource._register(resource)
    from yumex.ui.flatpak_view import YumexFlatpakView

    fpw: YumexFlatpakView = YumexFlatpakView(window)
    return fpw


@pytest.fixture
def package():
    return MockFlatpakPackage()


def test_backend_mock(flatpak_view):
    """Test that the backend is mocked."""
    assert isinstance(flatpak_view.backend, MockFlatpackBackend)


def test_backend_set_needs_attention(flatpak_view):
    """Test that the win.set_needs_attention is called with one update"""
    calls = flatpak_view.win.get_mock_call("set_needs_attention")
    assert len(calls) == 1
    assert calls[0] == "set_needs_attention(flatpaks,1)"


def test_backend_get_installed_called(flatpak_view):
    """Test that backend,get_installed is called"""
    assert isinstance(flatpak_view.backend, MockFlatpackBackend)
    calls = flatpak_view.backend.get_mock_call("get_installed")
    assert len(calls) == 1
    assert calls[0] == "get_installed(location=both)"


def test_get_icon_paths(flatpak_view):
    assert isinstance(flatpak_view.backend, MockFlatpackBackend)
    paths = flatpak_view.get_icon_paths()
    for path in paths:
        assert "/icons/" in path


def test_find_icon(flatpak_view, package):
    # if org.gnome.design.Contrast is install we get a path
    path = flatpak_view.find_icon(package)
    if path:
        assert package.id in path
    notfound = MockFlatpakPackage(id="xx.xxxxxx.notfound")
    path = flatpak_view.find_icon(notfound)
    assert path is None


# def test_view_do_transaction(flatpak_view):
#     """Test that backend,install is called"""
#     flatpak_view.do_transaction(flatpak_view.backend.install, None)
#     assert flatpak_view.backend.get_number_of_calls() == 2
