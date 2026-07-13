# Makefiles and Symlinks, Explained

A plain-language walkthrough of the two concepts from the `transcribe`
wrapper fix, using the actual files in `audio-transcription-pipeline` as
the example rather than generic tutorial code. Written for someone who
codes in R and is comfortable with scripts, functions, and file paths, but
hasn't spent time in Unix build tooling.

---

## The problem both tools solve

Before this fix, there were two copies of the same script:

- `transcribe.sh` — the real, editable file, tracked in the repo.
- `~/bin/transcribe` — a separate copy, installed once, actually invoked
  every time you typed `transcribe meeting.m4a`.

Editing `transcribe.sh` did nothing to `~/bin/transcribe`. You had to
remember to run `cp transcribe.sh ~/bin/transcribe` again after every
edit — and forgetting was exactly what caused the drift you ran into
earlier this session (the installed copy was missing a feature that had
already been added to the repo version).

A symlink removes the *need* to re-copy. A Makefile removes the need to
*remember the command* for the setup step that remains. They solve
different halves of the same problem.

---

## Symlinks

### What it actually is

A symlink (symbolic link) is not a copy of a file. It's a small pointer
that says "the real content is somewhere else." When any program —
`bash`, `transcribe`, anything — opens a symlink, the operating system
transparently redirects it to the real file. The program never notices
the difference.

The closest everyday analogy is a Mac Finder alias or a Windows shortcut,
except a symlink works at a lower level: every program treats it exactly
like the real file, not just Finder/Explorer.

### Copy vs. symlink

| | Copy (`cp`) | Symlink (`ln -s`) |
|---|---|---|
| How many real files exist | Two, independent | One — the link is just a pointer |
| Edit the source | Copy doesn't change (drift) | Link sees the edit immediately |
| If the source is deleted/moved | Copy still works, silently stale | Link breaks — loud, obvious error |

The "silently stale" row is what bit you. The "loud, obvious error" row is
the tradeoff: if you ever move this repo to a different folder, `transcribe`
would stop working with a clear "no such file" error, rather than quietly
running old code. That's a safer failure mode, not a free lunch.

### The actual command

The Makefile runs this on your behalf:

```bash
ln -s "/full/path/to/audio-transcription-pipeline/transcribe.sh" ~/bin/transcribe
```

`ln` is the "link" command. `-s` means "make it symbolic" (there's also a
"hard link," a different, lower-level mechanism you don't need here — it
came up once in a session note as an unrelated file-count oddity, not
something this project uses deliberately). The order matters and is a
common source of mistakes: **real file first, link location second** — get
it backwards and you'd overwrite the wrong thing.

This is exactly the command the Makefile exists to save you from typing
by hand.

---

## Makefiles

### What `make` is

`make` is a decades-old Unix tool for running named, repeatable command
sequences. It predates almost every modern build tool and is installed by
default on macOS and Linux (part of Xcode's command-line tools on Mac,
part of `build-essential` on Ubuntu). You're not installing new,
unfamiliar software — you already have it.

### The R analogy

Think of a `Makefile` as a file full of tiny functions, each with a name,
that you call from the terminal instead of from R. Where you'd write:

```r
install <- function() {
  ...several lines...
}
install()
```

a Makefile lets you type `make install` and have it run the equivalent
"function body" — without you needing to remember what's inside it.
That's the whole value: **one memorized word, instead of a multi-line
command with paths that are easy to get wrong.**

### The actual file

This project's `Makefile` (new, at the repo root) is:

```makefile
.PHONY: install

install:
	mkdir -p ~/bin
	ln -sf "$(CURDIR)/transcribe.sh" ~/bin/transcribe
	chmod +x transcribe.sh
```

Line by line:

- **`.PHONY: install`** — tells `make` that `install` is a command name,
  not a file it should look for on disk. (Without this, if a file
  literally named `install` ever appeared in the folder, `make` would get
  confused about whether there's anything to do.)
- **`install:`** — the target name. This is the word you type after
  `make`. A Makefile can define several targets; this one only has one.
- **The three indented lines** — the recipe: the actual shell commands
  that run, in order, when you type `make install`. These lines *must* be
  indented with a literal tab character, not spaces — one of `make`'s few
  genuine annoyances, and the most common reason a Makefile mysteriously
  fails for a first-time editor.
- **`$(CURDIR)`** — a built-in variable that always resolves to the
  absolute path of the folder containing the Makefile. This is what lets
  you run `make install` from inside the repo without ever typing out
  `/Users/cjtinant/PROJECTS/audio-transcription-pipeline/transcribe.sh`
  by hand — `make` computes it for you, so there's no path to get wrong.
- **`-f` in `ln -sf`** — makes the command safe to re-run. If the symlink
  already exists (e.g. you're reinstalling on a new machine), it's
  replaced cleanly instead of throwing an error.

### How you run it

From inside the repo folder:

```bash
make install
```

That's the entire day-to-day (and really, one-time) interaction. No
paths, no `cp`, no remembering argument order.

---

## Why both, together

- The **symlink** is what makes ongoing edits maintenance-free — there is
  structurally no "forgot to sync" state anymore, because there's only
  one real file.
- The **Makefile** is what makes the *one-time* setup command safe to
  forget the syntax of — you only ever need to remember `make install`,
  never the `ln -s` invocation underneath it.

Neither one alone fully solved the friction you described (step count
*and* what to type in sequence). Together, they do.

---

## Small glossary, for reference

- **Target** — the name you type after `make` (here, `install`).
- **Recipe** — the indented shell commands that run for a given target.
- **Symlink / symbolic link** — a filesystem pointer to another file;
  transparent to any program that opens it.
- **Hard link** — a different, lower-level way two filenames can point at
  the same underlying data; not used deliberately in this project.
- **`PATH`** — the list of folders your shell searches when you type a
  command name; `~/bin` has to be on it for typing `transcribe` (instead
  of the full file path) to work at all.
- **Shell** — the program interpreting your typed commands (`bash` or
  `zsh` on your Mac); distinct from Positron/Terminal.app, which are just
  windows that host a shell.
