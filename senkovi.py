import openai
import sys
import os
import traceback
import subprocess
import json
import difflib
import shutil
from typing import Tuple, List

openai.api_key = os.getenv("OPENAI_API_KEY")


def colored(text: str, color_code: str) -> str:
    return f"{color_code}{text}\033[0m"


def colorize_diff(diff: str) -> str:
    color_map = {
        "+": "\033[32m",
        "-": "\033[31m",
        "@": "\033[34m",
    }
    return "".join(
        colored(line, color_map.get(line[0], "\033[37m")) + "\n"
        for line in diff.splitlines()
    )


def run_code(file_name: str) -> Tuple[str, str]:
    code = ""
    output = ""
    with open(file_name, "r") as f:
        for i, line in enumerate(f.readlines()):
            code += f"{i + 1}: {line}"
    try:
        output = subprocess.check_output(
            ["python3", file_name], stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        output = e.output
        output += "\n" + "".join(
            traceback.format_exception(type(e), e, e.__traceback__)
        )
    return code, output


def send_code(file_name: str, intent: str = None) -> str:
    code, output = run_code(file_name)
    restricted_files = ["senkovi.py", "fabian.py"]
    other_file_codes = []
    for file in os.listdir():
        if (
            not os.path.isdir(file)
            and file != file_path
            and file not in restricted_files
            and "bak" not in file
        ):
            with open(file, "r") as f:
                file_code = (
                    "# "
                    + file
                    + " (this is not in the actual code file, this is for your info ONLY)\n"
                )
                for i, line in enumerate(f.readlines()):
                    file_code += f"{i + 1:4d}: {line}"
                other_file_codes.append(
                    file_code
                    + "# END OF "
                    + file
                    + " (this is not in the actual code file, this is for your info ONLY)\n"
                )

    prompt = f"""You are a brilliant Python programmer that is one of the best in the world 
    at finding and fixing bugs in code. You will be given a program that has bug(s) in it,
    along with the stack traces, and your job is to fix the bug(s) and return your changes
    in a very specific format specified below. {f"The intent of this program is {intent}" if intent else ""}. Please return a JSON object containing the suggested changes in a format \
            similar to the git diff system, showing whether a line is added,
            removed, or edited for each file.
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
    In the 'action' field, use "add" for adding a line, this will put the line \
            after the line number,
    "remove" for removing a line, and "edit" for editing a line.
    Please provide the suggested changes in this format. The code has line numbers \
    prepended to each line in the format "1:print('hello world')", so you can use \
    that to determine the line number on which to make a change. Edits are applied in
    reverse line order so that the line numbers don't change as you edit the code.
    Code of the file that was run:
    {code}
    Output:
    {output}
    You are also provided with the code of the other files in the directory:
    {"".join(other_file_codes)}
    PLAY VERY CLOSE ATTENTION TO INDENTATION AND WHITESPACE, THIS IS PYTHON AFTER ALL! DO NOT DEVIATE FROM THE FORMAT IT MUST BE ABLE TO BE PARSED BY ME! 
    You will be penalized if you do. ONLY RETURN JSON, DON'T EXPLAIN YOURSELF UNLESS IN THE EXPLANATION FIELD.
    DON'T INCLUDE MARKDOWN BACKTICKS OR ANYTHING LIKE THAT, JUST THE JSON.
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
        changes.sort(key=lambda x: x["line_number"], reverse=True)
        for change in changes:
            action = change["action"]
            line_number = change["line_number"] - 1
            new_line = change.get("new_line")
            if action == "edit":
                lines[line_number] = new_line.rstrip() + "\n"
            elif action == "remove":
                del lines[line_number]
            elif action == "add":
                lines.insert(line_number, new_line + "\n")

        with open(file_path, "w") as file:
            file.writelines(lines)
    return [f["file_name"] for f in files_changed]


def fix_code(file_path: str, intent: str = None):
    with open(file_path, "r") as f:
        original_code = f.read()
    for file in os.listdir():
        if file.endswith(".py"):
            shutil.copyfile(file, file + ".bak")
    while True:
        _, output = run_code(file_path)
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
    code, output = run_code(file_path)

    other_file_codes = []
    with open(file_path, "r") as f:
        original_code = f.read()
    restricted_files = ["senkovi.py", "fabian.py"]
    for file in os.listdir():
        if file.endswith(".py"):
            shutil.copyfile(file, "pre_change" + file + ".bak")
        if (
            not os.path.isdir(file)
            and file != file_path
            and file not in restricted_files
            and "bak" not in file
        ):
            with open(file, "r") as f:
                file_code = (
                    "# "
                    + file
                    + " (this is not in the actual code file, this is for your info ONLY)\n"
                )
                for i, line in enumerate(f.readlines()):
                    file_code += f"{i + 1}: {line}"
                other_file_codes.append(
                    file_code
                    + "# END OF "
                    + file
                    + " (this is not in the actual code file, this is for your info ONLY)\n"
                )

    change_prompt = f"""I want you to change the following Python code in a manner I declare with the following intent {intent}.
            The file you're editing is {file_path}.
            Please return a JSON object containing the suggested changes in a format \
            similar to the git diff system, showing whether a line is added,
            removed, or edited for each file.
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
    Please provide the suggested changes in this format. The code has line numbers \
    prepended to each line in the format "1:print('hello world')", so you can use \
    that to determine the line number on which to make a change. Edits are applied in
    reverse line order so that the line numbers don't change as you edit the code.
    Code of the file that was run:
    {code}
    Output:
    {output}
    You are also provided with the code of the other files in the directory:
    {"".join(other_file_codes)}
    PLAY VERY CLOSE ATTENTION TO INDENTATION AND WHITESPACE, THIS IS PYTHON AFTER ALL! DO NOT DEVIATE FROM THE FORMAT IT MUST BE ABLE TO BE PARSED BY ME! 
    You will be penalized if you do. ONLY RETURN JSON, DON'T EXPLAIN YOURSELF UNLESS IN THE EXPLANATION FIELD.
    DON'T INCLUDE MARKDOWN BACKTICKS OR ANYTHING LIKE THAT, JUST THE JSON.
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
        print(
            "Usage: python3 senkovi.py <file_path> <0 if you want to fix code, 1 if you want to change code> <intent, optional if just bugfixing>"
        )
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
            print(
                "Usage: python3 senkovi.py <file_path> <0 if you want to fix code, 1 if you want to change code> <intent, optional if just bugfixing>"
            )
            sys.exit(1)
