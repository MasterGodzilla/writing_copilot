import argparse
import curses
import sys
import wcwidth
import locale
from utils import save_text, display_welcomepage, save_buffer
from copilot import TogetherCopilot
# from editor import Buffer, Cursor, Window, char_width, left, right, Editor
from editor import Editor

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs='?', default="")
    return parser.parse_args()

def add_user_token(editor):
    user_token = " user\n"
    editor.buffer.insert(editor.cursor, user_token)
    for _ in user_token:
        editor.right()
        editor.cursor.right(editor.buffer)

def add_end_token(editor):
    end_token = "\n"
    editor.buffer.insert(editor.cursor, end_token)
    for _ in end_token:
        editor.right()
        editor.cursor.right(editor.buffer)

def copilot(editor, copilot):
    response = copilot(editor.buffer.prefix(editor.cursor), editor.buffer.suffix(editor.cursor))
    editor.draft_len = len(response)  # Update the draft_len attribute of the editor object
    editor.keep_draft = True  # Update the keep_draft attribute of the editor object
    for char in response:
        if char == "\n":
            editor.buffer.split(editor.cursor)
        else:
            editor.buffer.insert(editor.cursor, char)
        editor.right()
        editor.cursor.right(editor.buffer)

def remove_completion(editor):
    if editor.draft_len > 0:  # Access the draft_len attribute of the editor object
        for _ in range(editor.draft_len):
            editor.left()
            editor.buffer.delete(editor.cursor)
            editor.draft_len -= 1
        editor.keep_draft = True

def decrease_draft_len(editor):
    if editor.draft_len > 0:
        editor.draft_len -= 1
        editor.keep_draft = True

def set_keep_draft(editor):
    editor.keep_draft = False

def update_draft_len(editor):
    if not editor.keep_draft:
        editor.draft_len = 0

def main(stdscr):
    args = parse_args()

    copilot_instance = TogetherCopilot(model="Qwen/Qwen2-72B-Instruct", model_type="chat", sliding_window=500)

    keypresses_list = [
        {
            "key": ["\x15"],  # ctrl + u
            "func": add_user_token,
            "description": "Add user token"
        },
        {
            "key": ["\x05"],  # ctrl + e
            "func": add_end_token,
            "description": "Add end token"
        },
        {
            "key": ["\t"],  # tab for copilot
            "func": lambda editor: copilot(editor, copilot_instance),
            "description": "Invoke Copilot"
        },
        {
            "key": ["\x01"],  # ctrl + a
            "func": remove_completion,
            "description": "Remove completion"
        },
        # decrease draft_len when delete is pressed
        { 
            "key": ["KEY_DC", "KEY_BACKSPACE", "\x04", "\x7f", curses.KEY_BACKSPACE, curses.KEY_DC],
            "func": decrease_draft_len,
            "description": ""
        }
    ]
    
    editor = Editor(stdscr, args.filename, keypresses_list, func_after_keypress=update_draft_len,func_before_keypress=set_keep_draft)
    editor.draft_len = 0  # Add a draft_len attribute to the editor object
    editor.keep_draft = False  # Add a keep_draft attribute to the editor object
    editor.run()

if __name__ == "__main__":
    curses.wrapper(main)
