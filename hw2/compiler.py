"""
The entrypoint for the Quack compiler. Handles CLI args and file I/O
"""

import os
import logging
import argparse

import log_helper

if __name__ == "__main__":
    # Parse CLI args
    cliparser = argparse.ArgumentParser(description="Compiles a Quack program")
    cliparser.add_argument("--log-level", "-D", metavar="log-level", default="INFO", help="Specifies the log level. Can be INFO, DEBUG, or TRACE. Default INFO")
    cliparser.add_argument("--main-class", "-m", metavar="clazz", default=None, help="Specifies the main class name. Default inferred from source filename")
    cliparser.add_argument("--output", "-o", metavar="file", default=None, help="Specifies the output file for assembly. Default put in out/ directory")
    cliparser.add_argument("--output-json", "-j", metavar="file", default=None, help="Specifies the output file for JSON. Default put in out/ directory")
    cliparser.add_argument("source", metavar="<source>", help="The source program file")
    args = cliparser.parse_args()

    # Configure logging
    log_level = args.log_level
    log_helper.setup_logging(log_level)
    logger = logging.getLogger("quack-compiler")
    logger.debug("Logging succesfully setup")

    # Dynamic import after logging setup. This is cursed :)
    import parser
    import code_gen
    import assemble
    
    # Read entire program into memory
    prgm_file = args.source
    logger.debug("Attempting to read program " + prgm_file + " into memory")
    prgm_text = ""
    with open(prgm_file, "r") as f:
        prgm_text = f.read()
    if prgm_text == "":
        logger.warning("The source file is empty")
    logger.info("Successfully read in the program text")
    
    # Parse the program
    logger.debug("Attempting to parse the program")
    tree = parser.parse(prgm_text)
    logger.info("Successfully parsed the program")

    # Generate the assembly
    main_class = args.main_class
    if main_class == None:
        main_class = "".join(os.path.basename(prgm_file).split(".")[:-1])
    logger.debug("Attempting to generate the assembly with main class name " + main_class)
    asm = code_gen.gen_asm_code(tree, main_class)
    logger.info("Successfully generated the assembly code")

    # Output the assembly
    output_file = args.output
    if output_file == None:
        output_file = f"out/{main_class}.asm"
    logger.debug("Attempting to output assembly code to file " + output_file)
    os.makedirs(os.path.dirname(output_file), exist_ok=True) # Make subdirectories
    with open(output_file, "w") as f:
        for line in asm:
            f.write(line)
            f.write("\n")
    logger.info("Successfully written assembly to file " + output_file)

    # Generate the object code
    logger.debug("Attempting to generate object code")
    obj = assemble.translate(asm)
    logger.info("Successfully generated object code")

    # Output the object code
    output_file = args.output_json
    if output_file == None:
        output_file = f"out/{main_class}.json"
    logger.debug("Attempting to output object code to file " + output_file)
    os.makedirs(os.path.dirname(output_file), exist_ok=True) # Make subdirectories
    with open(output_file, "w") as f:
        f.write(obj.json())
    logger.info("Successfully written object code to file " + output_file)

    logger.info("Compilation success")

