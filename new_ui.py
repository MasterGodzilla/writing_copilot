import curses
from utils import save_text, display_welcomepage

def backspace(text, cursor_y, cursor_x):
    lines = text.split('\n')
    if cursor_x > 0:
        lines[cursor_y] = lines[cursor_y][:cursor_x - 1] + lines[cursor_y][cursor_x:]
        cursor_x -= 1
    elif cursor_y > 0:
        prev_line_length = len(lines[cursor_y - 1])
        lines[cursor_y - 1] += lines[cursor_y]
        del lines[cursor_y]
        cursor_y -= 1
        cursor_x = prev_line_length
    text = '\n'.join(lines)
    return text, cursor_y, cursor_x

def main(stdscr):
    # Clear screen
    stdscr.clear()

    # Turn off cursor blinking
    curses.curs_set(0)

    # Set up the window
    max_y, max_x = stdscr.getmaxyx()

    display_welcomepage(stdscr)

    # Initial editor content
    text = ""
    cursor_y, cursor_x = 0, 0
    scroll_offset = 0

    while True:
        stdscr.clear()
        lines = text.split('\n')
        visible_lines = lines[scroll_offset:scroll_offset + max_y]
        for i, line in enumerate(visible_lines):
            if i + scroll_offset == cursor_y:
                stdscr.addstr(i, 0, line[:cursor_x] + '█' + line[cursor_x:])
            else:
                stdscr.addstr(i, 0, line)
        
        stdscr.refresh()

        key = stdscr.get_wch()  # get_wch() supports wide characters

        if isinstance(key, str):
            if key == "\n":  # Enter key
                lines[cursor_y] = lines[cursor_y][:cursor_x] + '\n' + lines[cursor_y][cursor_x:]
                cursor_y += 1
                cursor_x = 0
                text = '\n'.join(lines)
            elif key == "\x1b":  # Escape key to exit
                save_text(text, stdscr)
                break
            elif key in ("\x08", "\x7f"):  # Backspace key
                text, cursor_y, cursor_x = backspace(text, cursor_y, cursor_x)
            elif key == "\x01":  # Command+Left (Home key)
                cursor_x = 0
            elif key == "\x05":  # Command+Right (End key)
                cursor_x = len(lines[cursor_y])
            else:  # Any other key
                lines[cursor_y] = lines[cursor_y][:cursor_x] + key + lines[cursor_y][cursor_x:]
                cursor_x += 1
                text = '\n'.join(lines)
        else:
            if key == curses.KEY_BACKSPACE:
                text, cursor_y, cursor_x = backspace(text, cursor_y, cursor_x)
            elif key == curses.KEY_LEFT:
                if cursor_x > 0:
                    cursor_x -= 1
                elif cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = len(lines[cursor_y])
            elif key == curses.KEY_RIGHT:
                if cursor_x < len(lines[cursor_y]):
                    cursor_x += 1
                elif cursor_y < len(lines) - 1:
                    cursor_y += 1
                    cursor_x = 0
            elif key == curses.KEY_UP:
                if cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = min(cursor_x, len(lines[cursor_y]))
                if cursor_y < scroll_offset:
                    scroll_offset -= 1
            elif key == curses.KEY_DOWN:
                if cursor_y < len(lines) - 1:
                    cursor_y += 1
                    cursor_x = min(cursor_x, len(lines[cursor_y]))
                if cursor_y >= scroll_offset + max_y:
                    scroll_offset += 1

        # Ensure the cursor position is valid
        cursor_y = max(0, min(cursor_y, len(lines) - 1))
        cursor_x = max(0, min(cursor_x, len(lines[cursor_y])))
        scroll_offset = max(0, min(scroll_offset, len(lines) - max_y))

        # Ensure the cursor is within the visible window
        if cursor_y - scroll_offset < 0:
            scroll_offset = cursor_y
        elif cursor_y - scroll_offset >= max_y:
            scroll_offset = cursor_y - max_y + 1

        # Redraw the screen
        stdscr.clear()
        visible_lines = lines[scroll_offset:scroll_offset + max_y]
        for i, line in enumerate(visible_lines):
            if i + scroll_offset == cursor_y:
                stdscr.addstr(i, 0, line[:cursor_x] + '█' + line[cursor_x:])
            else:
                stdscr.addstr(i, 0, line)
        stdscr.move(cursor_y - scroll_offset, cursor_x)
        stdscr.refresh()

def start_editor():
    curses.wrapper(main)

if __name__ == "__main__":
    start_editor()
