#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# builder.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

"""
A visitor to build the urwid TUI from the abstract UI definitions.
Is based on the visitor pattern
"""

import urwid

import logging

import ovirt.node.exceptions
from ovirt.node import ui

LOGGER = logging.getLogger(__name__)


def page_from_plugin(tui, plugin):
    element = plugin.ui_content()
    widget = None

    # FIXME could also be done using dict.
    if type(element) is ui.Page:
        widget = build_page(tui, plugin, element)
    else:
        raise Exception("Unknown element container: %s" % element)

    return widget


def build_page(tui, plugin, container):
    widgets = []

    for path, item in container.children:
        widget = widget_for_item(tui, plugin, path, item)
        widgets.append(("flow", widget))

    # Add buttons
    button_widgets = []
    for path, item in container.buttons:
        assert type(item) in [ui.SaveButton, ui.ResetButton, ui.CloseButton,
                              ui.Button]
        button_widgets.append(build_button(path, item, tui, plugin))

    if button_widgets:
        widgets.append(urwid.Filler(urwid.Columns(button_widgets)))

    widgets.append(urwid.Filler(urwid.Text("")))

    LOGGER.debug("Triggering initial sematic checks for '%s'" % plugin)
    try:
        plugin.check_semantics()
    except:
        tui.notify("error", "Initial model validation failed.")

    page = ui.widgets.PageWidget(widgets)
    page.plugin = plugin

    return page


def widget_for_item(tui, plugin, path, item):
    item_to_builder = {
        ui.Header: build_label,

        ui.Label: build_label,
        ui.KeywordLabel: build_label,

        ui.Entry: build_entry,
        ui.PasswordEntry: build_entry,

        ui.Button: build_button,
        ui.SaveButton: build_button,
        ui.ResetButton: build_button,

        ui.Options: build_options,
        ui.ProgressBar: build_progressbar,
        ui.Table: build_table,
        ui.Checkbox: build_checkbox,

        ui.Divider: build_divider,
        ui.Row: build_row,
    }

    # Check if builder is available for UI Element
    assert type(item) in item_to_builder, "No widget for item type"

    # Build widget from UI Element
    build_func = item_to_builder[type(item)]
    widget = build_func(path, item, tui, plugin)

    # Populate with values
    if type(item) in [ui.Entry,
                      ui.PasswordEntry,
                      ui.Label,
                      ui.KeywordLabel,
                      ui.Options,
                      ui.Checkbox]:
        model = plugin.model()
        if path in model:
            text = model[path]
            widget.set_text(text)

    return widget


def build_entry(path, item, tui, plugin):
    widget_class = None
    if type(item) is ui.Entry:
        widget_class = ui.widgets.Entry
    else:
        widget_class = ui.widgets.PasswordEntry

    widget = widget_class(item.label, align_vertical=item.align_vertical)
    widget.enable(item.enabled())

    def on_item_enabled_change_cb(w, v):
        LOGGER.debug("Element changed, updating entry '%s': %s" % (w, v))
        if widget.selectable() != v:
            widget.enable(v)
        if v == False:
            widget.notice = ""
            widget.valid(True)

    item.connect_signal("enabled", on_item_enabled_change_cb)

    def on_widget_value_change(widget, new_value):
        LOGGER.debug("Entry %s changed, calling callback: '%s'" % (widget,
                                                                   path))

        try:
            change = {path: new_value}
            plugin._on_ui_change(change)
            widget.notice = ""
            widget.valid(True)

        except ovirt.node.exceptions.Concern as e:
            LOGGER.error("Concern when updating: %s" % e)

        except ovirt.node.exceptions.InvalidData as e:
            LOGGER.error("Invalid data when updating: %s" % e)
            if widget._selectable:
                widget.notice = e.message
            widget.valid(False)

        tui._draw_screen()
    urwid.connect_signal(widget, 'change', on_widget_value_change)

    return widget


def build_label(path, item, tui, plugin):
    if type(item) is ui.KeywordLabel:
        widget = ui.widgets.KeywordLabel(item.keyword,
                                                    item.text())
    elif type(item) is ui.Header:
        widget = ui.widgets.Header(item.text(), item.template)
    else:
        widget = ui.widgets.Label(item.text())

    def on_item_text_change_cb(w, v):
        LOGGER.debug("Element changed, updating label '%s': %s" % (w, v))
        widget.text(v)
        # Redraw the screen if widget text is updated "outside" of the
        # mainloop
        tui._draw_screen()
    item.connect_signal("text", on_item_text_change_cb)

    return widget


def build_button(path, item, tui, plugin):
    itemtype = type(item)
    widget = ui.widgets.Button(item.text())

    if itemtype in [ui.SaveButton]:
        def on_valid_cb(w, v):
            widget.enable(plugin.is_valid_changes())
        plugin.sig_valid.connect(on_valid_cb)
        on_valid_cb(None, None)

    def on_widget_click_cb(widget, data=None):
        LOGGER.debug("Button click: %s" % {"path": path, "widget": widget})
        if itemtype is ui.Button:
            plugin._on_ui_change({path: True})
        if itemtype in [ui.Button, ui.SaveButton]:
            r = plugin._on_ui_save()
        if itemtype in [ui.CloseButton]:
            r = tui.close_topmost_dialog()
        if itemtype in [ui.ResetButton]:
            r = plugin._on_ui_reset()
            tui._display_plugin(plugin)
        parse_plugin_result(tui, plugin, r)

#        else:
#           Not propagating the signal as a signal to the plugin
#           item.emit_signal("click", widget)
#            plugin._on_ui_change({path: True})
    urwid.connect_signal(widget, "click", on_widget_click_cb)

    return widget


def build_divider(path, item, tui, plugin):
    return ui.widgets.Divider(item.char)


def build_options(path, item, tui, plugin):
    widget = ui.widgets.Options(item.label, item.options,
                                           plugin.model()[path])

    def on_widget_change_cb(widget, data):
        item.option(data)
        LOGGER.debug("Options changed, calling callback: %s" % data)
        plugin._on_ui_change({path: data})
    urwid.connect_signal(widget, "change", on_widget_change_cb)

    return widget


def build_checkbox(path, item, tui, plugin):
    widget = ui.widgets.Checkbox(item.label, item.state())

    def on_widget_change_cb(widget, data=None):
        item.state(data)
        LOGGER.debug("Checkbox changed, calling callback: %s" % data)
        plugin._on_ui_change({path: data})

    urwid.connect_signal(widget, "change", on_widget_change_cb)
    return widget


def build_row(path, container_item, tui, plugin):
    widgets = []
    for path, element in container_item.children:
        child = widget_for_item(tui, plugin, path, element)
        widgets.append(child)

    return urwid.Columns(widgets)


def build_progressbar(path, item, tui, plugin):
    widget = ui.widgets.ProgressBarWidget(item.current(), item.done)

    def on_item_current_change_cb(w, v):
        LOGGER.debug("Model changed, updating progressbar '%s': %s" % (w, v))
        widget.set_completion(v)
        tui._draw_screen()
    item.connect_signal("current", on_item_current_change_cb)

    return widget


def build_table(path, item, tui, plugin):
    children = []
    for key, label in item.items:
        c = _build_tableitem(tui, path, plugin, key, label)
        children.append(c)
    widget = ui.widgets.TableWidget(item.label, item.header,
                                               children,
                                               item.height, item.enabled())

    def on_change_cb(w, d=None):
        plugin._on_ui_change({path: w._key})
        item.select(w._key)
    urwid.connect_signal(widget, "changed", on_change_cb)

    return widget


def _build_tableitem(tui, path, plugin, key, label):
    c = ui.widgets.TableEntryWidget(label)
    c._key = key

    def on_activate_cb(w, data):
        plugin._on_ui_change({path: w._key})
        parse_plugin_result(tui, plugin, plugin._on_ui_save())
    urwid.connect_signal(c, "activate", on_activate_cb)
    return c


def parse_plugin_result(tui, plugin, result):
        LOGGER.debug("Parsing plugin change/save result: %s" % result)

        if type(result) in [ui.Page]:
            LOGGER.debug("Page requested.")
            tui.show_page(result)

        elif type(result) in [ui.Dialog]:
            LOGGER.debug("Dialog requested.")
            dialog = tui.show_dialog(result)

            def on_item_close_changed_cb(i, v):
                dialog.close()
            result.connect_signal("close", on_item_close_changed_cb)

        return result
