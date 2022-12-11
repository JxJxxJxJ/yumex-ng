from gi.repository import Gtk

from yumex.constants import rootdir
from yumex.utils import log  # noqa: F401


@Gtk.Template(resource_path=f"{rootdir}/ui/package_filter.ui")
class YumexPackageFilter(Gtk.Box):
    __gtype_name__ = "YumexPackageFilter"

    filter_available = Gtk.Template.Child()
    filter_installed = Gtk.Template.Child()
    filter_updates = Gtk.Template.Child()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)
        self.win = win
        self.setting = win.settings
        self.current_pkg_filter = None
        self.previuos_pkg_filter = None

    @Gtk.Template.Callback()
    def on_package_filter_toggled(self, button):
        state = button.get_active()
        if state:
            log(f"name : {button.get_name()} state: {state}")
            self.on_package_filter_activated(button)

    def on_package_filter_activated(self, button):
        entry = self.win.search_bar.get_child()
        entry.set_text("")
        pkg_filter = button.get_name()
        match pkg_filter:
            case "available":
                self.win.package_view.get_packages("available")
            case "installed":
                self.win.package_view.get_packages("installed")
            case "updates":
                self.win.package_view.get_packages("updates")
            case _:
                log(f"package_filter not found : {pkg_filter}")
        self.current_pkg_filer = pkg_filter
        self.previuos_pkg_filer = pkg_filter
        # self.show_message(f"package filter : {item.get_name()} selected")
