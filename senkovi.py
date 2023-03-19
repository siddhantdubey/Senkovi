import openai
import sys
import os
import traceback
import runpy
import json
import difflib
from contextlib import redirect_stdout
from io import StringIO
from typing import Tuple

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


def run_code(file_name: str) -> Tuple[str, str]:
    with open(file_name, "r") as f:
        code = f.read()
        
    buffer = StringIO()
    with redirect_stdout(buffer):
        try:
            runpy.run_path(file_name, run_name="__main__")
        except Exception:
            output = buffer.getvalue() + "\n" + "".join(traceback.format_exception(*sys.exc_info()))
        else:
            output = buffer.getvalue()
    return code, output


def send_code(file_name: str) -> str:
    code, output = run_code(file_name)
    prompt = f"""I have a Python program with errors, and I would like you to \
            help me fix the issues in the code.
    The original code and the output, including any error messages and stack \
            traces, are provided below.
    Please return a JSON object containing the suggested changes in a format \
            similar to the git diff system, showing whether a line is added,
            removed, or edited.

    Original Code:
    {code}
    Output:
    {output}
    For example, the JSON output should look like:
    {{
    "intent": "ascertain the original intent of the program",
    "explanation": "Explanation of what went wrong and the changes being made",
    "changes": [
        {{
        "action": "edit",
        "line_number": 2,
        "original_line": "print(hello world')",
        "new_line": "print('hello world')",
        }}
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
                        fixing code.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response["choices"][0]["message"]["content"]


def edit_code(file_path: str, fix: str) -> None:
    while True:
        try:
            changes = json.loads(fix)["changes"]
            break
        except json.JSONDecodeError:
            fix = send_code(file_path)
    
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


def main(file_path: str):
    with open(file_path, "r") as f:
        original_code = f.read()
    print(f"Original Code:\n{original_code}\n")

    while True:
        code, output = run_code(file_path)
        if "Traceback" in output:
            print(f"Output:\n{output}\n")
            print("Fixing code...\n")
            fix = send_code(file_path)
            edit_code(file_path, fix)
            with open(file_path, "r") as f:
                new_code = f.read()
            diff = difflib.unified_diff(
                code.splitlines(keepends=True),
                new_code.splitlines(keepends=True),
                fromfile="original",
                tofile="new",
            )
            diff = colorize_diff("".join(diff))
            print("".join(diff))
        else:
            print(f"Output:\n{output}\n")
            print("Code is syntax error-free!")
            break


if __name__ == "__main__":
    main(sys.argv[1])

