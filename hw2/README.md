# File explanation

* asm.conf: used by assembler. The OBJ folder is shared with the main vm
* assemble.py: the assembler itself
* code_gen.py: generates the assembly code by walking the tree
* compiler.py: the entrypoint, handles CLI args and file I/O
* log_helper.py: handles console logging
* opdefs.txt: used by assembler
* parser.py: contains the language grammar and lexes and parses the input
