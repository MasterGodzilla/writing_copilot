from typing import Any, Callable
from abc import ABC, abstractmethod

from run import completion

# print to log.txt
def print_to_log(text: str):
    with open("log.txt", "a") as file:
        file.write(text + "\n")



class Copilot(ABC):
    
    def __init__(self, 
                    sliding_window: int = -1,
                    fill_len: int = 7,
                    system_prompt: str = "",
                    ):
    
        self.sliding_window = sliding_window
        self.fill_len = fill_len
        self.system_prompt = system_prompt
    
    @abstractmethod
    def __call__(self, text: str, suffix: str = '') -> str:
        pass


class TogetherCopilot(Copilot):

    def __init__(self, 
                    sliding_window: int = -1,
                    fill_len: int = 7,
                    system_prompt: str = "",
                    model: str = "Qwen/Qwen1.5-32B",
                    model_type: str = None,
                    chat_template: str = None,
                    ):
        super().__init__(sliding_window, fill_len, system_prompt)
        self.model = model
        if model_type is None:
            self.model_type = "chat" if "chat" in model else "base"
        else:
            self.model_type = model_type
        supported_chat_template = ['Qwen',]
        if chat_template is None and self.model_type == "chat":
            for template in supported_chat_template:
                if template in model:
                    self.chat_template = template
                    break
            else:
                print_to_log ("Chat template not supported, using default = 'Qwen'")

    
    def __call__(self, text, suffix: str = '') -> str:
        print_to_log ("text: "+ text)
        if self.sliding_window > 0:
            if self.model_type == "chat":
                try:
                    user_prompt = text[text.rindex("<|im_start|> user"):text.index("<|im_end|>")+len("<|im_end|>")]
                except ValueError:
                    user_prompt = "" 
                parsed_text = text.replace("<|im_start|> user\n", "")
                parsed_text = "<|im_start|> assistant\n" + parsed_text
                prompt = self.system_prompt + user_prompt + parsed_text[-min(len(parsed_text)-len(user_prompt)-1, self.sliding_window):]
            else: 
                prompt = self.system_prompt + text[-min(len(text)-1, self.sliding_window):]
        else:
            prompt = self.system_prompt + text
        
        response = completion(prompt, self.model, self.fill_len, 0.8)
        return response
