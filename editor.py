import argparse
import curses
import sys
import wcwidth
import locale

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
        if (row, col) < (self.bottom, len(self[row])):
            current = self.lines.pop(row)
            if col < len(self[row]):
                new = current[:col] + current[col + 1:]
                self.lines.insert(row, new)
            else:
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
        self._col = col
        # col_hint is used to keep track of the column when moving up or down
        self._col_hint = col if col_hint is None else col_hint
        self.row_offset = 0

    @property
    def col(self):
        return self._col

    @col.setter
    def col(self, col):
        self._col = col
        self._col_hint = col


    # this method is used to keep the cursor column within the bounds of the line
    def _clamp_col(self, buffer):
        self._col = min(self._col_hint, len(buffer[self.row]))

    def up(self, buffer, n_cols):
        if self.row > 0:
            self.row -= 1
            self._clamp_col(buffer)
            self.row_offset -= line_width(buffer[self.row])//self.n_cols

    def down(self, buffer):
        if self.row < len(buffer) - 1:
            self.row += 1
            self._clamp_col(buffer)
            self.row_offset += line_width(buffer[self.row])//self.n_cols

    def left(self, buffer):
        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            self.row -= 1
            self.row_offset -= line_width(buffer[self.row])//self.n_cols
            self.col = len(buffer[self.row])

    def right(self, buffer):
        if self.col < len(buffer[self.row]):
            self.col += 1
        elif self.row < len(buffer[self.row]) - 1:
            self.row += 1
            self.row_offset += line_width(buffer[self.row])//self.n_cols
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
            self.row_offset += line_width(buffer[cursor.row])//self.n_cols

    def down(self, buffer, cursor):
        if cursor.row == self.bottom + 1 and self.bottom < len(buffer) - 1:
            self.row += 1
            self.row_offset -= line_width(buffer[cursor.row])//self.n_cols

    # def horizontal_scroll(self, cursor, left_margin=5, right_margin=2):
    #     n_pages = cursor.col // (self.n_cols - right_margin)
    #     self.col = max(n_pages * self.n_cols - right_margin - left_margin, 0)

    def translate(self, cursor, buffer):
        display_row = cursor.row - self.row + self.row_offset + cursor.row_offset
        lw = line_width(buffer[cursor.row][:cursor.col])
        return display_row + lw//self.n_cols, lw % self.n_cols


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
        window.n_rows = curses.LINES - 1
        cursor.n_cols = curses.COLS - 1

        for row, line in enumerate(buffer[window.row:]):
            # # split line into chunks that fit the window
            # chunks = [line[i:i + window.n_cols] for i in range(0, len(line), window.n_cols-1)]
            # if display_rows + len(chunks) >= window.n_rows:
            #     break 
            # for i, chunk in enumerate(chunks):
            #     stdscr.addstr(display_rows + i, 0, chunk)
            # display_rows += len(chunks)+1
            stdscr.addstr(row, 0, line)
        
        stdscr.move(*window.translate(cursor, buffer))

        k = stdscr.getkey()
        if k == "\x1b":
            sys.exit(0)
        elif k == "KEY_LEFT":
            left(window, buffer, cursor)
        elif k == "KEY_DOWN":
            cursor.down(buffer)
            window.down(buffer, cursor)
            # window.horizontal_scroll(cursor)
        elif k == "KEY_UP":
            cursor.up(buffer)
            window.up(cursor, buffer)
            # window.horizontal_scroll(cursor)
        elif k == "KEY_RIGHT":
            right(window, buffer, cursor)
        elif k == "\n":
            buffer.split(cursor)
            right(window, buffer, cursor)
        elif k in ("KEY_DELETE", "\x04"):
            buffer.delete(cursor)
        elif k in ("KEY_BACKSPACE", "\x7f"):
            if (cursor.row, cursor.col) > (0, 0):
                left(window, buffer, cursor)
                buffer.delete(cursor)
        else:
            buffer.insert(cursor, k)
            for _ in k:
                right(window, buffer, cursor)


if __name__ == "__main__":
    curses.wrapper(main)
