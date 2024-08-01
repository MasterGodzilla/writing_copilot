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

    supported_models = ["Qwen/Qwen1.5-32B",
                        "Qwen/Qwen1.5-32B-chat",
                        "Qwen/Qwen2-72B-Instruct",
                        ]
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

def check_overlap(text, response):
    # Determine the maximum length of overlap to check
    max_overlap = min(len(text), len(response))
    
    # Iterate through possible lengths of overlap from max to 1
    for length in range(max_overlap, 0, -1):
        if text[-length:] == response[:length]:
            return length  # Return the length of the overlap if found
    
    return 0

import google.generativeai as genai
import os
genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
class GeminiCopilot(Copilot):
    supported_models = ["gemini-1.5-flash", "gemini-1.5-pro"]
    def __init__(self, 
                    sliding_window: int = -1,
                    fill_len: int = 7,
                    system_prompt: str = "",
                    model: str = "gemini-1.5-flash", # "flash" or "pro"
                    ):
        super().__init__(sliding_window, fill_len, system_prompt)
        self.model = model
        
    def get_message(self,text, suffix: str = ''):
        message = []
        default_user_prompt = "给我写一段小说"
        message.append({"role": "user", "parts": [default_user_prompt]}) 

        # we looks for each user prompt enclosed with "<user>" and "</user>" in a loop
        # then, we iteratively add the user prompt to the message
        # we also add everything in between the user prompts as model response
        unprocessed_text = text
        while True:
            user_prompt_start = unprocessed_text.find("<user>")
            user_prompt_end = unprocessed_text.find("</user>")
            if user_prompt_start != -1:
                if user_prompt_end != -1:
                    user_prompt = unprocessed_text[user_prompt_start+len("<user>"):user_prompt_end]
                    model_completion = unprocessed_text[:user_prompt_start]
                    message.append({"role": "model", "parts": [model_completion]})
                    message.append({"role": "user", "parts": [user_prompt]})
                    unprocessed_text = unprocessed_text[user_prompt_end+len("</user>"):]
                else: # unclosed user prompt. we ask model to complete the prompt
                    message.append({"role": "model", "parts": [unprocessed_text[:user_prompt_start]]})
                    
                    unprocessed_text = unprocessed_text[user_prompt_start+len("<user>"):]
                    # complete_prompt_prompt = '帮助用户编辑下一条prompt，根据已有的prompt补全。'
                    complete_prompt_prompt = 'User has an unfinished prompt. Please help complete the prompt based on the existing prompt.'
                    
                    prompt = f'{complete_prompt_prompt}\nUser: {unprocessed_text}'

                    last_paragraph_index = unprocessed_text.rfind("\n")
                    # last_paragraph_index = max(unprocessed_text.rfind("\n"), unprocessed_text.rfind("。"))
                    # start from the last ",", "，" ".", "?", '？', '\n', "。"
                    # last_paragraph_index = max(
                        # unprocessed_text[:-4].rfind(","), 
                        # unprocessed_text[:-4].rfind("，"),
                    #     unprocessed_text[:-4].rfind("."), 
                        # unprocessed_text[:-4].rfind("?"),
                        # unprocessed_text[:-4].rfind("？"),
                        # unprocessed_text[:-4].rfind("\n"),
                        # unprocessed_text[:-4].rfind("。")
                    # )+1
                    # prompt += f'\n从这里开始补全，不要重复前面：{unprocessed_text[last_paragraph_index:]}'
                    prompt += f'\nStart from here, and do not repeat the previous content: {unprocessed_text[last_paragraph_index:]}'
                    message.append({"role": "user", "parts": [prompt]})
                    # message.append({"role": "user", "parts": [complete_prompt_prompt]})
                    # message.append({"role": "model", "parts": [unprocessed_text]})

                    return message, len(unprocessed_text) - last_paragraph_index
                
            else:
                break
        message.append({"role": "model", "parts": [unprocessed_text]})
        """
        # message.append({"role": "model", "parts": [text]})
        # last_paragraph_index = text.rfind("\n")
        last_paragraph_index = max(
            # unprocessed_text.rfind(","), 
            # unprocessed_text.rfind("，"),
            unprocessed_text.rfind("."), 
            unprocessed_text.rfind("?"),
            unprocessed_text.rfind("？"),
            unprocessed_text.rfind("\n"),
            unprocessed_text.rfind("。")
        )

        if last_paragraph_index != -1:
            # continuation_prompt = "继续，从这行开始：" 
            continuation_prompt = "继续，从这行开始，不要重复再之前的内容。"
            continuation_prompt += text[last_paragraph_index:]
        else:
            continuation_prompt = "继续"
        message.append({"role": "user", "parts": [continuation_prompt]})
        """
        last_paragraph_index = text.rfind("\n")
        if last_paragraph_index != -1:
            prefill_len = len(text) - last_paragraph_index
            continuation_prompt = "Continue from this line, do not repeat the previous content nor the chapter title:\n"
            continuation_prompt += text[last_paragraph_index:]
        else:
            prefill_len = 0
            continuation_prompt = "Continue"
        message.append({"role": "user", "parts": [continuation_prompt]})
        return message, prefill_len
    
    def __call__(self, text, suffix: str = '') -> str:
        if self.system_prompt:
            gen_model = genai.GenerativeModel(self.model,
                                            system_instruction=self.system_prompt)
        else:
            gen_model = genai.GenerativeModel(self.model)

        message, prefill_len = self.get_message(text, suffix)
        # prefill_message = message[-1]["parts"][0]
        # prefill_start = prefill_message.rfind("previous content:")
        # if prefill_start != -1:
        #     prefill_message = prefill_message[prefill_start+len("previous content:"):]
        # else:
        #     prefill_message = ""
        print_to_log ("message:"+ str(message))
        response = gen_model.generate_content(message,
                                              safety_settings={'HARASSMENT':'block_none',
                                                   'SEXUALLY_EXPLICIT': 'block_none',
                                                   'HATE_SPEECH': 'block_none',
                                                   'DANGEROUS': 'block_none',},
                                              generation_config=genai.types.GenerationConfig(
                                                    # candidate_count=1,
                                                    # stop_sequences=['x'],
                                                    # max_output_tokens=self.fill_len,
                                                    max_output_tokens=self.fill_len + prefill_len,
                                                    temperature=0.5)
                                              ).text

        
        print_to_log ("max_token: "+ str(self.fill_len+prefill_len))
        print_to_log ("response: "+ response)

        # strip away "User: "
        response = response.replace("User: ", "")

        overlap = check_overlap(text, response)
        print_to_log ("overlap length: "+ str(overlap))
        response = response[overlap:]

        # strip away ...
        if response[:3] == '...':
            response = response[3:]

        import regex

        def correct_spacing(text):
            # Regex pattern to match punctuation or Chinese characters followed by a space
            # but not followed by a newline
            pattern = regex.compile(r'([\p{P}\p{Han}])[ \t](?!\n)')
            # Replace occurrences found by the pattern with the character without the space
            corrected_text = regex.sub(pattern, r'\1', text)
            return corrected_text


        # Assuming the rest of the code is unchanged, apply the correction to the response:
        response = correct_spacing(response)
        
        return response


def get_copilot(model=None, provider=None, sliding_window=-1, fill_len=7, system_prompt = ''):
    """
    returns a copilot object based on the provider
    """
    # create a list of models that are supported by each provider
    
    if model is None:
        model = "Qwen/Qwen2-72B-Instruct"
        provider = "together"
    else:
        if model in TogetherCopilot.supported_models:
            provider = "together"
        elif model in GeminiCopilot.supported_models:
            provider = "gemini"
        else:
            raise ValueError("Model not supported by any provider")

    if provider == "gemini":
        return GeminiCopilot(sliding_window=sliding_window, fill_len=fill_len, system_prompt=system_prompt, model=model)
    if provider == "together":
        return TogetherCopilot(sliding_window=sliding_window, fill_len=fill_len, system_prompt=system_prompt, model=model)
    