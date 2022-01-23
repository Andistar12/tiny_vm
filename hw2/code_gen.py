"""
Generates assembly code targeted at the tiny vm. Parsing is in parser.py
"""

from pathlib import Path

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper


logger = logging.getLogger("asm-code-gen")


def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)


# Walks the tree (twice) and generates the end asm
class QuackASMGen(Visitor_Recursive):

    def __init__(self):
        self.identifiers = {} # Store local variable identifiers and data type
        self.asm = [] # Stores each assembly instruction

    def infer_name_type(self, tree, ident, scope=None):
        # Attempt to infer the identifier type/class, and get the name of it

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
            elif ident.data == "boolean_literal_true":
                return "true", "Boolean"
            elif ident.data == "boolean_literal_false":
                return "false", "Boolean"
            elif ident.data == "nothing_literal":
                return "none", "Nothing"

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
            if ident == "true" or ident == "false":
                return ident, "Boolean"
            if ident == "none":
                return ident, "Nothing"
            return ident, "String"
      
    def get_asm(self, main_class="Main"):
        # Generates the fully-formatted assembly program, line by line
        logger.trace("Writing assembly for program")
        self.add_asm("return 0")

        asm = [f".class {main_class}:Obj", "", ".method $constructor"]
        if len(self.identifiers.keys()) > 0:
            asm.append(".local " + ",".join(self.identifiers.keys()))
        for line in self.asm:
            asm.append("\t" + line)

        logger.trace("Generated assembly for program")
        logger.trace(asm)
        return asm

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
        
        # Remove surrounding quotes
        s = tree.children[0].value
        if s.startswith("\"\"\"") or s.startswith("'''"):
            s = s[3:-3]
        if s.startswith("\""):
            s = s[1:-1]

        # Unescaping this string was difficult, I tried re.escape(s), 
        # s.encode(unicode_escape), ast.literal_eval(s), r({}).format(s)
        # TODO there has to be a cleaner way to encode string literals
        self.add_asm("const \"" + repr(s)[1:-1] + "\"")

    def int_literal(self, tree):
        logger.debug(f"Processed int literal: {tree}")
        self.add_asm("const " + str(tree.children[0].value))

    def boolean_literal_true(self, tree):
        logger.debug(f"Processed boolean literal: {tree}")
        self.add_asm("const true")

    def boolean_literal_false(self, tree):
        logger.debug(f"Processed boolean literal: {tree}")
        self.add_asm("const false")
    
    def nothing_literal(self, tree):
        logger.debug(f"Processed nothing literal: {tree}")
        self.add_asm("const none")

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


def gen_asm_code(tree, main_class):
    logger.trace("Attempting to construct the code generator")
    quack_gen = QuackASMGen()
    logger.debug("Attempting to walk the tree to generate ASM")
    quack_gen.visit(tree)
    logger.debug("Attempting to generate the final asm")
    asm = quack_gen.get_asm(main_class)
    logger.debug("Successfully generated asm code")
    return asm
