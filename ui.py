import curses
import locale
from run import completion
import concurrent.futures

# Ensure the locale is set to support UTF-8
locale.setlocale(locale.LC_ALL, '')

import sys

sys.stdout = open('log.txt', 'w')

model = "Qwen/Qwen1.5-32B"
sliding_window = -1
fill_len = 15
chunk_delete = 10
system_prompt = "<|im_start|> system\n 你是一个每年稿费都有上千万的完美的小说作家。你用词生动，描写细致入微，文笔出彩。你擅长用对话，文字描述充满画面感，让人身临其境流连忘返。你喜欢用拟声词，比如“嗯，啊，呜，咦”。你会非常露骨的描写性爱场面，比如肉棒，阴茎，阴蒂，高潮。<|im_end|>\n"
drafts = 1 # not implemented yet


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


def call_model(prompt, max_tokens, model, temperature, stop=['\x08']):
    try:
        return completion(prompt=prompt, max_tokens=max_tokens, model=model, temperature=temperature, stop=stop)
    except Exception as e:
        print(f"Error calling model {model}: {e}")
        return " error "

def main(stdscr):
    # Clear screen
    stdscr.clear()

    # Turn off cursor blinking
    curses.curs_set(0)

    # Set up the window
    max_y, max_x = stdscr.getmaxyx()
    stdscr.scrollok(True)

    display_welcomepage(stdscr)

    # Initial editor content
    text = ""
    wait_to_be_accepted = 0

    while True:
        stdscr.clear()
        # highlight cursor position with a special character
        stdscr.addstr(text+"█")
        stdscr.refresh()

        key = stdscr.get_wch()  # get_wch() supports wide characters

        if isinstance(key, str):
            if key == "\n":  # Enter key
                text += '\n'
            elif key == "\x1b":  # Escape key to exit
                save_text(text, stdscr)
                break
            elif key in ("\x08", "\x7f"):  # Backspace key
                text = text[:-1]
                if wait_to_be_accepted > 0:
                    wait_to_be_accepted -= 1
            # control+u for adding <|im_start|> user\n
            elif key == "\x15":
                text += "<|im_start|> user\n"
            # control e for adding <|im_end|>\n
            # control+a for adding <|im_start|> assistant\n
            elif key == "\x01":
                text += "<|im_start|> assistant\n"
            elif key == "\x05":
                text += "<|im_end|>\n"
            # control s for saving the text
            elif key == "\x13":
                save_text(text, stdscr)
            else:
                text += key
        else:
            if key == curses.KEY_BACKSPACE:
                text = text[:-1]
                if wait_to_be_accepted > 0:
                    wait_to_be_accepted -= 1
            elif key == curses.KEY_LEFT:
                if wait_to_be_accepted > 1:
                    delete_len = min(wait_to_be_accepted, chunk_delete)
                    text = text[:-min(wait_to_be_accepted, len(text)-1)]
                    wait_to_be_accepted -= delete_len
                    assert wait_to_be_accepted >= 0, "wait_to_be_accepted should be non-negative"
            elif key == curses.KEY_RIGHT:
                # sliding window
                # first find user_prompt enclosed by <|im_start|> and <|im_end|>, including <|im_start|> and <|im_end|>

                # remove <|im_start|> user if <|im_end|> is not present
                if "<|im_end|>" not in text:
                    parsed_text = text.replace("<|im_start|> user\n", "")
                    parsed_text = "<|im_start|> assistant\n" + parsed_text
                else:
                    parsed_text = text
                if sliding_window > 0:
                    try:
                        user_prompt = text[text.rindex("<|im_start|> user"):text.index("<|im_end|>")+len("<|im_end|>")]
                    except ValueError:
                        user_prompt = "" 
                    prompt = system_prompt + user_prompt + parsed_text[-min(len(parsed_text)-len(user_prompt)-1, sliding_window):]
                else:
                    prompt = system_prompt + parsed_text

                response = call_model(prompt, fill_len, "Qwen/Qwen1.5-32B", 0.8)
                
                wait_to_be_accepted = len(response)
                text += response
                        


                

def start_editor():
    curses.wrapper(main)

if __name__ == "__main__":
    start_editor()
    sys.stdout.close()