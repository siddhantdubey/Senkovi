# Senkov

## What is it?
Inspired by this [tweet](https://twitter.com/bio_bootloader/status/1636880208304431104?s=20) by bio_bootloader, I wrote a Python script that uses the GPT-4 API to "heal" other pytho scripts. As of now, it catches some basic errors, and in my incredibly limited testing, it fixes them. It now also can write a small program with a prompt passed in and then iteratively heal that program until it works.

## Usage
You just need an OpenAI API Key in your env and GPT-4 access, although this probably could work well enough with GPT-3.5-turbo. I haven't tested that yet.
Then just run it as follows:

`python senkovi.py buggy_program.py 0 "optional instructions"` if you want to fix bugs. This works pretty decently.

`python senkovi.py buggy_program.py 1 "edits you want made to the code"` if you want to add a feature or change a feature in the code. I haven't tested this much.

To write a program from scratch, use fabian.py.

`python fabian.py "A python script to plot a quadratic equation and save it to an image"`

Notice that you do not actually provide a filename, this is probably an oversight, but fabian.py comes up with the filename itself.
Running fabian.py will run the program fabian writes as well, be careful! Also, I've found that it has a really hard time with indentation
so if you pass in a reminder in the instructions you'll probably end up with better results! 

## Limitations and Dangers
- 8k context length for GPT-4 api limits the size of the programs and projects that can be constructed.
- `senkovi.py` does not catch logic errors unless they crash the program
- `fabian.py` has all the problems `senkovi.py` does, although it seems to write programs correctly on the first try
- You're letting code you didn't write execute on your machine if you run this locally. This could potentially brick your computer.
- It is really slow. Hopefully speed picks up as OpenAI improves their infra for GPT-4.

## Contributions
I would love your contributions. Just make a Pull Request and add what you think might be cool.

## To-do
- [x] Pass in a user description of what the script *should* do, to give Senkovi more info to work with
- [x] Prettifying the terminal output to show diffs nicely.
- [x] A script to write a program from scratch
- [ ] Catch logic errors, not just errors that crash the program
- [ ] "Safe mode" where the user has to approve the code before it is run
- [ ] More interactivity where the user can guide the repairs to the code?
- [ ] Better TUI

## Naming
- `senkovi.py` named Senkovi after Disra Senkovi from *Children of Ruin*.
- `fabian.py` named Fabian after some of the spiders from *Children of Time*.
