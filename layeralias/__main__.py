import sys
import os
import traceback
from evdev import InputDevice, categorize, ecodes, KeyEvent, list_devices, UInput
from usb_kbd_keycode import usb_kbd_keycode

# See https://usb-ids.gowdy.us/read/UD/04b4
CYPRESS_VENDOR = 0x4B4
THUMB_BOARD = 0x818


def full_stack():
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]  # remove call of full_stack, the printed exception
        # will contain the caught exception caller instead
    trc = "Traceback (most recent call last):\n"
    stackstr = trc + "".join(traceback.format_list(stack))
    if exc is not None:
        stackstr += "  " + traceback.format_exc().lstrip(trc)
    return stackstr


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
    forward_aliases = dict()
    alias_keys = set()
    for i in range(0, len(mapdef_bin), 4):
        k_id, k1, k2, k3 = (int(x) for x in mapdef_bin[i : i + 4])
        k1 = usb_kbd_keycode[k1]
        k2 = usb_kbd_keycode[k2]
        k3 = usb_kbd_keycode[k3]
        if k_id == 0x8A:
            if k1 not in forward_aliases:
                forward_aliases[k1] = set()
            forward_aliases[k1].add(k2)
            forward_aliases[k1].add(k3)
            alias_keys.add(k2)
            alias_keys.add(k3)

    return forward_aliases, alias_keys


def is_typing_key(key_event):
    return key_event.scancode not in [
        ecodes.KEY_LEFTSHIFT,
        ecodes.KEY_RIGHTSHIFT,
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_RIGHTCTRL,
    ]


def usec_delta(a, b):
    return (a.sec - b.sec) * 1000000 + (a.usec - b.usec)


def is_alias_pair(k_unmodified, k_modified, forward_aliases):
    return (
        abs(usec_delta(k_unmodified.event, k_modified.event)) < 1
        and is_typing_key(k_modified)
        and is_typing_key(k_unmodified)
        and k_unmodified.scancode in forward_aliases
        and k_modified.scancode in forward_aliases[k_unmodified.scancode]
    )


def is_mod_release_alias(k_old, k_new, forward_aliases):
    return (
        is_alias_pair(k_new, k_old, forward_aliases)
        and k_old.keystate == KeyEvent.key_up
        and k_new.keystate == KeyEvent.key_down
    )


def is_mod_press_alias(k_old, k_new, forward_aliases):
    return (
        is_alias_pair(k_old, k_new, forward_aliases)
        and k_old.keystate == KeyEvent.key_up
        and k_new.keystate == KeyEvent.key_down
    )


def handle_early_press_alias(event_buffer, new_event, forward_aliases, ui, alias_keys):
    evts = list(event_buffer)
    if len(evts) < 2:
        return False

    newcode = KeyEvent(new_event)
    if newcode.scancode not in alias_keys or newcode.keystate != KeyEvent.key_down:
        return False

    x = [str(KeyEvent(e)) for e in evts]
    # print(
    #     ")))",
    #     "\n".join(x),
    #     "|||",
    #     KeyEvent(new_event),
    #     list(reversed(list(zip(x, x[1:])))),
    # )

    # step more recent to less
    for (aliasrelease, aliaspress) in reversed(list(zip(evts, evts[1:]))):
        if (
            is_mod_press_alias(
                KeyEvent(aliasrelease), KeyEvent(aliaspress), forward_aliases
            )
            and abs(usec_delta(aliaspress, new_event)) < 100000
        ):
            # press alias detected
            print(
                "detected early layer press aliasing (%s/%s -> %s)"
                % (
                    KeyEvent(aliasrelease).keycode,
                    KeyEvent(aliaspress).keycode,
                    KeyEvent(new_event).keycode,
                )
            )
            # delete the alias char and the new char
            ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 1)  # down
            ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 0)  # up
            ui.syn()
            ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 1)  # down
            ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 0)  # up
            ui.syn()

            # repeat the new keypress
            # print(newcode.scancode)
            ui.write(ecodes.EV_KEY, newcode.scancode, 1)  # down
            ui.write(ecodes.EV_KEY, newcode.scancode, 0)  # up
            ui.write(ecodes.EV_KEY, newcode.scancode, 1)  # down
            ui.write(ecodes.EV_KEY, newcode.scancode, 0)  # up

            ui.syn()

            return True

    return False


def handle_early_release_alias(event_buffer, new_event, forward_aliases, ui):
    release_aliasing = [
        old_event
        for old_event in event_buffer
        if is_mod_release_alias(
            KeyEvent(old_event), KeyEvent(new_event), forward_aliases
        )
    ]

    if len(release_aliasing):
        old_event = release_aliasing[0]
        k_new = KeyEvent(new_event)
        k_old = KeyEvent(old_event)

        print(
            "detected layer release aliasing (%s/%s)" % (k_old.keycode, k_new.keycode)
        )
        ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 1)  # down
        ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 0)  # up
        ui.syn()

        return True

    return False


def process_ev(event_buffer, forward_aliases, new_event, ui, alias_keys):
    (
        handle_early_press_alias(
            event_buffer, new_event, forward_aliases, ui, alias_keys
        )
        or handle_early_release_alias(event_buffer, new_event, forward_aliases, ui)
    )

    event_buffer.add(new_event)


def is_thumb_board(device):
    if device.name == "LingYao ShangHai Thumb Keyboard" or (
        device.info.vendor == CYPRESS_VENDOR and device.info.product == THUMB_BOARD
    ):

        cap = device.capabilities(verbose=True)
        key_keys = [x for x in cap.keys() if "EV_KEY" in x]
        if 0 == len(key_keys):
            return False

        device_keys = cap[key_keys[0]]
        # filter out pointer devices since the keyboard presents a keyboard and
        # pointer device. we only care about the keyboard
        return len([k for k in device_key if "BTN_MOUSE" not in k])
    return False


def identify_thumb_board():
    devices = [InputDevice(path) for path in list_devices()]
    thumb_boards = [
        device
        for device in devices
        if device.name == "LingYao ShangHai Thumb Keyboard"
        or (device.info.vendor == CYPRESS_VENDOR and device.info.product == THUMB_BOARD)
        and device.capabilities(verbose=True)
    ]

    if len(thumb_boards) < 1:
        return None
    thumb_board = thumb_boards[-1]

    for evdev_device in devices:
        if evdev_device != thumb_board:
            evdev_device.close()

    return thumb_board


def main(argv):
    thumb_board = identify_thumb_board()
    if thumb_board is None:
        print("could not find a Thumb Keyboard")
        return 1
    print(
        "binding to %s (%x %x)"
        % (thumb_board.path, thumb_board.info.vendor, thumb_board.info.product)
    )

    forward_aliases, alias_keys = get_aliasing_map(
        open("halfquerty-v2.bin", "rb").read()
    )
    event_buffer = CircleBuffer(5)
    print("forward_aliases", forward_aliases)
    print("alias_keys", alias_keys)

    try:
        ui = UInput()
        for event in thumb_board.read_loop():
            if event.type == ecodes.EV_KEY:
                process_ev(event_buffer, forward_aliases, event, ui, alias_keys)
    except KeyboardInterrupt as e:
        return 0
    except Exception as e:
        print(full_stack())
    finally:
        ui.close()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
