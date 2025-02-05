# Writing Copilot

## Introduction

Writing Copilot is a tool for writing fictions. It is designed to help you write stories by providing autocompletion based on the text you have written. 

## Installation

You can install Writing Copilot by running the following command:

```bash
pip install together
pip install -q -U google-generativeai
```

Then, before usage, input your together API key or Gemini API key:

```bash
export TOGETHER_API_KEY=your_together_api_key
export GOOGLE_API_KEY=your_google_api_key
```

## Usage

To use Writing Copilot, you can run the following command:

```bash
python ai_editor.py $file_path --model gemini-1.5-pro-exp-0801 --fill_len 20 --system_prompt 黄文 --sliding_window -1
```

Then, you can start writing your story. Writing Copilot will provide autocompletion based on the text you have written. 

### User Instructions

To input user instructions for plotline, character, setting, etc, you can use the following format in the terminal editor:

```
<user>

plotline: A
character 1: B
...

</user>
```

Note that if the user instructions are not enclosed with '</user>', Writing Copilot will help you generate a prompt. 