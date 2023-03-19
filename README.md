# Senkovi.py

## What is it?
Inspired by this [tweet](https://twitter.com/bio_bootloader/status/1636880208304431104?s=20) by bio_bootloader, I wrote a Python script that uses the GPT-4 API to "heal" other pytho scripts. As of now, it catches some basic errors, and in my incredibly limited testing, it fixes them.

## Usage
You just need an OpenAI API Key and GPT-4 access, although this probably could work well enough with GPT-3.5-turbo. I haven't tested that yet.
Then just run it as follows:
`python senkovi.py buggy_program.py`

If you want to pass in the intent of the program, you can do so as follows. Note that this is an optional argument.
`python senkovi.py buggy_program.py "This program is meant to add numbers"`

## Contributions
I would love your contributions. Just make a Pull Request and add what you think might be cool.

## More features
- Pass in a user description of what the script *should* do, and see if GPT can catch and fix more abstract logic errors.
- Passing in a suite of tests and their results so that GPT has more info with which to fix things
- Prettifying the terminal output to show diffs nicely.

## Naming
- Named Senkovi after Disra Senkovi from *Children of Ruin*.
