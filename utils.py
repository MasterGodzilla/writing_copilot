def save_text(text, stdscr):

    file_name = ""
    while True:
        stdscr.clear()
        # highlight cursor position with a special character
        stdscr.addstr("Enter the file name: "+file_name+"█")
        stdscr.refresh()
        file_name += stdscr.get_wch()
        if file_name[-1] == "\n":
            break
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