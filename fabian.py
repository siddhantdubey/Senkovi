import openai
import sys
import os
from typing import List

from senkovi import fix_code

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_program(prompt: str) -> List[str]:
    detailed_prompt = "I want you to write a Python program with"
    detailed_prompt += f" the following specification: {prompt} \n"
    detailed_prompt += open("fabian_prompt.txt", "r").read()
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that is a brilliant Python programmer."},
            {"role": "user", "content": detailed_prompt},
        ]
    )
    completion = response["choices"][0]["message"]["content"]
    lines = completion.split("\n")
    lines = [line for line in lines if line.strip() not in [
        "```python", "```"]]
    return lines


def write_program(completion: List[str], filename: str = None) -> str:
    if not filename:
        filename = "generated_program.py"
    program_code = "\n".join(completion)
    with open(filename, "w+") as f:
        f.write(program_code)
    return filename


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fabian.py <prompt>")
        sys.exit(1)
    prompt = sys.argv[1]
    if len(sys.argv) == 3:
        filename = sys.argv[2]
    else:
        filename = None
    program = generate_program(prompt)
    filename = write_program(program, filename)
    print(f"\033[94mProgram written to {filename}!\033[0m")
    fix_code(filename, prompt)


if __name__ == "__main__":
    main()
