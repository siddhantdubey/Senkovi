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
            if module_name not in module_cache:
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
    Original Code:
    {code}
    Output:
    {output}
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
                "original_line": "print(hello world')",
                "new_line": "print('hello world')",
                }}
            ]
        }},
    ]
    
    }}
    In the 'action' field, use "add" for adding a line,
    "remove" for removing a line, and "edit" for editing a line.
    Please provide the suggested changes in this format.
    DO NOT DEVIATE FROM THE FORMAT IT MUST BE ABLE TO BE PARSED BY ME! 
    You will be penalized if you do."""
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

        for change in changes:
            action = change["action"]
            line_number = change["line_number"] - 1
            original_line = change.get("original_line")
            new_line = change.get("new_line")

            if action == "edit" and lines[line_number].strip() == original_line.strip():
                indent = len(lines[line_number]) - len(lines[line_number].lstrip())
                lines[line_number] = " " * indent + new_line + "\n"
            elif action == "remove" and lines[line_number].strip() == original_line.strip():
                del lines[line_number]
            elif action == "add":
                lines.insert(line_number, new_line + "\n")

        with open(file_path, "w") as file:
            file.writelines(lines)
    return [f['file_name'] for f in files_changed]


def main(file_path: str, intent: str = None):
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


if __name__ == "__main__":
    intent = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
    if intent:
        main(sys.argv[1], intent)
    else:
        main(sys.argv[1])
