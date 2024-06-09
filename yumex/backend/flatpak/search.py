# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2024 Tim Lauridsen

"""Backend for searching in flatpak AppStream Metadata"""

import gi

gi.require_version("AppStream", "1.0")
gi.require_version("Flatpak", "1.0")
from gi.repository import AppStream, Flatpak, Gio  # type: ignore # noqa: E402


class AppStreamPackage:
    """AppStream Package"""

    def __init__(self, comp: AppStream.Component, repo_name) -> None:
        self.component: AppStream.Component = comp
        self.repo_name: str = repo_name
        bundle: AppStream.Bundle = comp.get_bundle(AppStream.BundleKind.FLATPAK)
        self.flatpak_bundle: str = bundle.get_id()

    @property
    def name(self) -> str:
        return self.component.get_name()

    @property
    def summary(self) -> str:
        return self.component.get_summary()

    def __str__(self) -> str:
        return f"{self.name} - {self.summary} ({self.repo_name})"


class AppstreamSearcher:
    """Flatpak AppStream Package seacher"""

    def __init__(self) -> None:
        self.remotes: dict[str, list[AppStreamPackage]] = {}

    def add_installation(self, inst: Flatpak.Installation):
        """Add enabled flatpak repositories from Flatpak.Installation"""
        remotes = inst.list_remotes()
        for remote in remotes:
            if not remote.get_disabled():
                self.add_remote(remote)

    def add_remote(self, remote: Flatpak.Remote):
        """Add packages for a given Flatpak.Remote"""
        remote_name = remote.get_name()
        if remote_name not in self.remotes:
            self.remotes[remote_name] = self._load_appstream_metadata(remote)

    def _load_appstream_metadata(self, remote: Flatpak.Remote) -> list[AppStreamPackage]:
        """load AppStrean metadata and create AppStreamPackage objects"""
        packages = []
        metadata = AppStream.Metadata.new()
        metadata.set_format_style(AppStream.FormatStyle.CATALOG)
        metadata.parse_file(
            Gio.File.new_for_path(remote.get_appstream_dir().get_path() + "/appstream.xml.gz"),
            AppStream.FormatKind.XML,
        )
        components: AppStream.ComponentBox = metadata.get_components()
        i = 0
        for i in range(components.get_size()):
            component = components.index_safe(i)
            if component.get_kind() == AppStream.ComponentKind.DESKTOP_APP:
                packages.append(AppStreamPackage(component, remote.get_name()))
        return packages

    def search(self, keyword: str) -> list[AppStreamPackage]:
        """Search packages matching a keyword"""
        search_results = []
        for remote_name in self.remotes.keys():
            packages = self.remotes[remote_name]
            for package in packages:
                if package.component.search_matches(keyword) > 0:
                    search_results.append(package)
        return search_results
