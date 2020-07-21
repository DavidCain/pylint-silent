"""Add "# pylint: disable" comments to silence the output of pylint.

Usage: pylint-silent apply <pylint-output-file>
            Add pylint comments based on the output of pylint.
       pylint-silent reset <python-file> ...
            Remove pylint comments from specified python files.
       pylint-silent stats <python-file> ...
            Report statistics on number of pylint comments in specified files.
       pylint-silent --version
            Show the version and exit.

WARNING: Python files are modified in place.
         It is assumed that you are using some version control system.
"""
import os
from typing import Dict, List, Set
# from pylint_silent.version import __version__
import pylint_silent.version
__version__ = pylint_silent.version.__version__

EOL = "\n"
TEMP_FILE_ENDING = ".created_by_pylint_silent"


def pyfile_add_comments(py_filename: str, messages: Dict[int, Set[str]]) -> None:
    """Add comments to a python file to silent 'messages'."""
    out_filename = py_filename + TEMP_FILE_ENDING

    with open(py_filename, "r") as py_file, \
         open(out_filename, "w") as out_file:

        for line_no, line in enumerate(py_file):
            pylint_line_no = line_no + 1
            if pylint_line_no in messages:
                # Sort messages alphabetically for reproducible output.
                sorted_messages = sorted(messages[pylint_line_no])
                line = (
                    f"{line.rstrip()}"
                    f"  # pylint: disable={','.join(sorted_messages)}{EOL}"
                )
            out_file.write(line)

    os.rename(out_filename, py_filename)


def apply(pylint_logfile: str) -> None:
    """Process the output of pylint add disable comments for all messages."""
    active_py_filename = None
    messages: Dict[int, Set[str]] = {}

    with open(pylint_logfile, "r") as logfile:

        for line in logfile:
            # 'line' should look like this:
            # "test.py:35:10: W0613: Unused argument 'name' (unused-argument)"
            line_parts = line.split(":", maxsplit=4)

            if len(line_parts) != 5:
                # Ignore lines with a different format.
                continue

            py_filename = line_parts[0]
            line_no = int(line_parts[1])
            # line_pos = line_parts[2]
            code = line_parts[3]
            message = line_parts[4]

            if code in (
                    " R0401",  # Cyclic import
                    " R0801",  # Similar lines in 2 files
            ):
                # Pylint reports the wrong file and line number for these messages.
                continue
            if code == " C0326":
                # For C0326 the message symbol is shown on the next line.
                message_symbol = "bad-whitespace"
            else:
                if message.find("(") < 0:
                    print("Message missing message symbol:", message)
                    continue
                message_symbol = message[message.rfind("(") + 1:message.rfind(")")]

            if py_filename != active_py_filename:
                # New file. Finish processing previous file.
                if active_py_filename is not None:
                    pyfile_add_comments(active_py_filename, messages)
                active_py_filename = py_filename
                messages = {}

            if line_no in messages:
                messages[line_no].add(message_symbol)
            else:
                # First message for this line_no
                messages[line_no] = set([message_symbol])

        # Handle last file.
        if active_py_filename is not None:
            pyfile_add_comments(active_py_filename, messages)


def reset(py_filename: str) -> None:
    """Remove all pylint comments from a python file."""
    out_filename = py_filename + TEMP_FILE_ENDING
    something_changed = False

    with open(py_filename, "r") as py_file, \
         open(out_filename, "w") as out_file:

        for line in py_file:
            comment_pos = line.find("# pylint: disable=")
            # Do not remove comments starting at beginning of line
            if comment_pos > 0:
                line = line[:comment_pos].rstrip() + EOL
                something_changed = True
            out_file.write(line)

    if something_changed:
        os.rename(out_filename, py_filename)
    else:
        os.remove(out_filename)


def statistics(py_filenames: List[str]) -> None:
    """Show statistics on pylint comments from a list of python files."""
    stats: Dict[str, int] = {}

    for py_filename in py_filenames:

        with open(py_filename, "r") as py_file:

            for line in py_file:
                comment_pos = line.find("# pylint: disable=")
                # Ignore comments starting at beginning of line
                if comment_pos >= 0:
                    comment = line[comment_pos:].rstrip()
                    # 'comment' may disable sevral messages:
                    # "# pylint: disable=too-many-branches,too-many-statements"
                    messages = comment[comment.find("=") + 1:].split(",")
                    for message in messages:
                        if message in stats:
                            stats[message] += 1
                        else:
                            stats[message] = 1

    for message in sorted(stats):
        print(f"{message}: {stats[message]}")

    print("TOTAL:", sum(stats.values()))
