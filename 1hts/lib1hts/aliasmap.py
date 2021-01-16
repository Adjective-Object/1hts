from .usb_kbd_keycode import usb_kbd_keycode


class AliasMap:
    def __init__(self, mapdef_bin):
        self.forward_aliases = dict()
        self.reverse_aliases = dict()

        self.alias_source_keys = set()
        self.alias_target_keys = set()
        for i in range(0, len(mapdef_bin), 4):
            k_id, k1, k2, k3 = (int(x) for x in mapdef_bin[i : i + 4])
            k1 = usb_kbd_keycode[k1]
            k2 = usb_kbd_keycode[k2]
            k3 = usb_kbd_keycode[k3]
            if k_id == 0x8A:
                if k1 not in self.forward_aliases:
                    self.forward_aliases[k1] = set()
                self.forward_aliases[k1].add(k2)
                self.forward_aliases[k1].add(k3)

                if k2 not in self.reverse_aliases:
                    self.reverse_aliases[k2] = set()
                self.reverse_aliases[k2].add(k1)

                if k3 not in self.reverse_aliases:
                    self.reverse_aliases[k3] = set()
                self.reverse_aliases[k3].add(k1)

                self.alias_source_keys.add(k1)
                self.alias_target_keys.add(k2)
                self.alias_target_keys.add(k3)
