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

from gi.repository import Gtk, Adw, Gio

from yumex.constants import rootdir, app_id, PACKAGE_COLUMNS
from yumex.ui.pachage_view import YumexPackageView
from yumex.utils import log


@Gtk.Template(resource_path=f"{rootdir}/ui/window.ui")
class YumexMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "YumexMainWindow"

    content_packages = Gtk.Template.Child()
    clamp_packages = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    main_view = Gtk.Template.Child()
    content_groups = Gtk.Template.Child("content_groups")
    content_queue = Gtk.Template.Child("content_queue")
    main_menu = Gtk.Template.Child("main-menu")
    sidebar = Gtk.Template.Child()
    package_filter = Gtk.Template.Child()
    filter_available = Gtk.Template.Child()
    stack = Gtk.Template.Child("view_stack")
    search_button = Gtk.Template.Child("search-button")
    search_bar = Gtk.Template.Child("search_bar")
    sidebar_button = Gtk.Template.Child("sidebar-button")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = kwargs["application"]
        self.settings = Gio.Settings(app_id)
        # save settings on windows close
        self.connect("unrealize", self.save_window_props)
        # connect to changes on Adw.ViewStack
        self.stack.get_pages().connect("selection-changed", self.on_stack_changed)
        self.setup_gui()

    def save_window_props(self, *args):
        win_size = self.get_default_size()

        # Save windows size
        self.settings.set_int("window-width", win_size.width)
        self.settings.set_int("window-height", win_size.height)

        # Save coloumn widths
        for setting in PACKAGE_COLUMNS:
            width = getattr(self.package_view, f"{setting}s").get_fixed_width()
            width = self.settings.set_int(f"col-{setting}-width", width)

        self.settings.set_boolean("window-maximized", self.is_maximized())
        self.settings.set_boolean("window-fullscreen", self.is_fullscreen())

    def setup_gui(self):
        self.setup_package_page()
        self.setup_groups_page()
        self.setup_queue()

    def setup_package_page(self):
        """Setup the packages page"""
        self.package_view = YumexPackageView(self)
        self.content_packages.set_child(self.package_view)
        # set columns width from settings and calc clamp width
        clamp_width = 100
        for setting in PACKAGE_COLUMNS:
            width = self.settings.get_int(f"col-{setting}-width")
            getattr(self.package_view, f"{setting}s").set_fixed_width(width)
            clamp_width += width
        self.clamp_packages.set_maximum_size(clamp_width)
        self.clamp_packages.set_tightening_threshold(clamp_width)

    def setup_groups_page(self):
        """Setup the groups page"""
        self.content_groups.append(self.create_label_center("Groups"))

    def setup_queue(self):
        """Setup the groups page"""
        self.content_queue.append(self.create_label_center("Action Queue"))

    def show_message(self, title, timeout=1):
        toast = Adw.Toast(title=title)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
        return toast

    def create_label_center(self, label):
        lbl = Gtk.Label()
        lbl.props.hexpand = True
        lbl.props.vexpand = True
        lbl.props.label = label
        lbl.add_css_class("page_label")
        lbl.add_css_class("accent")
        return lbl

    @Gtk.Template.Callback()
    def on_apply_actions_clicked(self, *_args):
        self.show_message("Apply pressed")

    @Gtk.Template.Callback()
    def on_search_changed(self, widget):
        search_txt = widget.get_text()
        log(f"search changed : {search_txt}")
        if search_txt:
            # remove selection in package filter (sidebar)
            self.package_filter.unselect_all()
            self.package_view.search(search_txt)

    @Gtk.Template.Callback()
    def on_package_filter_activated(self, widget, item):
        entry = self.search_bar.get_child()
        entry.set_text("")
        match item.get_name():
            case "available":
                self.package_view.get_packages("available")
            case "installed":
                self.package_view.get_packages("installed")
            case "updates":
                self.package_view.get_packages("updates")

        self.sidebar.set_reveal_flap(False)
        # self.show_message(f"package filter : {item.get_name()} selected")

    def show_on_packages_page(self, show=False):
        """show/hide widget only used on packages page"""
        self.search_button.set_visible(show)
        self.search_bar.set_visible(show)
        self.sidebar_button.set_visible(show)

    def on_stack_changed(self, widget, position, n_items):
        """Called when the stack page is changed"""
        active_name = self.stack.get_visible_child_name()
        log(f"stack changed : {active_name}")
        match active_name:
            case "packages":
                self.show_on_packages_page(show=True)
            case "groups":
                self.show_on_packages_page(show=False)
            case "queue":
                self.show_on_packages_page(show=False)
