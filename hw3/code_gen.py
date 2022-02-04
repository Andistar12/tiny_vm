"""
Generates assembly code targeted at the tiny vm. Parsing is in parser.py
"""

from pathlib import Path

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

from default_class_map import default_class_map

logger = logging.getLogger("asm-code-gen")


def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)


# Walks the tree (twice) and generates the end asm
class QuackASMGen(Visitor_Recursive):

    def __init__(self, main_class="Main", class_map = default_class_map, identifiers={}):
        self.identifiers = identifiers # Store local variable identifiers and data type
        self.asm = [] # Stores each assembly instruction
        self.main_class = main_class # The name of the main class

        # Setup method signatures of default
        self.class_map = class_map
        self.class_map[main_class] = { # TODO deep copy from parent class
            "superclass":"Obj",
            "field_list":{},
            "method_returns":{
                "$constructor":"Obj",
                "string":"String",
                "print":"Nothing"
            },
            "method_args":{
                "$constructor":[],
                "string":[],
                "print":[]
            }
        }

    def infer_name_type(self, ident):
        # Attempt to infer the identifier type/class, and get the name of it
        logger.trace(f"Attempting to infer type and name of {ident}")

        if isinstance(ident, Tree):
            # For identifiers, just recurse
            if ident.data == "identifier":
                # TODO this will change when we add fields
                return self.infer_name_type(ident.children[0].value) # Child is a token
            elif ident.data.startswith("identifier"):
                return self.infer_name_type(ident.children[0]) # Recurse
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
                
            elif ident.data == "method_invocation":
                # Validate method and class
                _, clazz = self.infer_name_type(ident.children[1]) # Get object class
                ident, _ = self.infer_name_type(ident.children[0]) # Get method name
                
                if clazz not in self.class_map:
                    compile_error(f"Attempted to invoke method {ident} of unknown class {clazz}")
                if ident not in self.class_map[clazz]["method_returns"]:
                    compile_error(f"Attempted to invoke unknown method {ident} of class {clazz}")

                return ident, self.class_map[clazz]["method_returns"][ident]

            else:
                compile_error(f"Attempted to infer name and type of unknown tree type {ident.data}")

        elif isinstance(ident, Token):
            if ident.type == "INT":
                return ident.value, "INT"
            elif ident.type == "ESCAPED_STRING" or ident.type == "CNAME":
                return ident.value, "String"
            elif ident.type == "CNAME":
                compile_error(f"Could not find type of unknown identifier {ident}")

            return self.infer_name_type(ident.value)

        if ident in self.identifiers:
            return ident, self.identifiers[ident]

        logger.warn(f"Could not infer type of {ident}. Attempting to parse by value")

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
        ident, _ = self.infer_name_type(tree.children[0])
        self.add_asm("load " + ident)

    def identifier_lhand(self, tree):
        logger.trace(f"Processed identifier_lhand: {tree}")

    def statement(self, tree):
        logger.trace(f"Processed statement: {tree}")

    def assignment(self, tree):
        logger.debug(f"Processed assignment: {tree}")
        # Identifier for local variable (without field)

        ident, _ = self.infer_name_type(tree.children[0])
        logger.warn(f"ident is {ident}")

        if len(tree.children) == 3:
            # Need to store identifier type
            self.identifiers[ident] = tree.children[1].children[0].value # Add identifier
        else:
            if ident not in self.identifiers:
                compile_error(f"Identifier {ident} used before type declaration. Quit")

        self.add_asm("store " + ident)

    def string_literal(self, tree):
        logger.debug(f"Processed string literal: {tree}")
        self.add_asm("const " + tree.children[0].value)

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

    def method_invocation(self, tree):
        logger.debug(f"Processed method invocation: {tree}")
        _, clazz = self.infer_name_type(tree.children[1]) # Get object class
        ident, _ = self.infer_name_type(tree.children[0]) # Get method name
        
        if clazz not in self.class_map:
            compile_error(f"Attempted to invoke method {ident} of unknown class {clazz}")
        if ident not in self.class_map[clazz]["method_returns"]:
            compile_error(f"Attempted to invoke unknown method {ident} of class {clazz}")

        self.add_asm(f"call {clazz}:{ident}")
        
        # Pop the nothings
        ret_type = self.class_map[clazz]["method_returns"][ident]
        if ret_type == "Nothing":
            self.add_asm("pop")

    def method_args(self, tree):
        logger.trace(f"Processed method args: {tree}")

    def visit(self, tree):

        if not isinstance(tree, Tree):
            return tree

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
        elif tree.data == "method_invocation":
            # Want to visit method args in reverse order to put calling object on stack last
            logger.trace("Processing method_invocation, using custom traversal")
            for child in reversed(tree.children):
                self.visit(child)
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
