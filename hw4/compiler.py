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
    cliparser.add_argument("--output-dir", "-o", metavar="file", default=None, help="Specifies the output file directory. Default out/")
    cliparser.add_argument("--obj-dir", "-j", metavar="file", default=None, help="Specifies the output file directory for OBJ files. Default OBJ/")
    cliparser.add_argument("--png", "-p", metavar="filename", default=None, help="If set, visualizes the parsed tree as a PNG stored at given filename")
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
    import ident_usage
    import type_inf
    import manual_checks
    
    # Read entire program into memory
    prgm_file = args.source
    logger.debug("Attempting to read program " + prgm_file + " into memory")
    prgm_text = ""
    with open(prgm_file, "r") as f:
        prgm_text = f.read()
    if prgm_text == "":
        logger.warning("The source file is empty")
    logger.info("Successfully read in the program text")

    main_class = args.main_class
    if main_class == None:
        main_class = "".join(os.path.basename(prgm_file).split(".")[:-1])
    
    # Parse the program
    logger.debug("Attempting to parse the program")
    tree = parser.parse(prgm_text, main_class=main_class)
    logger.info("Successfully parsed the program")

    # Visualize the tree
    png_file = args.png
    if png_file:
        logger.debug("Attempting to save the tree as a PNG")
        parser.visualize(tree, png_file)
        logger.info(f"Successfully saved tree to file {png_file}")

    # Static semantic checks
    logger.debug("Attempting to check identifier declaration vs usage")
    ident_usage.check(tree) # Check tree declares identifiers before using them
    logger.debug("Attempting to perform type inferencing on declarations")
    inferred_types = type_inf.infer(tree) # Perform type inferencing
    logger.debug("Attempting to perform final tree and class hierarchy checks")
    manual_checks.check(tree, inferred_types)
    logger.info("Successfully performed static semantic checks on tree")

    # Generate the assembly
    logger.debug("Attempting to generate the assembly with main class name " + main_class)
    asm_output = code_gen.gen_asm_code(tree, main_class, inferred_types)
    logger.info("Successfully generated the assembly code")

    output_dir = args.output_dir
    if output_dir == None:
        output_dir = "out"

    obj_dir = args.obj_dir
    if obj_dir == None:
        obj_dir = "OBJ"

    # Output the assembly and object code
    for clazz in asm_output:
        output_file = f"{output_dir}/{clazz}.asm"
        logger.debug("Attempting to output assembly code to file " + output_file)
        os.makedirs(os.path.dirname(output_file), exist_ok=True) # Make subdirectories
        with open(output_file, "w") as f:
            for line in asm_output[clazz]:
                f.write(line)
                f.write("\n")
        logger.info("Successfully written assembly to file " + output_file)

        # Generate the object code
        logger.debug(f"Attempting to generate object code for {clazz}")
        obj = assemble.translate(asm_output[clazz])
        logger.debug(f"Successfully generated object code for {clazz}")

        output_file = f"{obj_dir}/{clazz}.json"
        logger.debug("Attempting to output object code to file " + output_file)
        os.makedirs(os.path.dirname(output_file), exist_ok=True) # Make subdirectories
        with open(output_file, "w") as f:
            f.write(obj.json())

        os.sync() # Fixes race condition bugs with assembler loading
        logger.info("Successfully written object code to file " + output_file)

    logger.info("Compilation success")

