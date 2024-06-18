import curses
import concurrent.futures
import locale
# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')


def save_buffer(buffer, stdscr):
    text = "\n".join(buffer)
    save_text(text, stdscr)

def save_text(text, stdscr):
    file_name = ""
    while True:
        stdscr.erase()
        # highlight cursor position with a special character
        stdscr.addstr("Enter the file name: "+file_name)
        key = stdscr.get_wch()

        if isinstance(key, str):
            if key == "\n":
                break
            elif key in ("KEY_DELETE", "\x04", "KEY_BACKSPACE", "\x7f"):
                if file_name:
                    file_name = file_name[:-1]
            else:
                file_name += key
        elif isinstance(key, int):
            if key == curses.KEY_DC or key == curses.KEY_BACKSPACE:
                if file_name:
                    file_name = file_name[:-1]
    # if empty file name, do not save
    if len(file_name) > 1:
        with open(f"text/{file_name.strip()}.txt", 'w') as file:
            file.write(text)

def display_welcomepage(stdscr):
    """
    A welcome page that displays the welcome message and instructions.
    
    """

    instructions = """
- backspace or delete: delete the character before the cursor
- esc: exit the editor and save the text
- right arrow: autocomplete the text
- left arrow: undo the autocomplete
- control-a: add <|im_start|> assistant\\n
- control-u: add <|im_start|> user\\n
- control-e: add <|im_end|>\\n

press Enter to continue...
"""
    while True:
        stdscr.clear()
        stdscr.addstr(instructions)
        stdscr.refresh()
        key = stdscr.get_wch()
        if key == "\n":
            break