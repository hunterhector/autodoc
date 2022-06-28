This script analyzes the source files with some markers to find
the line numbers of the code blocks, and then uses 
[markdown-autodoc](https://github.com/dineshsonachalam/markdown-autodocs)
(actually, the [dockerized version](https://github.com/karolswdev/autodocs-markdown-docker))
to generate markdown files with the code blocks. One difference
from using markdown-autodoc directly is that one don't have to
hardcode the line numbers so one can feel free to modify the
source code.

Essentially, in additional to the `lines` option, we add the `label` option to insert code
blocks between `SOURCE_MARKER_BEGIN_{label}` and `SOURCE_MARKER_END_{label}` from the
source code.

## Requires
 - comment_parser
   - `pip install comment_parser`
 - [markdown-autodoc dockerized](https://github.com/karolswdev/autodocs-markdown-docker)
   - `docker pull karolswdev/autodocs-markdown-docker:latest`

## Usage 

```
python code_block.py [markdown input] [source code]
```

The output directory will be the directory with "_out" appending to 
the input directory.

Try the example markdown files in this repo with the following:
```
python code_block.py markdown source
```

![image](https://raw.githubusercontent.com/hunterhector/autodoc/main/autodoc.gif)


## Assumptions
 - The source files should have correct extension so that the MIME
    types can be determined.
      * We will use # (python/shell comments) for unknown types
 - Have https://github.com/karolswdev/autodocs-markdown-docker docker
    ready.
 - Output directory will be produced in the same level/structure of the
    input (i.e. from ./input/ to ./output/, not ./input/ to ./some/output/)
 - Rely on certain string pattern to do the replacement (such as `&`).
 - Comment tags should be simple ascii names (no special characters, spaces, underscores).
 - Comment tags cannot be nested.
