import openai
import sys
import os
import importlib
import traceback
import runpy
import json
import types
import difflib
from contextlib import redirect_stdout
from io import StringIO
from typing import Tuple, List, Dict

openai.api_key = os.getenv("OPENAI_API_KEY")


def colored(text: str, color_code: str) -> str:
    return f"{color_code}{text}\033[0m"


def colorize_diff(diff: str) -> str:
    color_map = {
        "+": "\033[32m",
        "-": "\033[31m",
        "@": "\033[34m",
    }
    return "".join(colored(line, color_map.get(line[0], "\033[37m")) + "\n" for line in diff.splitlines())


def run_code(file_name: str, module_cache: Dict[str, types.ModuleType] = None) -> Tuple[str, str]:
    code = ""
    output = ""
    if module_cache is None:
        module_cache = {}
    with open(file_name, "r") as f:
        code = f.read()
    for file in os.listdir():
        if file.endswith(".py"):
            module_name = file.split(".")[0]
            if module_name not in module_cache and module_name != "__main__" and module_name != "senkovi" and module_name != file_name.split(".")[0]:
                module_cache[module_name] = importlib.import_module(module_name)
    buffer = StringIO()
    with redirect_stdout(buffer):
        for module_name, module in module_cache.items():
            if module_name != "__main__":
                importlib.reload(module)
        try:
            runpy.run_path(file_name, run_name="__main__")
        except Exception as e:
            output += buffer.getvalue()
            output += "\n" + "".join(traceback.format_exception(
                *sys.exc_info()))
    if not output:
        output = buffer.getvalue()
    return code, output


def send_code(file_name: str, intent: str = None) -> str:
    code, output = run_code(file_name)

    prompt = f"""I have a Python program with errors, and I would like you to \
            help me fix the issues in the code.
    The original code of the program run ({file_name}) and the output, including any error messages and stack \
            traces, are provided below.

    Please return a JSON object containing the suggested changes in a format \
            similar to the git diff system, showing whether a line is added,
            removed, or edited for each file.
    {"Intent: " + intent if intent else ""}
    
    For example, the JSON output should look like:
    {{
    "intent": "This should be what you think the program SHOULD do.",
    "explanation": "Explanation of what went wrong and the changes being made",
    "files": [
        {{
            "file_name": "file_name.py",
            "changes": [
                {{
                "action": "edit",
                "line_number": 2,
                "new_line": "print('hello world')",
                }},
                {{
                "action": "add",
                "line_number": 3,
                "new_line": "hello="world"\nprint(hello)\nprint(1 + 2)",
                }},
                {{
                "action": "remove",
                "line_number": 4,
                "new_line": "",
                }},
            ]
        }},
    ]

    }}
    In the 'action' field, use "add" for adding a line, thisl will put the line \
            after the line number,
    "remove" for removing a line, and "edit" for editing a line.
    Please provide the suggested changes in this format.
    PLAY VERY CLOSE ATTENTION TO INDENTATION AND WHITESPACE.
    You should only have ONE add per file, the add should be at the end of the file and contain all lines you are adding separated with newline characters.
    DO NOT DEVIATE FROM THE FORMAT IT MUST BE ABLE TO BE PARSED BY ME! 
    You will be penalized if you do.
    Original Code:
    {code}
    Output:
    {output}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that is great at \
                        fixing code and not breaking it.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=1.0,
    )
    return response["choices"][0]["message"]["content"]


def edit_code(run_file: str, fix: str, intent: str = None) -> List[str]:
    """Returns a list of the files that were changed"""
    while True:
        try:
            files_changed = json.loads(fix)["files"]
            break
        except json.JSONDecodeError:
            print(f"Old fix: {fix} was not validly formatted. Trying again...")
            fix = send_code(run_file, intent)

    for f in files_changed:
        file_path = f["file_name"]
        changes = f["changes"]
        with open(file_path, "r") as file:
            lines = file.readlines()
        print(type(changes))
        print(changes)
        changes.sort(key=lambda x: x["line_number"], reverse=True)
        print(changes)
        for change in changes:
            action = change["action"]
            line_number = change["line_number"] - 1
            new_line = change.get("new_line")
            if action == "edit":
                lines[line_number] = new_line.rstrip() + "\n"
            elif action == "remove":
                del lines[line_number]
            elif action == "add":
                lines.insert(line_number + 1, new_line + "\n")

        with open(file_path, "w") as file:
            file.writelines(lines)
    return [f['file_name'] for f in files_changed]


def fix_code(file_path: str, intent: str = None):
    module_cache = {}

    with open(file_path, "r") as f:
        original_code = f.read()
    print(f"Original Code:\n{original_code}\n")

    while True:
        code, output = run_code(file_path, module_cache)   
        original_files = {}
        for file in os.listdir():
            if file.endswith(".py"):
                original_files[file] = open(file, "r").read()
        if "Traceback" in output:
            print(f"Output:\n{output}\n")
            print("Fixing code...\n")
            fix = send_code(file_path, intent)
            print(f"Fix:\n{fix}\n")
            files_changed = edit_code(file_path, fix, intent)
            for code_file in files_changed:
                with open(code_file, "r") as f:
                    new_code = f.read()
                diff = difflib.unified_diff(
                    original_files[code_file].splitlines(keepends=True),
                    new_code.splitlines(keepends=True),
                    fromfile="original",
                    tofile="new",
                )
                diff = colorize_diff("".join(diff))
                print(f"\033[33m{code_file}\033[0m")
                print("".join(diff))
        else:
            print(f"Output:\n{output}\n")
            print("Code is syntax error-free!")
            break

def change_code(file_path: str, intent: str = None):
    """ 
    This changes the code according to the intent provided by the user.
    It then calls fix_code to fix the code if there are any bugs.
    """
    module_cache = {}
    code, output = run_code(file_path)

    with open(file_path, "r") as f:
        original_code = f.read()
    
    print(f"Original Code:\n{original_code}\n")

    change_prompt = f"""I want you to change the following Python code in a manner I declare with the following intent {intent}.
            The file you're editing is {file_path}.
            Please return a JSON object containing the suggested changes in a format \
            similar to the git diff system, showing whether a line is added,
            removed, or edited for each file.
            You should only have ONE add per file, the add should be at the end of the file and contain all lines you are adding separated with newline characters.
            BE JUDICIOUS WITH YOUR CHANGES, DON'T TOUCH LINES THAT DON'T NEED TO BE TOUCHED.
    {"Intent: " + intent if intent else ""}

    For example, the JSON output should look like:
    {{
    "intent": "This should be what you the user wants the code to do.",
    "explanation": "Explanation of your plan to change the code.",
    "files": [
        {{
            "file_name": "file_name.py",
            "changes": [
                {{
                "action": "edit",
                "line_number": 2,
                "new_line": "print('hello world')",
                }},
                {{
                "action": "add",
                "line_number": 3,
                "new_line": "hello="world"\nprint(hello)\nprint(1 + 2)",
                }},
                {{
                "action": "remove",
                "line_number": 4,
                "new_line": "",
                }},
            ]
        }},
    ]

    }}
    In the 'action' field, use "add" for adding a line,
    "remove" for removing a line, and "edit" for editing a line.
    Please provide the suggested changes in this format.
    PLAY VERY CLOSE ATTENTION TO INDENTATION AND WHITESPACE, THIS IS PYTHON AFTER ALL!
    DO NOT DEVIATE FROM THE FORMAT IT MUST BE ABLE TO BE PARSED BY ME! 
    You will be penalized if you do.
    Original Code:
    {code}
    Output:
    {output}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that is brilliant at writing Python code.",
            },
            {"role": "user", "content": change_prompt},
        ],
        temperature=1.0,
    )

    fix = response["choices"][0]["message"]["content"]
    print(f"Fix:\n{fix}\n")
    files_changed = edit_code(file_path, fix, intent)
    for code_file in files_changed:
        with open(code_file, "r") as f:
            new_code = f.read()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            fromfile="original",
            tofile="new",
        )
        diff = colorize_diff("".join(diff))
        print(f"\033[33m{code_file}\033[0m")
        print("".join(diff))
    fix_code(file_path, intent)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 senkovi.py <file_path> <0 if you want to fix code, 1 if you want to change code> <intent, optional if just bugfixing>")
        sys.exit(1)
    file_path = sys.argv[1]
    if len(sys.argv) > 2:
        if sys.argv[2] == "0":
            fix_code(file_path)
        elif sys.argv[2] == "1":
            if len(sys.argv) > 3:
                intent = sys.argv[3]
                change_code(file_path, intent)
            else:
                print("YOU MUST PROVIDE AN INTENT IF YOU WANT TO CHANGE CODE!")
                sys.exit(1)
        else:
            print("Usage: python3 senkovi.py <file_path> <0 if you want to fix code, 1 if you want to change code> <intent, optional if just bugfixing>")
            sys.exit(1)