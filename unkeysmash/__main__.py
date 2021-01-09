import tkinter as tk
import sys
import traceback
from Xlib.display import Display
from Xlib.ext import xinput
from Xlib import XK
from vocab import Vocab


def is_well_known_ctrl_hotkey(c):
    return c in "cvzyafs"


space_chars = set([" ", "\t", "\n"])


class TypingTracker:
    def __init__(self, language_model):
        self._language_model = language_model
        self.reset_buff()
        self.modifier_map = dict()
        self.modifier_map[XK.XK_Control_L] = False
        self.modifier_map[XK.XK_Control_R] = False
        self.modifier_map[XK.XK_Shift_L] = False
        self.modifier_map[XK.XK_Shift_R] = False

    def reset_buff(self):
        self.typing_buffer = []
        self.cursor_idx = 0
        self.selection_range_chars = 0

    def shift_cursor_right(self):
        self.cursor_idx += 1
        if self.cursor_idx > len(self.typing_buffer):
            self.reset_buff()

    def shift_cursor_left(self):
        self.cursor_idx -= 1
        if self.cursor_idx < 0:
            self.reset_buff()

    def _find_word_boundary(self, rangeiter):
        in_word = False
        for i in rangeiter:
            print(i)
            if self.typing_buffer[i] not in space_chars:
                in_word = True
            elif in_word:
                return i

        return -1

    def shift_cursor_start_word(self):
        if self.cursor_idx == 0:
            self.reset_buff()
        else:
            prev_spc = self._find_word_boundary(range(self.cursor_idx - 1, -1, -1))
            self.cursor_idx = 0 if prev_spc == -1 else prev_spc + 1

    def shift_cursor_end_word(self):
        if self.cursor_idx == len(self.typing_buffer):
            self.reset_buff()
        else:
            next_spc = self._find_word_boundary(
                range(self.cursor_idx + 1, len(self.typing_buffer), 1)
            )
            self.cursor_idx = len(self.typing_buffer) if next_spc == -1 else next_spc

    def forward_delete(self):
        if self.cursor_idx != len(self.typing_buffer):
            self.typing_buffer = (
                self.typing_buffer[0 : self.cursor_idx]
                + self.typing_buffer[self.cursor_idx + 1 :]
            )

    def backward_delete(self):
        if self.cursor_idx != 0:
            self.typing_buffer = (
                self.typing_buffer[0 : self.cursor_idx - 1]
                + self.typing_buffer[self.cursor_idx :]
            )
            self.cursor_idx -= 1

    def handle_keypress_sym(self, k):
        name = XK.keysym_to_string(k)

        if k in self.modifier_map:
            self.modifier_map[k] = True
            return

        # in buffer mvmt
        if k == XK.XK_Right and self.is_ctrl():
            self.shift_cursor_end_word()
        elif k == XK.XK_Right:
            self.shift_cursor_right()
        elif k == XK.XK_Left and self.is_ctrl():
            self.shift_cursor_start_word()
        elif k == XK.XK_Left:
            self.shift_cursor_left()

        # del bk
        elif k == XK.XK_Delete:
            self.forward_delete()
        elif k == XK.XK_BackSpace:
            self.backward_delete()

        # printable char
        elif name is not None:
            if self.is_ctrl() and is_well_known_ctrl_hotkey(name):
                self.reset_buff()
            else:
                c = name.upper() if self.is_shift() else name
                self.type_char(c)
        else:
            print("other", k, name)
            self.reset_buff()

    def handle_keyrelease_sym(self, k):
        if k in self.modifier_map:
            self.modifier_map[k] = False
            return

    def is_ctrl(self):
        return self.modifier_map[XK.XK_Control_L] or self.modifier_map[XK.XK_Control_R]

    def is_shift(self):
        return self.modifier_map[XK.XK_Shift_L] or self.modifier_map[XK.XK_Shift_R]

    def type_char(self, char):
        self.typing_buffer = (
            self.typing_buffer[0 : self.cursor_idx]
            + [char[0]]
            + self.typing_buffer[self.cursor_idx :]
        )
        self.cursor_idx += 1

    def get_text(self):
        return (
            "".join(self.typing_buffer[: self.cursor_idx]),
            "".join(self.typing_buffer[self.cursor_idx :]),
        )


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


class SuggestionLabel:
    def __init__(self, container):
        self.var = tk.StringVar()
        self.var.set("")
        self.sel_label = tk.Label(
            container,
            textvariable=self.var,
            cnf={"font": "monospace 12", "fg": "#EEEEEE", "bg": "#0000EE", "height": 1},
        )

    def update(self, txt):
        self.var.set(txt)
        self.sel_label.pack()

    def dispose(self):
        self.sel_label.destroy()


def main(argv):
    display = Display()
    # Xinput
    extension_info = display.query_extension("XInputExtension")
    xinput_major = extension_info.major_opcode

    typing_tracker = TypingTracker(None)

    version_info = display.xinput_query_version()
    print(
        "Found XInput version %u.%u"
        % (
            version_info.major_version,
            version_info.minor_version,
        )
    )

    xscreen = display.screen()
    xscreen.root.xinput_select_events(
        [
            (
                xinput.AllDevices,
                xinput.KeyPressMask
                | xinput.KeyReleaseMask
                | xinput.ButtonPressMask
                | xinput.RawButtonPressMask,
            ),
        ]
    )

    # Window
    win = tk.Tk()
    win.geometry("+100+100")

    win.wm_attributes("-topmost", 1)
    win.overrideredirect(True)

    container = tk.Frame(win)
    container.pack()

    before_txt_var = tk.StringVar()
    before_txt_var.set("")
    before_label = tk.Label(
        container,
        textvariable=before_txt_var,
        cnf={"font": "monospace 12", "fg": "#EEEEEE", "height": 1},
    )

    sel_txt_var = tk.StringVar()
    sel_txt_var.set("")
    sel_label = tk.Label(
        container,
        textvariable=sel_txt_var,
        cnf={"font": "monospace 12", "fg": "#EEEEEE", "bg": "#0000EE", "height": 1},
    )

    after_txt_var = tk.StringVar()
    after_txt_var.set("")
    after_label = tk.Label(
        container,
        textvariable=after_txt_var,
        cnf={"font": "monospace 12", "fg": "#EEEEEE", "height": 1},
    )

    suggestion_container = tk.Frame(win)
    suggestion_labels = []

    before_label.pack(side=tk.LEFT)
    sel_label.pack(side=tk.LEFT)
    after_label.pack(side=tk.LEFT)
    suggestion_container.pack(side=tk.BOTTOM)

    vocab = Vocab.loads(open("vocab.json", "r").read())

    try:
        while True:
            i = 0
            while display.pending_events() > 0 and i < 20:
                i += 1
                event = display.next_event()

                print(event)
                if not event or event.type != 35:
                    continue

                if event.evtype == xinput.KeyPress:
                    keycode = event.data.detail
                    typing_tracker.handle_keypress_sym(
                        display.keycode_to_keysym(keycode, 0)
                    )
                elif event.evtype == xinput.KeyRelease:
                    keycode = event.data.detail
                    typing_tracker.handle_keyrelease_sym(
                        display.keycode_to_keysym(keycode, 0)
                    )
                elif (
                    event.evtype == xinput.ButtonPress
                    or event.evtype == xinput.RawButtonPress
                ):
                    typing_tracker.reset_buff()
            if i >= 1:
                before_text, after_text = typing_tracker.get_text()
                before_txt_var.set(before_text)
                after_txt_var.set(after_text)

                suggestions = vocab.suggestions(before_text)
                print(suggestions)
                while len(suggestions) > len(suggestion_labels):
                    l = SuggestionLabel(
                        suggestion_container,
                    )
                    suggestion_labels.append(l)

                while len(suggestions) < len(suggestion_labels):
                    l = suggestion_labels.pop()
                    l.dispose()

                for sugg, label in zip(suggestions, suggestion_labels):
                    label.update(sugg)

            win.update_idletasks()
            win.update()
    except KeyboardInterrupt as e:
        return 0
    except Exception as e:
        print(e)
        print(full_stack())
    finally:
        win.destroy()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
