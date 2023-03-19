import openai
import sys
import os
from typing import List

from senkovi import fix_code

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_program(prompt: str) -> List[str]:
    detailed_prompt = f""""
    I want you to write a Python program with the following specification: {prompt}.
    Do not output anything but a valid Python script. The very first line in the program should be a single-line comment with the name of the file like this '# filename.py'
    If you need to think through things before writing the code, include a multiline comment at the top of the script.
    You can also include comments as you see fit in the code, but everything should be valid Python.
    DO NOT OUTPUT ANYTHING BUT PYTHON CODE!! DO NOT EXPLAIN YOURSELF UNLESS IT IS IN COMMENTS IN THE CODE, YOUR COMMENTS SHOULD ONLY RELATE TO THE CODE ITSELF.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that is a brilliant Python programmer."},
            {"role": "user", "content": detailed_prompt},
        ]
    )
    completion = response["choices"][0]["message"]["content"]
    lines = completion.split("\n")
    lines = [line for line in lines if line.strip() not in ["```python", "```"]]
    return lines


def write_program(completion: List[str]) -> str:
    filename_line = completion.pop(0)
    filename = filename_line.strip().strip("# ").strip()
    program_code = "\n".join(completion)
    with open(filename, "w+") as f:
        f.write(program_code)
    return filename

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fabian.py <prompt>")
        sys.exit(1)
    prompt = sys.argv[1]
    program = generate_program(prompt)
    filename = write_program(program)
    print(f"\033[94mProgram written to {filename}!\033[0m")
    fix_code(filename, prompt)

if __name__ == "__main__":
    main()
