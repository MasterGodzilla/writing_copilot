import argparse
import curses
import sys
import wcwidth
import locale
from utils import save_text, display_welcomepage, save_buffer
from copilot import TogetherCopilot, get_copilot
# from editor import Buffer, Cursor, Window, char_width, left, right, Editor
from editor import Editor

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

def add_user_token(editor):
    user_token = "<user>"
    editor.insert(user_token)

def add_end_token(editor):
    end_token = "</user>\n"
    editor.insert(end_token)

def copilot(editor, copilot):
    response = copilot(editor.buffer.prefix(editor.cursor), editor.buffer.suffix(editor.cursor))
    editor.draft_len = len(response)  # Update the draft_len attribute of the editor object
    editor.keep_draft = True  # Update the keep_draft attribute of the editor object
    editor.insert(response)

def remove_completion(editor, max_deletions=15):
    if editor.draft_len > 0:  # Access the draft_len attribute of the editor object
        for _ in range(min(editor.draft_len, max_deletions)):
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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs='?', default="")
    # add arguments --model --provider --sliding_window(default -1)
    parser.add_argument("--model", type=str, default="Qwen/Qwen2-72B-Instruct")
    # parser.add_argument("--model_type", type=str, default="chat")
    parser.add_argument("--sliding_window", type=int, default=-1)
    parser.add_argument("--provider", type=str, default=None)
    parser.add_argument('--system_prompt', type=str, default="")
    parser.add_argument('--fill_len', type=int, default=7)
    parser.add_argument("--auto-save", action="store_true", default=False)
    return parser.parse_args()

def get_system_prompt(system_prompt):
    if system_prompt:
        try:
            with open(f'prompts/{system_prompt}.txt', 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"System prompt file {system_prompt}.txt not found.")
            return ""
    return ""

def main(stdscr):
    args = parse_args()
    system_prompt = get_system_prompt(args.system_prompt)
    # copilot_instance = TogetherCopilot(model="Qwen/Qwen2-72B-Instruct", model_type="chat", sliding_window=500)
    copilot_instance = get_copilot(model = args.model, 
                                    provider = args.provider, 
                                    sliding_window = args.sliding_window,
                                    system_prompt = system_prompt,
                                    fill_len = args.fill_len)

    keypresses_list = [
        {
            "key": ["\x15"],  # ctrl + u
            "func": add_user_token,
            "description": "Add user token '<user>'"
        },
        {
            "key": ["\x05"],  # ctrl + e
            "func": add_end_token,
            "description": "Add end token '</user>'"
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
            "description": "decrease draft_len"
        }
    ]
    
    editor = Editor(stdscr, args.filename, keypresses_list, 
                    func_after_keypress=update_draft_len,
                    func_before_keypress=set_keep_draft,
                    auto_save=args.auto_save)
    editor.draft_len = 0  # Add a draft_len attribute to the editor object
    editor.keep_draft = False  # Add a keep_draft attribute to the editor object
    editor.run()

if __name__ == "__main__":
    curses.wrapper(main)
