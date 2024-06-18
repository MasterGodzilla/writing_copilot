from typing import Any, Callable
from abc import ABC, abstractmethod

from run import completion

with open("insertion_prompt.txt", "r") as file:
    insertion_prompt = file.read()

# print to log.txt
def print_to_log(text: str):
    with open("log.txt", "a") as file:
        file.write(text + "\n")




from run import completion, openai_completion
import concurrent.futures

# try call the model. if no response in 1 second, return "error"
def call_model(prompt: str,
                model: str = "Qwen/Qwen1.5-110B-Chat",
                max_tokens: int = 1000,
                temperature: float = 0.6,
                stop: list = ["</s>"],
                unstable: bool = False):
    if not unstable:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(completion, prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature, stop=stop)
            try:
                return future.result(timeout=1)
            # except any 
            except Exception as e:
                return str(e)
    else:
        return unstable_call_model(prompt, model, max_tokens, temperature, stop)
    
import pickle
# load chinese tokens and unstable tokens
with open("chinese_tokens.pkl", "rb") as file:
    chinese_tokens = pickle.load(file)
with open("unstable_tokens.pkl", "rb") as file:
    unstable_tokens = pickle.load(file)

def unstable_call_model(prompt: str,
                        model: str = "Qwen/Qwen1.5-110B-Chat",
                        max_tokens: int = 1000,
                        temperature: float = 0.6,
                        stop: list = ["</s>"]):
    """
    Unstable call for text completion avoids unnatural splits of Chinese tokens. 
    e.g. "我是" should not be split into "我" and "是" in the completion.
    thus, we need to check the last few tokens in the prompt to see if they are in the unstable tokens.
    then, we need to call the model with the last few tokens not in the prompt, but use logit_bias
    to bias the completion towards the last few tokens in the prompt.
    
    """

    max_token_length = 4
    if len(prompt)<1:
        return call_model(prompt, model, max_tokens, temperature, stop, unstable=False)
    # if the last words in the prompt are not in the unstable tokens, return the normal call_model
    last1 = prompt[-1]
    last2 = None if len(prompt) < 2 else prompt[-2:]
    last3 = None if len(prompt) < 3 else prompt[-3:]

    # if none of the last words are in the unstable tokens, return the normal call_model
    if last1 not in unstable_tokens and last2 not in unstable_tokens and last3 not in unstable_tokens:
        return call_model(prompt, model, max_tokens, temperature, stop, unstable=False)
    

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

        # remove the last "user" token if not closed with end token
        if self.model_type == "chat":
            # find the last user token
            user_token_index = text.rfind("<|im_start|> user")
            # if no end token after the last user token, remove the last user token
            if "<|im_end|>" not in text[user_token_index:]:
                # remove the last user token with user_token_index
                text = text[:user_token_index] + text[user_token_index+len("<|im_start|> user"):]
                print_to_log ("text after removing last user token: "+ text)

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
        
        # if suffix:
        #     prefix = prompt
        #     prompt = eval(f'f"""{insertion_prompt}"""')
        #     print_to_log ("prompt: "+ prompt)
        
        response = call_model(prompt, self.model, self.fill_len, 0.8)
        print_to_log ("response: "+ response)
        return response

class GeminiCopilot(Copilot):

        def __init__(self, 
                        sliding_window: int = -1,
                        fill_len: int = 7,
                        system_prompt: str = "",
                        model: str = "flash", # "flash" or "pro"
                        ):
            super().__init__(sliding_window, fill_len, system_prompt)
            self.model = model
        
        def __call__(self, text, suffix: str = '') -> str:
            pass