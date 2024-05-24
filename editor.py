import argparse
import curses
import sys
import wcwidth
import locale
from utils import save_text, display_welcomepage, save_buffer

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

def char_width(character):
    width = wcwidth.wcwidth(character)
    return max(0, width)

def line_width(line):
    return sum(char_width(c) for c in line)

class Buffer:
    def __init__(self, lines):
        self.lines = lines

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, index):
        return self.lines[index]

    @property
    def bottom(self):
        return len(self) - 1

    def insert(self, cursor, string):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        new = current[:col] + string + current[col:]
        self.lines.insert(row, new)

    def split(self, cursor):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        self.lines.insert(row, current[:col])
        self.lines.insert(row + 1, current[col:])

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


def clamp(x, lower, upper):
    if x < lower:
        return lower
    if x > upper:
        return upper
    return x


class Cursor:
    def __init__(self, row=0, col=0, col_hint=None):
        self.row = row
        self.col = col
        self.row_offset = 0


    def up(self, buffer):
        if self.row > 0:
            self.row -= 1
            self.row_offset -= (line_width(buffer[self.row]))//self.n_cols
            self.col = clamp(self.col, 0, len(buffer[self.row]))

    def down(self, buffer):
        if self.row < len(buffer) - 1:
            self.row_offset += (line_width(buffer[self.row]))//self.n_cols
            self.row += 1
            self.col = clamp(self.col, 0, len(buffer[self.row]))
            

    def left(self, buffer):
        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            self.row -= 1
            self.row_offset -= (line_width(buffer[self.row]))//self.n_cols
            self.col = len(buffer[self.row])

    def right(self, buffer):
        if self.col < len(buffer[self.row]):
            self.col += 1
        elif self.row < len(buffer) - 1:
            self.row_offset += (line_width(buffer[self.row]))//self.n_cols
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
            self.row_offset += (line_width(buffer[self.row]))//self.n_cols

    def down(self, buffer, cursor):
        line_height = (line_width(buffer[cursor.row]))//self.n_cols
        while self.translate(cursor, buffer)[0] + line_height >= self.n_rows - 1 :
            self.row_offset -= (line_width(buffer[self.row]))//self.n_cols
            self.row += 1
            

    # def horizontal_scroll(self, cursor, left_margin=5, right_margin=2):
    #     n_pages = cursor.col // (self.n_cols - right_margin)
    #     self.col = max(n_pages * self.n_cols - right_margin - left_margin, 0)

    def translate(self, cursor, buffer):
        display_row = cursor.row - self.row + self.row_offset + cursor.row_offset
        lw = line_width(buffer[cursor.row][:cursor.col])
        return display_row + (lw)//self.n_cols, lw % self.n_cols


def left(window, buffer, cursor):
    cursor.left(buffer)
    window.up(buffer, cursor)
    # window.horizontal_scroll(cursor)


def right(window, buffer, cursor):
    cursor.right(buffer)
    window.down(buffer, cursor)
    # window.horizontal_scroll(cursor)


def main(stdscr):
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    args = parser.parse_args()

    with open(args.filename) as f:
        buffer = Buffer(f.read().splitlines())

    window = Window(curses.LINES - 1, curses.COLS - 1)
    cursor = Cursor()

    while True:
        stdscr.erase()
        # for row, line in enumerate(buffer[window.row:window.row + window.n_rows]):
        #     if row == cursor.row - window.row and window.col > 0:
        #         line = "«" + line[window.col + 1:]
        #     if len(line) > window.n_cols:
        #         line = line[:window.n_cols - 1] + "»"
        #     stdscr.addstr(row, 0, line)

        window.n_cols = curses.COLS - 1
        window.n_rows = curses.LINES - 2
        cursor.n_cols = curses.COLS - 1

        display_rows = 0
        for row, line in enumerate(buffer[window.row:]):
            # split line into chunks that fit the window by line_width
            chunks = []
            # remove all \n
            line = line.strip()
            while True:
                chunk = ""
                chunk_width = 0
                while line and chunk_width < window.n_cols - 1:
                    chunk += line[0]
                    line = line[1:]
                    chunk_width += char_width(chunk[-1])
                chunks.append(chunk)
                if not line:
                    break
            
            for i, chunk in enumerate(chunks):
                if display_rows + i < window.n_rows:
                    stdscr.addstr(display_rows + i, 0, chunk)
                else: 
                    break
            display_rows += len(chunks)
            # display_rows += line_width(line)//window.n_cols + 1
            # if display_rows >= window.n_rows:
            #     break
            # stdscr.addstr(row, 0, line)
        display_str = f"cursor: {cursor.row}, {cursor.col}, {cursor.row_offset}"
        display_str += f", window: {window.row}, {window.row_offset}"
        display_str += f", buffer: {len(buffer)}, {len(buffer[cursor.row])}"
        stdscr.addstr(curses.LINES-1, 0, display_str)
            
        
        stdscr.move(*window.translate(cursor, buffer))

        # k = stdscr.getkey()
        # # k = stdscr.get_wch()
        # if k == "\x1b":
        #     save_buffer(buffer, stdscr)
        #     sys.exit(0)
        # elif k == "KEY_LEFT":
        #     left(window, buffer, cursor)
        # elif k == "KEY_DOWN":
        #     cursor.down(buffer)
        #     window.down(buffer, cursor)
        #     # window.horizontal_scroll(cursor)
        # elif k == "KEY_UP":
        #     cursor.up(buffer)
        #     window.up(buffer, cursor)
        #     # window.horizontal_scroll(cursor)
        # elif k == "KEY_RIGHT":
        #     right(window, buffer, cursor)
        # elif k == "\n":
        #     buffer.split(cursor)
        #     right(window, buffer, cursor)
        # elif k in ("KEY_DELETE", "\x04","KEY_BACKSPACE", "\x7f"):
        #     if cursor.col > 0 or cursor.row > 0:
        #         left(window, buffer, cursor)
        #         buffer.delete(cursor)
        k = stdscr.get_wch()  # Use get_wch instead of getkey

        if isinstance(k, str):
            if k == "\x1b":  # ESC key
                save_buffer(buffer, stdscr)
                sys.exit(0)
            elif k == "KEY_LEFT":
                left(window, buffer, cursor)
            elif k == "KEY_DOWN":
                cursor.down(buffer)
                window.down(buffer, cursor)
            elif k == "KEY_UP":
                cursor.up(buffer)
                window.up(buffer, cursor)
            elif k == "KEY_RIGHT":
                right(window, buffer, cursor)
            elif k == "\n":  # Enter key
                buffer.split(cursor)
                right(window, buffer, cursor)
            elif k in ("KEY_DELETE", "\x04", "KEY_BACKSPACE", "\x7f"):
                if cursor.col > 0 or cursor.row > 0:
                    left(window, buffer, cursor)
                    buffer.delete(cursor)
            else:
                buffer.insert(cursor, k)
                for _ in k:
                    right(window, buffer, cursor)

        elif isinstance(k, int):
            if k == curses.KEY_LEFT:
                left(window, buffer, cursor)
            elif k == curses.KEY_DOWN:
                cursor.down(buffer)
                window.down(buffer, cursor)
            elif k == curses.KEY_UP:
                cursor.up(buffer)
                window.up(buffer, cursor)
            elif k == curses.KEY_RIGHT:
                right(window, buffer, cursor)
            elif k == curses.KEY_DC or k == curses.KEY_BACKSPACE:
                if cursor.col > 0 or cursor.row > 0:
                    left(window, buffer, cursor)
                    buffer.delete(cursor)
                
            
                
        


if __name__ == "__main__":
    curses.wrapper(main)
