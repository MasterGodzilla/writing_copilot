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
        # with open(f"text/{file_name.strip()}.txt", 'w') as file:
        with open(file_name.strip(), 'w') as file:
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


import string

def create_ascii_to_key_mapping():
    mapping = {}
    
    # Standard printable ASCII characters
    for char in string.printable:
        mapping[ord(char)] = char
    
    # Control characters
    ctrl_chars = {
        1: 'Ctrl + A', 2: 'Ctrl + B', 3: 'Ctrl + C', 4: 'Ctrl + D', 5: 'Ctrl + E',
        6: 'Ctrl + F', 7: 'Ctrl + G', 8: 'Ctrl + H', 9: 'Ctrl + I', 10: 'Ctrl + J',
        11: 'Ctrl + K', 12: 'Ctrl + L', 13: 'Ctrl + M', 14: 'Ctrl + N', 15: 'Ctrl + O',
        16: 'Ctrl + P', 17: 'Ctrl + Q', 18: 'Ctrl + R', 19: 'Ctrl + S', 20: 'Ctrl + T',
        21: 'Ctrl + U', 22: 'Ctrl + V', 23: 'Ctrl + W', 24: 'Ctrl + X', 25: 'Ctrl + Y',
        26: 'Ctrl + Z', 27: 'ESC', 28: 'FS', 29: 'GS', 30: 'RS', 31: 'US'
    }
    mapping.update(ctrl_chars)
    
    return mapping

def ascii_to_key(ascii_code):
    mapping = create_ascii_to_key_mapping()
    return mapping.get(ascii_code, f"Unknown ({ascii_code})")

# # Example usage
# print(ascii_to_key(ord('\x14')))  # Output: Ctrl + T
# print(ascii_to_key(ord('A')))     # Output: A
# print(ascii_to_key(27))           # Output: ESC