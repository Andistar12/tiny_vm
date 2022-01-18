"""
Author:       Andy Nguyen
Class:        CIS 461
Term:         Winter 2022
Assignment:   Assignment 2
File:         compiler.py
Date:         15 January 2022
Notes:
 - we are adding basic statements and expressions to our language/compiler
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

# Setup project logging
log_helper.setup_logging("TRACE")
logger = logging.getLogger("quack-compiler")

def compile_error(msg):
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

# The quack grammar for lexical analysis
quack_grammar = "\n".join([
    "?start: program",

    # Definition of a program: a statement followed by a program (more statements)
    "?program: statement*                               -> program",
    
    # Definition of a statement: an expression or variable assignment
    "?statement: r_expr \";\"                           -> statement",
    "   | l_expr (\":\" CNAME)? \"=\" r_expr \";\"      -> assignment",

    # Definition of a left-hand expression: identifier, or object.identifier
    "?l_expr: identifier                                -> identifier_lhand",
    # TODO add object field for l_expr

    # Definition of an identifier: non digit character followed by alphanumeric
    "?identifier: [\"_\" | LETTER] CNAME*               -> identifier",

    # Definition of a right-hand expression: an identifier, constant, binary operator, or method invocation

    "?r_expr: r_expr_prod",
    "   | r_expr \"+\" r_expr_prod                      -> method_add",
    "   | r_expr \"-\" r_expr_prod                      -> method_sub",
    "   | r_expr \".\" method_name \"(\" method_args? \")\"     -> method_invocation",

    "?r_expr_prod: r_expr_atom",
    "   | r_expr_prod \"*\" r_expr_atom                 -> method_mul",
    "   | r_expr_prod \"/\" r_expr_atom                 -> method_div",

    "?r_expr_atom: l_expr                               -> identifier_rhand",
    "   | ESCAPED_STRING                                -> string_literal",
    "   | INT                                           -> int_literal",
    "   | \"-\" r_expr_atom                             -> method_neg",
    "   | \"(\" r_expr \")\"                            -> identifier_rhand",

    
    "?method_name: identifier                           -> identifier_method",
    "?method_args: r_expr (\",\" r_expr)*               -> method_args",

    # Useful defaults
    "%import common.INT",
    "%import common.ESCAPED_STRING",
    "%import common.WORD",
    "%import common.LETTER",
    "%import common.CNAME",

    # Ignore whitespace
    "%import common.WS_INLINE",
    "%import common.WS",
    "%ignore WS",
    "%ignore WS_INLINE"
])


# Parses the tree into assembly - syntatic analysis 
class QuackParser(Visitor_Recursive):

    def __init__(self):
        self.identifiers = {} # Store local variable identifiers and data type
        self.asm = [] # Stores each assembly instruction

    def infer_name_type(self, tree, ident, scope=None):
        # Attempt to infer the identifier type, and get the name of it

        if isinstance(ident, Tree):
            # For identifiers, just recurse
            if ident.data == "identifier":
                return self.infer_name_type(tree, ident.children[1].value) # Token in index 1 spot
            elif ident.data.startswith("identifier"): # includes _lhand, _rhand, _method
                return self.infer_name_type(tree, ident.children[0])
            elif ident.data.startswith("method_"): # some sort of method invocation
                return self.infer_name_type(tree, ident.children[0])
            elif ident.data == "int_literal":
                return ident.children[0].value, "Int"
            elif ident.data == "string_literal":
                return ident.children[0].value, "String"
            else:
                compile_error(f"Attempted to infer name and type of unknown tree type {ident.data} in {tree}")

        elif isinstance(ident, Token):
            return self.infer_name_type(tree, ident.token)

        if ident in self.identifiers:
            return ident, self.identifiers[ident]

        try:
            a = int(ident)
            return ident, "Int"
        except ValueError:
            return ident, "String"
      
    def write_asm(self, output_name):
        # Generates the full assembly program
        logger.trace("Writing assembly for program")
        self.add_asm("return 0")
        with open(output_name, "w") as f:
            f.write(".class Sample:Obj\n\n.method $constructor\n")
            f.write(".local " + ",".join(self.identifiers.keys()))
            for line in self.asm:
                f.write("\n\t")
                f.write(line)
            f.write("\n")

    def add_asm(self, line):
        # Adds a line of assembly to the output
        logger.debug("Generated assembly: " + line)
        self.asm.append(line)

    def program(self, tree):
        logger.trace(f"Processed program: {tree}")

    def identifier(self, tree):
        logger.trace(f"Processed identifier: {tree}")

    def identifier_rhand(self, tree):
        logger.debug(f"Processed identifier_rhand: {tree}")
        ident, _ = self.infer_name_type(tree, tree.children[0])
        if tree.children[0].data == "identifier_lhand":
            self.add_asm("load " + ident)

    def identifier_lhand(self, tree):
        logger.trace(f"Processed identifier_lhand: {tree}")

    def statement(self, tree):
        logger.trace(f"Processed statement: {tree}")

    def assignment(self, tree):
        logger.debug(f"Processed assignment: {tree}")
        if tree.children[0].children[0].data == "identifier":

            ident, _ = self.infer_name_type(tree, tree.children[0])

            if len(tree.children) == 3:
                # Need to store identifier type
                self.identifiers[ident] = tree.children[1].value # Add identifier
            else:
                if ident not in self.identifiers:
                    compile_error(f"Identifier {ident} used before type declaration. Quit")

        self.add_asm("store " + ident)

    def string_literal(self, tree):
        logger.debug(f"Processed string literal: {tree}")
        self.add_asm("const " + str(tree.children[0].value))

    def int_literal(self, tree):
        logger.debug(f"Processed int literal: {tree}")
        self.add_asm("const " + str(tree.children[0].value))

    def method_add(self, tree):
        logger.debug(f"Processed method add: {tree}")
        _, clazz = self.infer_name_type(tree, tree.children[1])
        self.add_asm(f"call {clazz}:plus")

    def method_sub(self, tree):
        logger.debug(f"Processed method sub: {tree}")
        self.add_asm("call Int:minus")

    def method_mul(self, tree):
        logger.debug(f"Processed method mul: {tree}")
        self.add_asm("call Int:times")

    def method_div(self, tree):
        logger.debug(f"Processed method div: {tree}")
        self.add_asm("call Int:divide")

    def method_neg(self, tree):
        logger.debug(f"Processed method neg: {tree}")
        self.add_asm("call Int:negate")

    def method_invocation(self, tree):
        logger.debug(f"Processed method invocation: {tree}")
        _, clazz = self.infer_name_type(tree, tree.children[0]) # Get object class
        ident, _ = self.infer_name_type(tree, tree.children[1]) # Get method name
        self.add_asm(f"call {clazz}:{ident}")

    def method_args(self, tree):
        logger.trace(f"Processed method args: {tree}")

    def visit(self, tree):
        # For specific trees, need to visit them in special order
        if tree.data == "assignment":
            # Want to visit rhand before lhand
            logger.trace("Processing assignment, using custom traversal")
            if len(tree.children) == 3:
                # ident: Class = value; 
                #  0 : 1 = 2. Skip 1
                self.visit(tree.children[2])
                self.visit(tree.children[0])
            else:
                self.visit(tree.children[1])
                self.visit(tree.children[0])
        elif tree.data == "method_sub" or tree.data == "method_div":
            # Want to visit second operand before first operand
            logger.trace("Processing method_sub/div, using custom traversal")
            self.visit(tree.children[1])
            self.visit(tree.children[0])
        else:
            # Default to normal traversal
            return super().visit(tree)

        # Don't forget to visit our tree then give it back
        self._call_userfunc(tree)
        return tree

if __name__ == '__main__':

    # Argument check
    if len(sys.argv) <= 1:
        print(f"Usage: {sys.argv[0]} <file>")
        exit(1)

    # Read entire program into memory
    logger.debug("Reading in program text")
    prgm_text = ""
    prgm_file = sys.argv[1]
    with open(prgm_file, "r") as f:
        prgm_text = f.read()
    logger.info("Program text successfully read in")

    # Lex the program
    logger.debug("Attempting to parse the grammer")
    quack_lexer = Lark(quack_grammar, parser="lalr")
    logger.debug("Atetmpting to lex the program text")
    tree = quack_lexer.parse(prgm_text)
    logger.info("Program text successfully lexed")

    # Parse the program
    logger.debug("Attempting to construct the parser")
    quack_parser = QuackParser()
    logger.debug("Attempting to parse the tree")
    quack_parser.visit(tree)
    logger.info("Program text successfully parsed")

    logger.trace("Outputted assembly:")
    logger.trace(quack_parser.asm)
    logger.trace(quack_parser.identifiers)

    # Write program to output
    output_file = "output.asm"
    logger.debug("Attempting to write assembly output")
    quack_parser.write_asm(output_file)
    logger.info(f"Assembly successfully outputted to {output_file}")

