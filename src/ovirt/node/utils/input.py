#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# logging_page.py - Copyright (C) 2013 Red Hat, Inc.
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

# pylint: disable-msg=E1101,E1102

from ovirt.node import base, log
import os
import select  # @UnresolvedImport
import struct
import sys
import threading
"""
Simple wrapper to Linux input
At some poitn switch to:
https://github.com/gvalkov/python-evdev/

See also:

- http://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/tree/\
Documentation/input/event-codes.txt?id=HEAD

- http://stackoverflow.com/questions/13129804/python-how-to-get-current-\
keylock-status

- http://svn.navi.cx/misc/trunk/python/evdev/evdev.py
"""


class Enum(object):
    def __init__(self, amap):
        self.__add_attributes(amap)

    def __add_attributes(self, amap):
        self._amap = amap
        for k, v in amap.items():
            self.__dict__[v] = k

    def __getitem__(self, key):
        return self.by_key(key)

    def get(self, key, fallback=None):
        return self.by_key(key, fallback)

    def by_key(self, key, fallback=None):
        return self._amap[key] if key in self._amap else fallback

    def by_value(self, value, fallback=None):
        return self.__dict__[value] if value in self.__dict__ else fallback


typeMap = Enum({0x00: "EV_RST",
                0x01: "EV_KEY",
                0x02: "EV_REL",
                0x03: "EV_ABS",
                0x04: "EV_MSC",
                0x11: "EV_LED",
                0x12: "EV_SND",
                0x14: "EV_REP",
                0x15: "EV_FF",
                })


codeMaps = Enum({"EV_KEY": Enum({0: "KEY_RESERVED",
                                 1: "KEY_ESC",
                                 2: "KEY_1",
                                 3: "KEY_2",
                                 4: "KEY_3",
                                 5: "KEY_4",
                                 6: "KEY_5",
                                 7: "KEY_6",
                                 8: "KEY_7",
                                 9: "KEY_8",
                                 10: "KEY_9",
                                 11: "KEY_0",
                                 12: "KEY_MINUS",
                                 13: "KEY_EQUAL",
                                 14: "KEY_BACKSPACE",
                                 15: "KEY_TAB",
                                 16: "KEY_Q",
                                 17: "KEY_W",
                                 18: "KEY_E",
                                 19: "KEY_R",
                                 20: "KEY_T",
                                 21: "KEY_Y",
                                 22: "KEY_U",
                                 23: "KEY_I",
                                 24: "KEY_O",
                                 25: "KEY_P",
                                 26: "KEY_LEFTBRACE",
                                 27: "KEY_RIGHTBRACE",
                                 28: "KEY_ENTER",
                                 29: "KEY_LEFTCTRL",
                                 30: "KEY_A",
                                 31: "KEY_S",
                                 32: "KEY_D",
                                 33: "KEY_F",
                                 34: "KEY_G",
                                 35: "KEY_H",
                                 36: "KEY_J",
                                 37: "KEY_K",
                                 38: "KEY_L",
                                 39: "KEY_SEMICOLON",
                                 40: "KEY_APOSTROPHE",
                                 41: "KEY_GRAVE",
                                 42: "KEY_LEFTSHIFT",
                                 43: "KEY_BACKSLASH",
                                 44: "KEY_Z",
                                 45: "KEY_X",
                                 46: "KEY_C",
                                 47: "KEY_V",
                                 48: "KEY_B",
                                 49: "KEY_N",
                                 50: "KEY_M",
                                 51: "KEY_COMMA",
                                 52: "KEY_DOT",
                                 53: "KEY_SLASH",
                                 54: "KEY_RIGHTSHIFT",
                                 55: "KEY_KPASTERISK",
                                 56: "KEY_LEFTALT",
                                 57: "KEY_SPACE",
                                 58: "KEY_CAPSLOCK",
                                 59: "KEY_F1",
                                 60: "KEY_F2",
                                 61: "KEY_F3",
                                 62: "KEY_F4",
                                 63: "KEY_F5",
                                 64: "KEY_F6",
                                 65: "KEY_F7",
                                 66: "KEY_F8",
                                 67: "KEY_F9",
                                 68: "KEY_F10",
                                 69: "KEY_NUMLOCK",
                                 70: "KEY_SCROLLLOCK",
                                 71: "KEY_KP7",
                                 72: "KEY_KP8",
                                 73: "KEY_KP9",
                                 74: "KEY_KPMINUS",
                                 75: "KEY_KP4",
                                 76: "KEY_KP5",
                                 77: "KEY_KP6",
                                 78: "KEY_KPPLUS",
                                 79: "KEY_KP1",
                                 80: "KEY_KP2",
                                 81: "KEY_KP3",
                                 82: "KEY_KP0",
                                 83: "KEY_KPDOT",
                                 84: "KEY_103RD",
                                 85: "KEY_F13",
                                 86: "KEY_102ND",
                                 87: "KEY_F11",
                                 88: "KEY_F12",
                                 89: "KEY_F14",
                                 90: "KEY_F15",
                                 91: "KEY_F16",
                                 92: "KEY_F17",
                                 93: "KEY_F18",
                                 94: "KEY_F19",
                                 95: "KEY_F20",
                                 96: "KEY_KPENTER",
                                 97: "KEY_RIGHTCTRL",
                                 98: "KEY_KPSLASH",
                                 99: "KEY_SYSRQ",
                                 100: "KEY_RIGHTALT",
                                 101: "KEY_LINEFEED",
                                 102: "KEY_HOME",
                                 103: "KEY_UP",
                                 104: "KEY_PAGEUP",
                                 105: "KEY_LEFT",
                                 106: "KEY_RIGHT",
                                 107: "KEY_END",
                                 108: "KEY_DOWN",
                                 109: "KEY_PAGEDOWN",
                                 110: "KEY_INSERT",
                                 111: "KEY_DELETE",
                                 112: "KEY_MACRO",
                                 113: "KEY_MUTE",
                                 114: "KEY_VOLUMEDOWN",
                                 115: "KEY_VOLUMEUP",
                                 116: "KEY_POWER",
                                 117: "KEY_KPEQUAL",
                                 118: "KEY_KPPLUSMINUS",
                                 119: "KEY_PAUSE",
                                 120: "KEY_F21",
                                 121: "KEY_F22",
                                 122: "KEY_F23",
                                 123: "KEY_F24",
                                 124: "KEY_KPCOMMA",
                                 125: "KEY_LEFTMETA",
                                 126: "KEY_RIGHTMETA",
                                 127: "KEY_COMPOSE",
                                 128: "KEY_STOP",
                                 129: "KEY_AGAIN",
                                 130: "KEY_PROPS",
                                 131: "KEY_UNDO",
                                 132: "KEY_FRONT",
                                 133: "KEY_COPY",
                                 134: "KEY_OPEN",
                                 135: "KEY_PASTE",
                                 136: "KEY_FIND",
                                 137: "KEY_CUT",
                                 138: "KEY_HELP",
                                 139: "KEY_MENU",
                                 140: "KEY_CALC",
                                 141: "KEY_SETUP",
                                 142: "KEY_SLEEP",
                                 143: "KEY_WAKEUP",
                                 144: "KEY_FILE",
                                 145: "KEY_SENDFILE",
                                 146: "KEY_DELETEFILE",
                                 147: "KEY_XFER",
                                 148: "KEY_PROG1",
                                 149: "KEY_PROG2",
                                 150: "KEY_WWW",
                                 151: "KEY_MSDOS",
                                 152: "KEY_COFFEE",
                                 153: "KEY_DIRECTION",
                                 154: "KEY_CYCLEWINDOWS",
                                 155: "KEY_MAIL",
                                 156: "KEY_BOOKMARKS",
                                 157: "KEY_COMPUTER",
                                 158: "KEY_BACK",
                                 159: "KEY_FORWARD",
                                 160: "KEY_CLOSECD",
                                 161: "KEY_EJECTCD",
                                 162: "KEY_EJECTCLOSECD",
                                 163: "KEY_NEXTSONG",
                                 164: "KEY_PLAYPAUSE",
                                 165: "KEY_PREVIOUSSONG",
                                 166: "KEY_STOPCD",
                                 167: "KEY_RECORD",
                                 168: "KEY_REWIND",
                                 169: "KEY_PHONE",
                                 170: "KEY_ISO",
                                 171: "KEY_CONFIG",
                                 172: "KEY_HOMEPAGE",
                                 173: "KEY_REFRESH",
                                 174: "KEY_EXIT",
                                 175: "KEY_MOVE",
                                 176: "KEY_EDIT",
                                 177: "KEY_SCROLLUP",
                                 178: "KEY_SCROLLDOWN",
                                 179: "KEY_KPLEFTPAREN",
                                 180: "KEY_KPRIGHTPAREN",
                                 181: "KEY_INTL1",
                                 182: "KEY_INTL2",
                                 183: "KEY_INTL3",
                                 184: "KEY_INTL4",
                                 185: "KEY_INTL5",
                                 186: "KEY_INTL6",
                                 187: "KEY_INTL7",
                                 188: "KEY_INTL8",
                                 189: "KEY_INTL9",
                                 190: "KEY_LANG1",
                                 191: "KEY_LANG2",
                                 192: "KEY_LANG3",
                                 193: "KEY_LANG4",
                                 194: "KEY_LANG5",
                                 195: "KEY_LANG6",
                                 196: "KEY_LANG7",
                                 197: "KEY_LANG8",
                                 198: "KEY_LANG9",
                                 200: "KEY_PLAYCD",
                                 201: "KEY_PAUSECD",
                                 202: "KEY_PROG3",
                                 203: "KEY_PROG4",
                                 205: "KEY_SUSPEND",
                                 206: "KEY_CLOSE",
                                 220: "KEY_UNKNOWN",
                                 224: "KEY_BRIGHTNESSDOWN",
                                 225: "KEY_BRIGHTNESSUP",
                                 0x100: "BTN_0",
                                 0x101: "BTN_1",
                                 0x102: "BTN_2",
                                 0x103: "BTN_3",
                                 0x104: "BTN_4",
                                 0x105: "BTN_5",
                                 0x106: "BTN_6",
                                 0x107: "BTN_7",
                                 0x108: "BTN_8",
                                 0x109: "BTN_9",
                                 0x110: "BTN_LEFT",
                                 0x111: "BTN_RIGHT",
                                 0x112: "BTN_MIDDLE",
                                 0x113: "BTN_SIDE",
                                 0x114: "BTN_EXTRA",
                                 0x115: "BTN_FORWARD",
                                 0x116: "BTN_BACK",
                                 0x120: "BTN_TRIGGER",
                                 0x121: "BTN_THUMB",
                                 0x122: "BTN_THUMB2",
                                 0x123: "BTN_TOP",
                                 0x124: "BTN_TOP2",
                                 0x125: "BTN_PINKIE",
                                 0x126: "BTN_BASE",
                                 0x127: "BTN_BASE2",
                                 0x128: "BTN_BASE3",
                                 0x129: "BTN_BASE4",
                                 0x12a: "BTN_BASE5",
                                 0x12b: "BTN_BASE6",
                                 0x12f: "BTN_DEAD",
                                 0x130: "BTN_A",
                                 0x131: "BTN_B",
                                 0x132: "BTN_C",
                                 0x133: "BTN_X",
                                 0x134: "BTN_Y",
                                 0x135: "BTN_Z",
                                 0x136: "BTN_TL",
                                 0x137: "BTN_TR",
                                 0x138: "BTN_TL2",
                                 0x139: "BTN_TR2",
                                 0x13a: "BTN_SELECT",
                                 0x13b: "BTN_START",
                                 0x13c: "BTN_MODE",
                                 0x13d: "BTN_THUMBL",
                                 0x13e: "BTN_THUMBR",
                                 0x140: "BTN_TOOL_PEN",
                                 0x141: "BTN_TOOL_RUBBER",
                                 0x142: "BTN_TOOL_BRUSH",
                                 0x143: "BTN_TOOL_PENCIL",
                                 0x144: "BTN_TOOL_AIRBRUSH",
                                 0x145: "BTN_TOOL_FINGER",
                                 0x146: "BTN_TOOL_MOUSE",
                                 0x147: "BTN_TOOL_LENS",
                                 0x14a: "BTN_TOUCH",
                                 0x14b: "BTN_STYLUS",
                                 0x14c: "BTN_STYLUS2",
                                 }),

                 "EV_REL": Enum({0x00: "REL_X",
                                 0x01: "REL_Y",
                                 0x02: "REL_Z",
                                 0x06: "REL_HWHEEL",
                                 0x07: "REL_DIAL",
                                 0x08: "REL_WHEEL",
                                 0x09: "REL_MISC",
                                 }),


                 "EV_ABS": Enum({0x00: "ABS_X",
                                 0x01: "ABS_Y",
                                 0x02: "ABS_Z",
                                 0x03: "ABS_RX",
                                 0x04: "ABS_RY",
                                 0x05: "ABS_RZ",
                                 0x06: "ABS_THROTTLE",
                                 0x07: "ABS_RUDDER",
                                 0x08: "ABS_WHEEL",
                                 0x09: "ABS_GAS",
                                 0x0a: "ABS_BRAKE",
                                 0x10: "ABS_HAT0X",
                                 0x11: "ABS_HAT0Y",
                                 0x12: "ABS_HAT1X",
                                 0x13: "ABS_HAT1Y",
                                 0x14: "ABS_HAT2X",
                                 0x15: "ABS_HAT2Y",
                                 0x16: "ABS_HAT3X",
                                 0x17: "ABS_HAT3Y",
                                 0x18: "ABS_PRESSURE",
                                 0x19: "ABS_DISTANCE",
                                 0x1a: "ABS_TILT_X",
                                 0x1b: "ABS_TILT_Y",
                                 0x1c: "ABS_MISC",
                                 }),

                 "EV_MSC": Enum({0x00: "MSC_SERIAL",
                                 0x01: "MSC_PULSELED",
                                 }),

                 "EV_LED": Enum({0x00: "LED_NUML",
                                 0x01: "LED_CAPSL",
                                 0x02: "LED_SCROLLL",
                                 0x03: "LED_COMPOSE",
                                 0x04: "LED_KANA",
                                 0x05: "LED_SLEEP",
                                 0x06: "LED_SUSPEND",
                                 0x07: "LED_MUTE",
                                 0x08: "LED_MISC",
                                 }),

                 "EV_REP": Enum({0x00: "REP_DELAY",
                                 0x01: "REP_PERIOD",
                                 }),

                 "EV_SND": Enum({0x00: "SND_CLICK",
                                 0x01: "SND_BELL",
                                 }),
                 })


class InputEvent(object):
    def __init__(self, _type, code, value):
        self.type = _type
        self.code = code
        self.value = value

    def __str__(self):
        return "<InputEvent type={type} code={code} value={value}>".format(
            type=typeMap[self.type],
            code=codeMaps[typeMap[self.type]].get(self.code, self.code),
            value=self.value)

    def __eq__(self, other):
        vals = [(self.type, other.type),
                (self.code, other.code),
                (self.value, other.value)]
        return all(sv == ov for sv, ov in vals if sv and ov)


class InputParser(object):
    logger = None
    fmt = "llHHI"
    fmtsize = struct.calcsize(fmt)

    def __init__(self, files):
        assert type(files) is list
        self.fds = [os.open(dev, os.O_RDONLY) for dev in files]
        self.logger = log.getLogger(__name__)

    def __readevent(self, rs):
        packages = []
        try:
            packages = (os.read(fd, self.fmtsize) for fd in rs)
            for package in packages:
                parsed = struct.unpack(self.fmt, package[:self.fmtsize])
                timeval, suseconds, typ, code, value = parsed
                if typ:
                    yield timeval, suseconds, typ, value, code
        except OSError as e:
            self.logger.exception("Couldn't parse event: %s" % e)

    def parse(self):
        while 1:
            rs, _, _ = select.select(self.fds, [], [])
            for _, _, t, v, e in self.__readevent(rs):
                yield InputEvent(t, e, v)


class InputParserThread(threading.Thread):
    """A thread to watch for input events
    """
    inputdevices = []
    event_filter = None
    on_event = None
    logger = None

    def __init__(self, inputdevices, event_filter=None):
        super(InputParserThread, self).__init__()
        self.logger = log.getLogger(__name__)
        self.daemon = True
        self.logger.info("Creating input watcher thread")
        self.inputdevices = inputdevices
        self.event_filter = event_filter
        self.on_event = base.Base.Signal(self)

    def run(self):
        self.logger.info("Starting input watcher")
        try:
            assert self.inputdevices and self.on_event

            parser = InputParser(self.inputdevices)
            for event in parser.parse():
                is_correct_event = (self.event_filter and event ==
                                    self.event_filter)
                if not self.event_filter or is_correct_event:
                    self.on_event.emit(event)
        except:
            self.logger.exception("Exception in input watcher")


if __name__ == "__main__":
    def cb(evnt):
        print evnt
        if evnt == InputEvent(typeMap.EV_LED, None, None):
            print "Found the event you were looking for:", evnt

    p = InputParserThread(sys.argv[1:])
    p.on_event_callback = cb
    p.start()
    p.join()
