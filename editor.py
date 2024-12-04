import argparse
import curses
import sys
import wcwidth
import locale
from utils import save_text, save_buffer, ascii_to_key

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

def char_width(character):
    width = wcwidth.wcwidth(character)
    return max(0, width)

def line_width(line):
    return sum(char_width(c) for c in line)

def get_line_height(line, n_cols):
    """
    line: str
    n_cols: int
    return: int, int
    """

    lw = 0
    line_rows = 0
    line += ' '
    for cursor_col in range(len(line)):
        # lw = line_width(buffer[cursor.row][line_start:cursor_col+1])
        lw += char_width(line[cursor_col])
        if lw < n_cols:
            continue
        line_rows += 1
        # line_start = cursor_col + 1 
        lw = 0
    return line_rows

class Buffer:
    def __init__(self, lines):
        self.lines = lines
        self.word_count = sum([len(line) for line in lines])

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, index):
        return self.lines[index]
    
    # get all text before cursor
    def prefix(self, cursor):
        if cursor.row == 0:
            return self.lines[0][:cursor.col]
        return "\n".join(self.lines[:cursor.row]) + '\n' + self.lines[cursor.row][:cursor.col]

    def suffix(self, cursor):
        if cursor.row == len(self) - 1:
            return self[cursor.row][cursor.col:]
        return self[cursor.row][cursor.col:] + "\n".join(self.lines[cursor.row + 1:])
        

    @property
    def bottom(self):
        return len(self) - 1

    def insert(self, cursor, string):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        new = current[:col] + string + current[col:]
        self.lines.insert(row, new)
        self.word_count += len(string)

    def split(self, cursor):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        self.lines.insert(row, current[:col])
        self.lines.insert(row + 1, current[col:])
        self.word_count += 1

    def delete(self, cursor):
        row, col = cursor.row, cursor.col
        if col < len(self[row]): # if left did not move cursor up
            current = self.lines.pop(row) 
            new = current[:col] + current[col+1:]
            self.lines.insert(row, new)
        else: # if left moved cursor up
            current = self.lines.pop(row) 
            next = self.lines.pop(row)
            new = current + next
            self.lines.insert(row, new)
        self.word_count -= 1


def clamp(x, lower, upper):
    if x < lower:
        return lower
    if x > upper:
        return upper
    return x


class Cursor:
    def __init__(self, n_cols, row=0, col=0, col_hint=None):
        self.row = row
        self.col = col
        self.row_offset = 0
        self.n_cols = n_cols


    def up(self, buffer):
        if self.row > 0:
            self.row -= 1
            # self.row_offset -= (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset -= get_line_height(buffer[self.row], self.n_cols)
            self.col = clamp(self.col, 0, len(buffer[self.row]))

    def down(self, buffer):
        if self.row < len(buffer) - 1:
            # self.row_offset += (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset += get_line_height(buffer[self.row], self.n_cols)
            self.row += 1
            self.col = clamp(self.col, 0, len(buffer[self.row]))
        else:
            self.col = len(buffer[self.row])
            

    def left(self, buffer):
        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            self.row -= 1
            # self.row_offset -= (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset -= get_line_height(buffer[self.row], self.n_cols)
            self.col = len(buffer[self.row])

    def right(self, buffer):
        if self.col < len(buffer[self.row]):
            self.col += 1
        elif self.row < len(buffer) - 1:
            # self.row_offset += (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset += get_line_height(buffer[self.row], self.n_cols)
            self.row += 1
            self.col = 0


class Window:
    def __init__(self, n_rows, n_cols, row=0, col=0):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.row = row
        self.row_offset = 0

    @property
    def bottom(self):
        return self.row + self.n_rows - 1

    def up(self, buffer, cursor):
        if cursor.row == self.row - 1 and self.row > 0:
            self.row -= 1
            # self.row_offset += (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset += get_line_height(buffer[self.row], self.n_cols)

    def down(self, buffer, cursor):
        # line_height = (line_width(buffer[cursor.row]))//self.n_cols
        cursor_line_height = get_line_height(buffer[cursor.row], self.n_cols)
        while self.translate(cursor, buffer)[0] + cursor_line_height >= self.n_rows - 1 :
            # self.row_offset -= (line_width(buffer[self.row])+1)//self.n_cols
            self.row_offset -= get_line_height(buffer[self.row], self.n_cols)
            self.row += 1
            # cursor_line_height = get_line_height(buffer[self.row], self.n_cols)

    # def horizontal_scroll(self, cursor, left_margin=5, right_margin=2):
    #     n_pages = cursor.col // (self.n_cols - right_margin)
    #     self.col = max(n_pages * self.n_cols - right_margin - left_margin, 0)

    def translate(self, cursor, buffer):
        display_row = cursor.row - self.row + self.row_offset + cursor.row_offset
        line_start = 0
        lw = 0
        for cursor_col in range(cursor.col):
            # lw = line_width(buffer[cursor.row][line_start:cursor_col+1])
            lw += char_width(buffer[cursor.row][cursor_col])
            if lw < self.n_cols:
                continue
            display_row += 1
            # line_start = cursor_col + 1 
            lw = 0
        return display_row, lw

        # lw = line_width(buffer[cursor.row][:cursor.col])
        # return display_row + (lw)//(self.n_cols-1), lw % (self.n_cols-1)



class Editor:
    def __init__(self, stdscr, filename, keypresses_list = [], func_after_keypress = None, func_before_keypress = None, auto_save=False):
        self.stdscr = stdscr
        self.window = Window(curses.LINES - 1, curses.COLS - 1)
        self.cursor = Cursor(n_cols = curses.COLS-1)
        self.filename = filename
        if filename:
            self.buffer = Buffer(self.read_file(filename).splitlines())
        else:
            self.buffer = Buffer([""])
        self.keypresses_list = keypresses_list
        self.func_after_keypress = func_after_keypress
        self.func_before_keypress = func_before_keypress
        self.saved = False
        self.auto_save = auto_save
    def display_welcomepage(self):
        instructions = """
- backspace or delete: delete the character before the cursor
- esc: exit the editor and save the text
- ctrl + t: save the text
- ctrl + n: go to the bottom of the text
- right arrow: move cursor right
- left arrow: move cursor left
- down arrow: move cursor down
- up arrow: move cursor up
- enter: split the line
"""
        
        for keypress in self.keypresses_list:
            for key in keypress["key"]:
                print (key)
                if isinstance(key, int):
                    instructions += f"\n- {ascii_to_key(key)}: {keypress['description']}"
                elif len(key) == 1:
                    instructions += f"\n- {ascii_to_key(ord(key))}: {keypress['description']}"
                else: 
                    instructions += f"\n- {key}: {keypress['description']}"

        instructions += "\n\npress Enter to continue..."
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(instructions)
            self.stdscr.refresh()
            key = self.stdscr.get_wch()
            if key == "\n":
                break
    def read_file(self, filename):
        with open(filename) as f:
            return f.read()

    def display_buffer(self):
        self.stdscr.erase()
        display_rows = 0
        for row, line in enumerate(self.buffer[self.window.row:]):
            chunks = []
            line = line.strip() + " "
            while True:
                chunk = ""
                chunk_width = 0
                while line and chunk_width < self.window.n_cols:
                    chunk += line[0]
                    line = line[1:]
                    chunk_width += char_width(chunk[-1])
                chunks.append(chunk)
                if not line:
                    break

            for i, chunk in enumerate(chunks):
                if display_rows + i < self.window.n_rows:
                    self.stdscr.addstr(display_rows + i, 0, chunk)
                else:
                    break
            display_rows += len(chunks)
        # use last line to display col, row, row_offsets, word_count
        if not self.saved:
            self.stdscr.addstr(curses.LINES-1, 0, f"row: {self.cursor.row}, col: {self.cursor.col}, w_row: {self.window.row} w_row_off: {self.window.row_offset}, c_row_off: {self.cursor.row_offset}, word_count: {self.buffer.word_count}")
        else:
            self.stdscr.addstr(curses.LINES-1, 0, f"row: {self.cursor.row}, col: {self.cursor.col}, w_row_off: {self.window.row_offset}, c_row_off: {self.cursor.row_offset}, word_count: {self.buffer.word_count} - saved")
        self.saved = False

    def translate_cursor(self):
        self.stdscr.move(*self.window.translate(self.cursor, self.buffer))

    def left(self):
        self.cursor.left(self.buffer)
        self.window.up(self.buffer, self.cursor)
    
    def right(self):
        self.cursor.right(self.buffer)
        self.window.down(self.buffer, self.cursor)
    
    def insert(self, string):
        for char in string:
            if char == "\n":
                self.buffer.split(self.cursor)
            else:
                self.buffer.insert(self.cursor, char)
            self.right()

    def goto_bottom(self):
        while self.cursor.row < self.buffer.bottom or self.cursor.col < len(self.buffer[self.cursor.row]):
            self.right()
    
    def save(self):
        if len(self.filename) > 1:
            text = "\n".join(self.buffer)
            with open(self.filename, 'w') as file:
                file.write(text)
        self.saved = True

    """
    add special keypresses to customize functionalities. 
    it does not handle the keypresses, just add them as Editor attributes
    input: 
        List of dictionary with entries 
            key: str or int, 
            func: a callable that takes three inputs: window, buffer, and cursor
            description: (str)
    """
    def handle_keypress(self, k):
        special_keypress = False
        # add special keypresses
        if self.keypresses_list is not None:
            for keypress in self.keypresses_list:
                if k in keypress["key"]:
                    keypress["func"](self)
                    special_keypress = True
        if isinstance(k, str):
            # esc 
            # if k == "\x1b" or k == '\x14': 
            if k == "\x1b":
                save_buffer(self.buffer, self.stdscr)
                sys.exit(0)
            # ctrl + t
            elif k == "\x14":
                self.save()
            # goto bottom if ctrl + n
            elif k == "\x0e":
                self.goto_bottom()
            elif k == "KEY_LEFT":
                self.left()
            elif k == "KEY_DOWN":
                self.window.down(self.buffer, self.cursor)
                self.cursor.down(self.buffer)
                
            elif k == "KEY_UP":
                self.cursor.up(self.buffer)
                self.window.up(self.buffer, self.cursor)
            elif k == "KEY_RIGHT":
                self.right()
            elif k == "\n":
                self.buffer.split(self.cursor)
                self.right()
            elif k in ("KEY_DELETE", "\x04", "KEY_BACKSPACE", "\x7f"):
                if self.cursor.col > 0 or self.cursor.row > 0:
                    self.left()
                    self.buffer.delete(self.cursor)
            elif not special_keypress:
                self.buffer.insert(self.cursor, k)
                for _ in k:
                    self.right()
            

        elif isinstance(k, int):
            if k == curses.KEY_LEFT:
                self.left()
            elif k == curses.KEY_DOWN:
                self.cursor.down(self.buffer)
                self.window.down(self.buffer, self.cursor)
            elif k == curses.KEY_UP:
                self.cursor.up(self.buffer)
                self.window.up(self.buffer, self.cursor)
            elif k == curses.KEY_RIGHT:
                self.right()
            elif k == curses.KEY_DC or k == curses.KEY_BACKSPACE:
                if self.cursor.col > 0 or self.cursor.row > 0:
                    self.left()
                    self.buffer.delete(self.cursor)

    def run(self):
        self.display_welcomepage()
        ops = 0
        while True:
            self.display_buffer()
            self.translate_cursor()
            k = self.stdscr.get_wch()
            if self.func_before_keypress:
                self.func_before_keypress(self)
            self.handle_keypress(k)
            if self.func_after_keypress:
                self.func_after_keypress(self)
            ops += 1
            if self.auto_save and ops % 100 == 0:
                self.save()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs="?")
    parser.add_argument("--auto-save", action="store_true", default=False)
    return parser.parse_args()

def main(stdscr):
    args = parse_args()
    """
    def add_user_token(editor):
        user_token = "<|user|>"
        editor.buffer.insert(editor.cursor, user_token)
        for _ in user_token:
            editor.right()
            editor.cursor.right(editor.buffer)
    
    
    keypresses_list = [
        {
            # ctrl + u
            "key": ["\x15", "\n"],
            "func": add_user_token,
            "description": "Add user token"
        }
    ]
    editor = Editor(stdscr, args.filename, keypresses_list, func_before_keypress=add_user_token)
    """

    editor = Editor(stdscr, args.filename, auto_save=args.auto_save)
    editor.run()

if __name__ == "__main__":
    curses.wrapper(main)