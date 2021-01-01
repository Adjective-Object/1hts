import sys
import os
from evdev import InputDevice, categorize, ecodes, KeyEvent

# Map USB Keysym to linux Keysym since the translation happens normally
# in driver, but the Koolertron keymap bin uses USB HID codes. We have to
# replicate the mapping here.
#
# from https://github.com/torvalds/linux/blob/master/drivers/hid/usbhid/usbkbd.c
usb_kbd_keycode = [
    0,
    0,
    0,
    0,
    30,
    48,
    46,
    32,
    18,
    33,
    34,
    35,
    23,
    36,
    37,
    38,
    50,
    49,
    24,
    25,
    16,
    19,
    31,
    20,
    22,
    47,
    17,
    45,
    21,
    44,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    28,
    1,
    14,
    15,
    57,
    12,
    13,
    26,
    27,
    43,
    43,
    39,
    40,
    41,
    51,
    52,
    53,
    58,
    59,
    60,
    61,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    87,
    88,
    99,
    70,
    119,
    110,
    102,
    104,
    111,
    107,
    109,
    106,
    105,
    108,
    103,
    69,
    98,
    55,
    74,
    78,
    96,
    79,
    80,
    81,
    75,
    76,
    77,
    71,
    72,
    73,
    82,
    83,
    86,
    127,
    116,
    117,
    183,
    184,
    185,
    186,
    187,
    188,
    189,
    190,
    191,
    192,
    193,
    194,
    134,
    138,
    130,
    132,
    128,
    129,
    131,
    137,
    133,
    135,
    136,
    113,
    115,
    114,
    0,
    0,
    0,
    121,
    0,
    89,
    93,
    124,
    92,
    94,
    95,
    0,
    0,
    0,
    122,
    123,
    90,
    91,
    85,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    29,
    42,
    56,
    125,
    97,
    54,
    100,
    126,
    164,
    166,
    165,
    163,
    161,
    115,
    114,
    113,
    150,
    158,
    159,
    128,
    136,
    177,
    178,
    176,
    142,
    152,
    173,
    140,
]


class CircleBufferIter:
    def __init__(self, cb):
        self.circlebuffer = cb
        self.pos = 0

    def __next__(self):
        if self.pos >= self.circlebuffer.sz or self.circlebuffer.at(self.pos) == None:
            raise StopIteration
        to_ret = self.circlebuffer.at(self.pos)
        self.pos += 1
        return to_ret


# Bus 001 Device 007: ID 04b4:0818 Cypress Semiconductor Corp. Thumb Keyboard
class CircleBuffer:
    def __init__(self, sz):
        self.sz = sz
        self.buff = [None] * sz
        self.pos = 0

    def add(self, to_add):
        self.buff[self.pos] = to_add
        self.pos = (self.pos + 1) % self.sz

    def at(self, i):
        return self.buff[(self.pos + i) % self.sz]

    def __iter__(self):
        return CircleBufferIter(self)


def get_aliasing_map(mapdef_bin):
    aliases = dict()
    for i in range(0, len(mapdef_bin), 4):
        k_id, k1, k2, k3 = (int(x) for x in mapdef_bin[i : i + 4])
        k1 = usb_kbd_keycode[k1]
        k2 = usb_kbd_keycode[k2]
        k3 = usb_kbd_keycode[k3]
        if k_id == 0x8A:
            if k1 not in aliases:
                aliases[k1] = set()
            aliases[k1].add(k2)
            aliases[k1].add(k3)

    return aliases


def is_mod_release_alias(old_event, new_event, aliases):
    k_new = KeyEvent(new_event)
    k_old = KeyEvent(old_event)
    return (
        old_event.sec == new_event.sec
        and abs(old_event.usec - new_event.usec) < 1
        and KeyEvent(old_event).keystate == KeyEvent.key_up
        and k_new.keystate == KeyEvent.key_down
        and k_new.scancode in aliases
        and k_old.scancode in aliases[k_new.scancode]
    )


def process_ev(evbuff, aliases, new_event):
    if any(is_mod_release_alias(old_event, new_event, aliases) for old_event in evbuff):
        print("alias")
    evbuff.add(new_event)


def main(argv):
    dev = InputDevice(
        "/dev/input/by-id/usb-LingYao_ShangHai_Thumb_Keyboard_081820131130-event-kbd"
    )
    aliases = get_aliasing_map(open("halfquerty-v2.bin", "rb").read())
    evbuff = CircleBuffer(5)
    print("aliases", aliases)
    print(dev)
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            process_ev(evbuff, aliases, event)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
