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
#
# Copyright (C) 2022  Tim Lauridsen
#
#

from time import time
from typing import Union

import dnf
import dnf.yum
import dnf.const
import dnf.conf
import dnf.subject
import hawkey

from yumex.backend import YumexPackage, PackageState


class Packages:
    """
    Get access to packages in the dnf (hawkey) sack in an easy way
    """

    def __init__(self, base: dnf.Base):
        self._base = base
        self.sack = base.sack
        self.query = self.sack.query()
        self._inst_na = self.query.installed()._na_dict()
        self._update_na = self.query.upgrades()._na_dict()

    def _filter_packages(self, pkg_list: list[dnf.package.Package]):
        """
        Filter a list of package objects and replace
        the installed ones with the installed object, instead
        of the available object
        """
        pkgs = []
        for pkg in pkg_list:
            ypkg = YumexPackage(pkg)
            key = (pkg.name, pkg.arch)
            inst_pkg = self._inst_na.get(key, [None])[0]
            if inst_pkg:
                ypkg.set_installed()
            pkgs.append(ypkg)
        return pkgs

    @property
    def installed(self):
        """
        get installed packages
        """
        avail_na = self.query.available()._na_dict()
        pkgs = []
        for pkg in self.query.installed().run():
            key = (pkg.name, pkg.arch)
            repo_pkg = avail_na.get(key, [None])[0]
            if repo_pkg:
                ypkg = YumexPackage(repo_pkg)
                ypkg.set_installed()
            else:
                ypkg = YumexPackage(pkg, state=PackageState.INSTALLED)
            pkgs.append(ypkg)
        return pkgs

    @property
    def updates(self):
        """
        get available updates
        """
        return [
            YumexPackage(pkg, state=PackageState.UPDATE)
            for pkg in self.query.upgrades().run()
        ]

    def filter_installed(self, query: dnf.query.Query):
        pkgs = []
        for pkg in query.run():
            ypkg = YumexPackage(pkg)
            key = (pkg.name, pkg.arch)
            inst_pkg = self._inst_na.get(key, [None])[0]
            if inst_pkg:
                ypkg.set_installed()
            pkgs.append(ypkg)
        return pkgs

    @property
    def available(self) -> list[YumexPackage]:
        """
        newest available packages
        mark the installed ones
        """
        return self.filter_installed(query=self.query.available().latest())

    @property
    def extras(self):
        """
        installed packages, not in current repos
        """
        # anything installed but not in a repo is an extra
        avail_dict = self.query.available().pkgtup_dict()
        inst_dict = self.query.installed().pkgtup_dict()
        pkgs = []
        for pkgtup in inst_dict:
            if pkgtup not in avail_dict:
                pkgs.extend(inst_dict[pkgtup])
        return pkgs

    @property
    def obsoletes(self):
        """
        packages there is obsoleting some installed packages
        """
        inst = self.query.installed()
        return self.query.filter(obsoletes=inst)

    @property
    def recent(self, showdups=False):
        """
        Get the recent packages
        """
        recent = []
        now = time()
        recentlimit = now - (self._base.conf.recent * 86400)
        if showdups:
            avail = self.query.available()
        else:
            avail = self.query.latest()
        for po in avail:
            if int(po.buildtime) > recentlimit:
                recent.append(po)
        return recent

    def search(self, txt: str, field="name"):
        q = self.query.available()
        # field like *txt* and arch != src
        match field:
            case "name":
                fdict = {f"{field}__substr": txt, "arch__neq": "src"}
            case "summary":
                fdict = {f"{field}__substr": txt, "arch__neq": "src"}
            case _:
                fdict = {f"{field}": txt}

        try:
            q = q.filter(hawkey.ICASE, **fdict).latest()
            return self.filter_installed(query=q)
        except AssertionError:
            return []

    def find_package(self, pkg: YumexPackage) -> dnf.package.Package:
        """Get the package from given package id."""
        q = self.query
        if pkg.repo.startswith("@"):  # installed package
            f = q.installed()
            f = f.filter(
                name=pkg.name, version=pkg.version, release=pkg.release, arch=pkg.arch
            )
            if len(f) > 0:
                return f[0]
            else:
                return None
        else:
            f = q.available()
            f = f.filter(
                name=pkg.name, version=pkg.version, release=pkg.release, arch=pkg.arch
            )
            if len(f) > 0:
                return f[0]
            else:
                return None


class DnfBase(dnf.Base):
    """
    class to encapsulate and extend the dnf.Base API
    """

    def __init__(self, setup_sack=False):
        dnf.Base.__init__(self)
        # setup the dnf cache
        RELEASEVER = dnf.rpm.detect_releasever(self.conf.installroot)
        self.conf.substitutions["releasever"] = RELEASEVER
        # read the repository infomation
        self._packages = None
        self.read_all_repos()
        if setup_sack:
            # populate the dnf sack
            self.fill_sack()
            self._packages = Packages(self)  # Define a Packages object

    def setup_base(self):
        self.fill_sack()
        self._packages = Packages(self)  # Define a Packages object

    @property
    def packages(self):
        """property to get easy acceess to packages"""
        if not self._packages:
            self.setup_base()
        return self._packages

    def cachedir_fit(self):
        conf = self.conf
        subst = conf.substitutions
        # this is not public API, same procedure as dnf cli
        suffix = dnf.conf.parser.substitute(dnf.const.CACHEDIR_SUFFIX, subst)
        cli_cache = dnf.conf.CliCache(conf.cachedir, suffix)
        return cli_cache.cachedir, cli_cache.system_cachedir

    def setup_cache(self):
        """Setup the dnf cache, same as dnf cli"""
        conf = self.conf
        conf.substitutions["releasever"] = dnf.rpm.detect_releasever("/")
        conf.cachedir, self._system_cachedir = self.cachedir_fit()
        print("cachedir: %s" % conf.cachedir)


class Backend(DnfBase):
    """
    Package backend base on dnf 4.x python API
    """

    def __init__(self):
        DnfBase.__init__(self)

    def get_packages(self, pkg_filter: str) -> list[YumexPackage]:
        match pkg_filter:
            case "available":
                return self.packages.available
            case "installed":
                return self.packages.installed
            case "updates":
                return self.packages.updates
            case _:
                return []

    def search(self, txt: str, field: str = "name") -> list[YumexPackage]:
        return self.packages.search(txt, field=field)

    def get_package_info(self, pkg: YumexPackage, attr: str) -> Union[str, None]:
        found = self.packages.find_package(pkg)
        if found:
            if hasattr(found, attr):
                return getattr(found, attr)
        return None

    def get_repositories(self):
        repos = self.repos.all()
        for repo in repos:
            if not repo.id.endswith("-source") and not repo.id.endswith("-debuginfo"):
                yield (repo.id, repo.name, repo.enabled)
