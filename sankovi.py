import openai
import sys
import os
import traceback
import runpy
import json
from contextlib import redirect_stdout
from io import StringIO
from typing import Tuple

openai.api_key = os.getenv("OPENAI_API_KEY")


def run_code(file_name: str) -> Tuple[str, str]:
    code = ""
    output = ""
    with open(file_name, "r") as f:
        code = f.read()
    buffer = StringIO()
    with redirect_stdout(buffer):
        try:
            runpy.run_path(file_name, run_name="__main__")
        except Exception as e:
            output += buffer.getvalue()
            output += "\n" + "".join(traceback.format_exception(
                *sys.exc_info()))
    if not output:
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
    Please provide the suggested changes in this format."""
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
    changes = json.loads(fix)["changes"]

    with open(file_path, "r") as file:
        lines = file.readlines()

    for change in changes:
        action = change["action"]
        line_number = change["line_number"] - 1  # Adjust for 0-based indexing
        original_line = change.get("original_line")
        new_line = change.get("new_line")

        if action == "edit":
            if lines[line_number].strip() == original_line.strip():
                lines[line_number] = new_line + "\n"
        elif action == "remove":
            if lines[line_number].strip() == original_line.strip():
                del lines[line_number]
        elif action == "add":
            lines.insert(line_number, new_line + "\n")

    with open(file_path, "w") as file:
        file.writelines(lines)

    print("Code has been fixed. Please run the code again.")


if __name__ == "__main__":
    while True:
        code, output = run_code(sys.argv[1])
        print(f"Code:\n{code}\n")
        if "Traceback" in output:
            print(f"Output:\n{output}\n")
            print("Fixing code...\n")
            fix = send_code(sys.argv[1])
            edit_code(sys.argv[1], fix)
        else:
            print(f"Output:\n{output}\n")
            print("Code is syntax error-free!")
            break
