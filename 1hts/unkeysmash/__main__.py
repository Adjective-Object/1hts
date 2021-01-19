import tkinter as tk
import sys
import traceback
from Xlib.display import Display
from Xlib.ext import xinput
from Xlib import XK
from evdev import ecodes, UInput
from .vocab import Vocab
from .suggester import Suggester
from .edit_sequences import EditSequencesConfig
from ..lib1hts.aliasmap import AliasMap


def is_well_known_ctrl_hotkey(c):
    return c in "cvzyafsd"


space_chars = set([" ", "\t", "\n"])

STEP_PREV = ecodes.KEY_F23
STEP_NEXT = ecodes.KEY_F22
SELECT_ACTIVE = ecodes.KEY_F21


BG_NOHL = "#222222"
FG_NOHL = "#EEEEEE"

BG_HL = "#1111AA"
FG_HL = "#FFFFFF"

BG_SEL = "#444444"
FG_SEL = "#EEEEEE"


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
            cnf={
                "font": "monospace 12",
                "height": 1,
                "fg": FG_NOHL,
                "bg": BG_NOHL,
            },
        )

    def update(self, txt, selected):
        self.var.set(txt)
        if selected:
            self.sel_label.configure(
                {
                    "fg": FG_HL,
                    "bg": BG_HL,
                }
            )
        else:
            self.sel_label.configure(
                {
                    "fg": FG_NOHL,
                    "bg": BG_NOHL,
                }
            )

        self.sel_label.pack()

    def dispose(self):
        self.sel_label.destroy()


def get_last_word(buffer):
    lastspaceidx = buffer.rfind(" ")
    lastwordstartidx = 0 if lastspaceidx == -1 else lastspaceidx + 1
    return buffer[lastwordstartidx:]


def correct_typing_buffer(display, ui, current_content, intended_content):
    print("correct_typing_buffer", current_content, intended_content)

    first_mismatch_idx = 0
    while (
        first_mismatch_idx < len(current_content)
        and current_content[first_mismatch_idx] == intended_content[first_mismatch_idx]
    ):
        first_mismatch_idx += 1

    # clear buffer backwards
    numbkspc = len(current_content) - first_mismatch_idx
    print("backspace", numbkspc)

    for i in range(numbkspc):
        ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 1)  # down
        ui.write(ecodes.EV_KEY, ecodes.KEY_BACKSPACE, 0)  # up
        ui.syn()

    print("type", intended_content[first_mismatch_idx:])

    # emit intended buffer
    for char in intended_content[first_mismatch_idx:]:
        upper = char.isupper()
        if upper:
            ui.write(ecodes.KEY_LEFTSHIFT, ecodes.KEY_LEFTSHIFT, 1)  # down
            ui.syn()

        sym = XK.string_to_keysym(char.lower())

        # linux keycodes are offset by 8bytes
        code = display.keysym_to_keycode(sym) - 8
        # print("emit 0x%x %s" % (code, code))
        ui.write(ecodes.EV_KEY, code, 1)  # down
        ui.write(ecodes.EV_KEY, code, 0)  # up
        ui.syn()

        if upper:
            ui.write(ecodes.KEY_LEFTSHIFT, ecodes.KEY_LEFTSHIFT, 0)  # up
            ui.syn()


def main(argv):
    display = Display()
    # Xinput
    extension_info = display.query_extension("XInputExtension")
    xinput_major = extension_info.major_opcode

    typing_tracker = TypingTracker(None)

    aliasing_map = AliasMap(open("halfquerty-v2.bin", "rb").read())

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
    win.attributes("-alpha", 0.5)
    win.config(bg=BG_NOHL)
    win.overrideredirect(True)

    container = tk.Frame(win, cnf={"bg": BG_NOHL})
    container.pack()

    before_txt_var = tk.StringVar()
    before_txt_var.set("")
    before_label = tk.Label(
        container,
        textvariable=before_txt_var,
        cnf={"font": "monospace 12", "fg": FG_NOHL, "bg": BG_NOHL, "height": 1},
    )

    sel_txt_var = tk.StringVar()
    sel_txt_var.set("")
    sel_label = tk.Label(
        container,
        textvariable=sel_txt_var,
        cnf={"font": "monospace 12", "fg": FG_SEL, "bg": BG_SEL, "height": 1},
    )

    after_txt_var = tk.StringVar()
    after_txt_var.set("")
    after_label = tk.Label(
        container,
        textvariable=after_txt_var,
        cnf={"font": "monospace 12", "fg": FG_NOHL, "bg": BG_NOHL, "height": 1},
    )

    suggestion_container = tk.Frame(win, cnf={"bg": BG_NOHL})
    suggestion_labels = []
    suggestion_idx = 0

    before_label.pack(side=tk.LEFT)
    sel_label.pack(side=tk.LEFT)
    after_label.pack(side=tk.LEFT)
    suggestion_container.pack(side=tk.BOTTOM)

    vocab = Vocab.loads(open("vocab.json", "r").read())
    ui = UInput()

    suggester = Suggester(vocab, edit_sequence_config=EditSequencesConfig())

    try:
        while True:
            i = 0
            while display.pending_events() > 0 and i < 20:
                i += 1
                event = display.next_event()

                # print(event)
                if not event or event.type != 35:
                    continue

                if event.evtype == xinput.KeyPress:
                    keycode = event.data.detail
                    keysym = display.keycode_to_keysym(keycode, 0)
                    if keycode == STEP_NEXT:
                        suggestion_idx = min(
                            suggestion_idx + 1, len(suggestion_labels) - 1
                        )
                    elif keycode == STEP_PREV:
                        suggestion_idx = max(suggestion_idx - 1, 0)
                    elif keycode == SELECT_ACTIVE:
                        # correct the word to the suggestion
                        before_text, after_text = typing_tracker.get_text()
                        last_word = get_last_word(before_text)

                        suggestions = suggester.get_prefix_suggestions(lastword)

                        if suggestion_idx < len(suggestions):
                            correct_typing_buffer(
                                display, ui, last_word, suggestions[suggestion_idx]
                            )

                    else:
                        typing_tracker.handle_keypress_sym(keysym)
                        suggestion_idx = 0

                elif event.evtype == xinput.KeyRelease:
                    keycode = event.data.detail
                    keysym = display.keycode_to_keysym(keycode, 0)
                    typing_tracker.handle_keyrelease_sym(keysym)
                elif (
                    event.evtype == xinput.ButtonPress
                    or event.evtype == xinput.RawButtonPress
                ):
                    typing_tracker.reset_buff()
            if i >= 1:
                before_text, after_text = typing_tracker.get_text()
                before_txt_var.set(before_text)
                h = 1 + before_text.count("\r")
                before_label.configure({"height": h})
                after_txt_var.set(after_text)

                lastword = get_last_word(before_text)
                suggestions = suggester.get_prefix_suggestions(lastword)
                while len(suggestions) > len(suggestion_labels):
                    l = SuggestionLabel(
                        suggestion_container,
                    )
                    suggestion_labels.append(l)

                while len(suggestions) < len(suggestion_labels):
                    l = suggestion_labels.pop()
                    l.dispose()

                for i, (sugg, label) in enumerate(zip(suggestions, suggestion_labels)):
                    label.update(sugg, i == suggestion_idx)
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
