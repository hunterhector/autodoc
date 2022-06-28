# code_block.py
#
# This script analyzes the source files with some markers to find
#  the line numbers of the code blocks, and then uses markdown-autodoc
#  to generate markdown files with the code blocks. One difference
#  from using markdown-autodoc directly is that one don't have to
#  hardcode the line numbers so can somehow feel free to modify the
#  source code.
#
# Usage: python code_block.py [markdown input] [source code]
#
# The output directory will be the directory with "_out" appending to
# the input directory
#
# 1. Find comments from the source files, find the markers and write
#   out a mapping from the makrers to their path and line numbers.
# 2. Make a copy of the README files and replace the README side marker
#   with the path and line numbers.
#
# Requires:
#  - `comment_parser`
#
# Assumptions:
#  - The source files should have correct extension so that the MIME
#     types can be determined.
#  - Have https://github.com/karolswdev/autodocs-markdown-docker docker
#     ready.
#  - Markdown output directory need to be in the same level/structure of the
#     input (i.e. from ./input/ to ./output/, not ./input/ to ./some/output/)
#  - Rely on certain string pattern to do the replacement (such as `&`).
#  - Comment tags should be simple ascii names (no special characters).
#  - Comment tags cannot be nested.

import os
import shutil
import sys
import re
import logging
import mimetypes
from typing import Dict, Iterator, List, Tuple

from comment_parser import parsers
from comment_parser import comment_parser as cp
from comment_parser.comment_parser import UnsupportedError


COMMENT_MARKER_BEGIN = "SOURCE_MARKER_BEGIN"
COMMENT_MARKER_END = "SOURCE_MARKER_END"
COMMENT_AUTODOC_BEGIN_PATTERN = (
    "<!-- MARKDOWN-AUTO-DOCS:START \(CODE:src=(.*?)&label=(\w+).*?\) -->"
)

# Setting up MIME type.
cp.MIME_MAP.update({"application/x-sh": parsers.shell_parser})


def list_files(some_path: str) -> Iterator[str]:
    for dirpath, dnames, fnames in os.walk(some_path):
        for f in fnames:
            yield os.path.join(dirpath, f)


def scan_sources(source_dirs: List[str], strip_empty_line: bool) -> Dict[str, str]:
    """
        Given a list of paths, find all text files under it and search for
        all the markers in the comments. Then return these mapping from
        markers to the path and line numbers that these markders enclose.

        The markers are stored in consts $COMMENT_MARKER_BEGIN and
        $COMMENT_MARKER_END from the comments.

        Note:
            - Cannot handle nested markers.
            - Support limited MIME types from https://github.com/jeanralphaviles/comment_parser
            - Use # style inline comments for all other file types now. 

        .. code-block:: python
            import sys

            # SOURCE_MARKER_START_some_name
            print("Testing 1")
            print("Testing 2")
            # SOURCE_MARKER_END_some_name

            # SOURCE_MARKER_START_another_name
            print("Testing 3")
            print("Testing 4")
            print("Testing 5")
            # SOURCE_MARKER_END_another_name


        The mapping would look like:

        .. code-block:: python
            {
                "some_name": "path/to/source&3-4"
                "another_name": "path/to/source&8-10"
            }

    Args:
        path (List[str]): List of file paths to scan.
        strip_empty_line (bool): strip the empty lines at the start and end of the block.

    Returns:
        The mapping from the marker name to the locations.
    """
    marker_mapping = {}

    def take_block(
        text_file: str, start_lineno: int, end_lineno: int, strip_empty: bool
    ):
        empty_begins, empty_ends = 0, 0

        if strip_empty:
            with open(text_file, encoding="utf-8") as f:
                all_lines = f.readlines()[start_lineno:end_lineno]

                for l in all_lines:
                    if l.strip() == "":
                        empty_begins += 1
                    else:
                        break

                for l in reversed(all_lines):
                    if l.strip() == "":
                        empty_ends += 1
                    else:
                        break

        return start_lineno + empty_begins, end_lineno - 1 - empty_ends

    for src_dir in source_dirs:
        for fn in list_files(src_dir):
            mime_type, _ = mimetypes.guess_type(fn)

            if mime_type is None:
                # Just try to use regular shell style comment
                mime_type = "text/x-shellscript"

            try:
                block_name = ""
                lineno = -1
                for comment in cp.extract_comments(fn, mime_type):
                    ctext = comment.text().strip()
                    if ctext.startswith(COMMENT_MARKER_BEGIN):
                        block_name = re.sub("^" + COMMENT_MARKER_BEGIN + "_", "", ctext)
                        lineno = comment.line_number()

                    if ctext.startswith(COMMENT_MARKER_END):
                        block_name_end = re.sub(
                            "^" + COMMENT_MARKER_END + "_", "", ctext
                        )
                        if block_name_end == block_name:
                            block_begin, block_end = take_block(
                                fn, lineno, comment.line_number(), strip_empty_line,
                            )

                            if block_end <= block_begin:
                                raise RuntimeError("Incorrect code block line numbers.")

                            fullpath = os.path.abspath(fn)

                            if fullpath not in marker_mapping:
                                marker_mapping[fullpath] = {}

                            marker_mapping[fullpath][
                                block_name
                            ] = f"lines={block_begin}-{block_end}"
                        else:
                            raise RuntimeError(
                                "Unbalanced comment markers, scanning %s, "
                                "found marker name [%s] at line %d, and [%s] at line %d."
                                % (
                                    fn,
                                    block_name,
                                    0,
                                    block_name_end,
                                    comment.line_number(),
                                )
                            )
                logging.info("Parsing file %s of type %s", fn, mime_type)
            except UnicodeDecodeError:
                logging.info("Ignoring non-text file %s", fn)
            except UnsupportedError:
                logging.info("Ignoring Unsupported file %s of type %s", fn, mime_type)

    return marker_mapping


def run_autodoc(markdown_path: str):
    """Run autodoc on the input file.

    Args:
        markdown_path (str): The input markdown path.
    """
    script = (
        f"docker run -v $(pwd):/data -it karolswdev/autodocs-markdown-docker"
        + f" -c code-block -o {markdown_path}"
    )
    logging.info(f"Running Auto Doc command:")
    logging.info(script)
    status = os.system(script)

    if not status == 0:
        raise RuntimeError(f"Command run unsuccessful, return status is {status}")


def prepare_markdown(
    markdown_path: str, copy_path: str, marker_dict: Dict[str, str]
) -> bool:
    """Given a markdown file, make a copy that replace the markers with the locations.

    In the copied file, the following replacement will happen:
    The string `<!-- MARKDOWN-AUTO-DOCS:START (CODE:src=path/to/source&some_name) -->`
    will be replaced to the following given the mapping: `"some_name": "path/to/source&3-4"`
    `<!-- MARKDOWN-AUTO-DOCS:START (CODE:src=path/to/source&3-4) -->`

    Args:
        markdown_path (str): The path to the input markdown file.
        copy_path (str): The path to copy the markdown to.
        markder_dict (Dict[str, str]): A mapping from the marker to the locations.

    Returns:
        A boolean value representing whether something is replaced.
    """
    is_replaced = False

    with open(markdown_path, encoding="utf-8") as f, open(
        copy_path, "w", encoding="utf-8"
    ) as out:
        for line in f:
            matched = re.match(COMMENT_AUTODOC_BEGIN_PATTERN, line.strip())
            if matched:
                if len(matched.groups()) > 2:
                    raise RuntimeError(
                        f"Should not have more than 2 matched groups in AUTODOC pattern at {f}"
                    )

                src_path_in_markdown, marker_label = matched.groups()

                src_path = os.path.join(
                    os.path.dirname(markdown_path), src_path_in_markdown
                )
                full_src_path = os.path.abspath(src_path)

                if full_src_path in marker_dict:
                    replace_label = marker_dict[full_src_path][marker_label]
                else:
                    raise RuntimeError(
                        f"Tag [{marker_label}] in a source file {full_src_path} "
                        f"cannot be found in the markdown file [{markdown_path}]."
                    )
                is_replaced = True
                out.write(line.replace("&label=" + marker_label, "&" + replace_label))
            else:
                out.write(line)

    if is_replaced:
        run_autodoc(copy_path)

    return is_replaced


def prepare_all_markdowns(
    markdown_dir: str, target_dir: str, marker_dict: Dict[str, str]
) -> Tuple[List[str], List[str], List[str]]:
    """Given a directory containing markdown files, replace the markdown content and copy
    them to the `target_dir`, trying to keep the same directory structure.

    Note:
        - Find markdown files using the ".md" extension.

    Args:
        markdown_dir (str): input markdown directory.
        target_dir (str): output directory.
        marker_dict (Dict[str, str]): A mapping from the marker to the locations.

    Returns:
        Three list of items:
          - The first one contains markdown files that are auto-replaced.
          - The second one contains other markdown files that are copied.
          - The third one contains other files (non-markdown) that are copied.
    """
    summary = [], [], []
    for dirpath, _, fnames in os.walk(markdown_dir):
        structure = os.path.join(target_dir, os.path.relpath(dirpath, markdown_dir))
        if not os.path.isdir(structure):
            os.makedirs(structure)

        for fname in fnames:
            src_file = os.path.join(dirpath, fname)
            target_file = os.path.normpath(os.path.join(structure, fname))

            if fname.endswith(".md"):
                # Replacing auto-doc comments
                if prepare_markdown(src_file, target_file, marker_dict,):
                    summary[0].append(target_file)
                else:
                    summary[1].append(target_file)
            else:
                shutil.copyfile(src_file, target_file)
                summary[2].append(target_file)
    return summary


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    # Scan the source files.
    mark_mapping = scan_sources(sys.argv[2:], strip_empty_line=True)
    summaries = prepare_all_markdowns(sys.argv[1], sys.argv[1] + "_out", mark_mapping)

    logging.info(f"{len(summaries[0])} markdown files get auto replaced.")
    logging.info(f"{len(summaries[1])} markdown files copied.")
    logging.info(f"{len(summaries[2])} other files copied.")
