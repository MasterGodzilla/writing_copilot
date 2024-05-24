import argparse
import curses
import sys
import wcwidth
import locale
from utils import save_text, display_welcomepage, save_buffer
from copilot import TogetherCopilot
from editor import Buffer, Cursor, Window, char_width, left, right

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

def main(stdscr):
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    args = parser.parse_args()

    with open(args.filename) as f:
        buffer = Buffer(f.read().splitlines())

    window = Window(curses.LINES - 1, curses.COLS - 1)
    cursor = Cursor()
    # copilot = TogetherCopilot()
    copilot = TogetherCopilot(model="Qwen/Qwen1.5-32B-chat", model_type="chat")
    # a better name for wait_to_be_accepted
    draft_len = 0

    while True:
        stdscr.erase()

        window.n_cols = curses.COLS - 1
        window.n_rows = curses.LINES - 2
        cursor.n_cols = curses.COLS - 1

        display_rows = 0
        for row, line in enumerate(buffer[window.row:]):
            chunks = []
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
            
        display_str = f"cursor: {cursor.row}, {cursor.col}, {cursor.row_offset}"
        display_str += f", window: {window.row}, {window.row_offset}"
        display_str += f", buffer: {len(buffer)}, {len(buffer[cursor.row])}"
        display_str += f", word count: {buffer.word_count}"
        stdscr.addstr(curses.LINES-1, 0, display_str)
        
        stdscr.move(*window.translate(cursor, buffer))
        keep_draft = False

        k = stdscr.get_wch()  # Use get_wch instead of getkey
        if isinstance(k, str):
            if k == "\x1b":  # ESC key
                save_buffer(buffer, stdscr)
                sys.exit(0)
            # for auto complete we use ctrl + e
            elif k == "\t":
                response = copilot(buffer.prefix(cursor))
                draft_len = len(response)
                keep_draft = True
                for char in response:
                    if char == "\n":
                        buffer.split(cursor)
                    else:
                        buffer.insert(cursor, char)
                    right(window, buffer, cursor)
            
            # cltr + a for undo
            elif k == "\x05":
                if draft_len > 0:
                    for _ in range(draft_len):
                        left(window, buffer, cursor)
                        buffer.delete(cursor)
                    draft_len = 0

            # # cltr + u for user
            # elif k == "\x15":
            #     buffer.insert(cursor, "<|im_start|> user\n")
            #     for _ in "<|im_start|> user\n":
            #         right(window, buffer, cursor)

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
                    if draft_len > 0:
                        draft_len -= 1
                        keep_draft = True
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
                    if draft_len > 0:
                        draft_len -= 1
                        keep_draft = True
                
        if not keep_draft:
            draft_len = 0
                
        


if __name__ == "__main__":
    curses.wrapper(main)
