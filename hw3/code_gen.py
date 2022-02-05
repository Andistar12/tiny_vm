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
        self.idents = identifiers # Store local variable identifiers and data type
        self.asm = [] # Stores each assembly instruction
        self.main_class = main_class # The name of the main class

        # Control flow short circuit helpers
        self.label_counts = {}
        self.sc_true = None
        self.sc_false = None

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

    def gen_label(self, prefix):
        # Generates a new label with given prefix
        num = self.label_counts.get(prefix, 0) + 1
        self.label_counts[prefix] = num
        return f"{prefix}_{num}"

    def infer_type(self, ident):
        # Attempts to infer the type of this tree

        if isinstance(ident, Tree):
            # Hardcode the literal cases (only five of them)
            if ident.data == "boolean_literal_false":
                return "Boolean"
            elif ident.data == "boolean_literal_true":
                return "Boolean"
            elif ident.data == "nothing_literal":
                return "Nothing"
            elif ident.data == "int_literal":
                return "Int"
            elif ident.data == "string_literal":
                return "String"


            # Identifiers may be nested but will have a token eventually
            elif ident.data == "identifier":
                # If we have it return it, otherwise return the generic
                return self.idents[ident.children[0].value]
            elif ident.data.startswith("identifier"):
                # Nested "identifier" tree nodes
                return self.infer_type(ident.children[0])

            elif ident.data == "method_invocation":
                # See what type the calling object is first
                clazz = self.infer_type(ident.children[1])
                # Look for return type of method
                method = self.get_ident_name(ident.children[0])
                return self.class_map[clazz]["method_returns"][method]
            else:
                compile_error(f"Attempted to infer type of unknown tree {ident}")

        elif isinstance(ident, Token):
            if ident.type == "INT":
                return "Int"
            elif ident.type == "ESCAPED_STRING":
                return "String"
            else:
                compile_error(f"Attempted to infer type of unknown Token {ident}")

        else:
            compile_error(f"Attempted to infer type of unknown object {ident}")

    def get_ident_name(self, ident):
        # Gets the actual name of the identifier

        if isinstance(ident, Tree):
            # For identifiers, just recurse
            if ident.data == "identifier":
                # TODO this will change when we add fields
                return ident.children[0].value # Child is a token
            elif ident.data.startswith("identifier"):
                return self.get_ident_name(ident.children[0]) # Recurse on only child
            else:
                compile_error(f"Attempted to get identifier name in unknown tree type {ident.data} {ident}")
        elif isinstance(ident, Token):
            return ident.value
        else:
            compile_error(f"Attempted to get identifier name in unrecognizable object {ident}")
      
    def get_asm(self, main_class="Main"):
        # Generates the fully-formatted assembly program, line by line
        logger.trace("Writing assembly for program")
        self.add_asm("return 0")

        asm = [f".class {main_class}:Obj", "", ".method $constructor"]
        if len(self.idents.keys()) > 0:
            asm.append(".local " + ",".join(self.idents.keys()))

        for line in self.asm:
            if line.startswith(".label"):
                asm.append(line[7:] + ":")
            else:
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
        ident = self.get_ident_name(tree.children[0])
        self.add_asm("load " + ident)

    def identifier_lhand(self, tree):
        logger.trace(f"Processed identifier_lhand: {tree}")

    def statement(self, tree):
        logger.trace(f"Processed statement: {tree}")

    def assignment(self, tree):
        logger.debug(f"Processed assignment: {tree}")
        # Identifier for local variable (without field)
        ident = self.get_ident_name(tree.children[0])
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
        clazz = self.infer_type(tree.children[1]) # Get object class
        ident = self.get_ident_name(tree.children[0]) # Get method name
        
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

    def cond_and(self, tree):
        # Needs a label to use skip over. See if there's an active label
        # set by a control structure first
        label = self.sc_false if self.sc_false else self.get_label("and")
        logger.trace(f"Processed cond_and with label {label}: {tree}")
        
        # Visit first child
        self.visit(tree.children[0])

        # Jump if this is false
        self.add_asm(f"jump_ifnot {label}")

        # Visit second child
        self.visit(tree.children[1])

        # Add label
        self.add_asm(f".{label}")

    def cond_or(self, tree):
        # Needs a label to use skip over. See if there's an active label
        # set by a control structure first
        label = self.sc_true if self.sc_true else self.get_label("or")
        logger.trace(f"Processed cond_or with label {label}: {tree}")
        
        # Visit first child
        self.visit(tree.children[0])

        # Jump if this is true
        self.add_asm(f"jump_if {label}")

        # Visit second child
        self.visit(tree.children[1])

        # Add label
        self.add_asm(f".{label}")

    def cond_not(self, tree):
        logger.trace(f"Processed cond_not: {tree}")
        if self.sc_true:
            # We are in conditional, switch the branches
            logger.trace("cond_not in condition, swapping two branches")
            self.sc_true, self.sc_false = self.sc_false, self.sc_true
            # Now visit child
            self.visit(tree.children[0])
        else:
            # Need to generate inversion logic. Wrote native method for this :)
            logger.trace("cond_not not in condition, calling native Boolean:negate")
            self.visit(tree.children[0])
            self.add_asm("call Boolean:negate")

    def if_structure(self, tree):
        logger.trace(f"Processed if_structure: {tree}")

        if len(tree.children) == 2: # No else clause
            # First generate two labels
            branch1 = self.gen_label("ifbranch1")
            self.sc_true = branch1
            endif = self.gen_label("ifend")
            self.sc_false = endif

            # Now generate the conditional
            self.visit(tree.children[0])
            self.add_asm(f"jump_ifnot {endif}")

            # Now generate the first branch
            self.add_asm(f".label {branch1}")
            self.visit(tree.children[1])

            # Now add the end of if
            self.add_asm(f".label {endif}")

        else: # Else clause present

            # First generate three labels
            branch1 = self.gen_label("ifbranch1")
            self.sc_true = branch1
            branch2 = self.gen_label("ifbranch2")
            self.sc_false = branch2
            endif = self.gen_label("ifend")

            # Now generate the conditional
            self.visit(tree.children[0])
            self.add_asm(f"jump_ifnot {branch2}")

            # Now generate the first branch
            self.add_asm(f".label {branch1}")
            self.visit(tree.children[1])
            self.add_asm(f"jump {endif}")

            # Now generate the second branch
            self.add_asm(f".label {branch2}")
            self.visit(tree.children[2])

            # Now add the end of if
            self.add_asm(f".label {endif}")

        # Finally, reset the short circuit branches
        self.sc_true = None
        self.sc_false = None

    def while_structure(self, tree):
        logger.trace(f"Processed while_structure: {tree}")

        # First generate three labels
        loop = self.gen_label("whileloop")
        self.sc_true = loop
        endwhile = self.gen_label("whileend")
        self.sc_false = endwhile
        cond = self.gen_label("whilecond")

        # First jump to condition
        self.add_asm(f"jump {cond}")

        # Now generate the loop
        self.add_asm(f".label {loop}")
        self.visit(tree.children[1])

        # Now generate the test condition
        self.add_asm(f".label {cond}")
        self.visit(tree.children[0])
        self.add_asm(f"jump_if {loop}")

        # Now add the end of while
        self.add_asm(f".label {endwhile}")

        # Finally, reset the short circuit branches
        self.sc_true = None
        self.sc_false = None

    def visit(self, tree):

        if not isinstance(tree, Tree):
            return tree

        # For specific trees, need to visit them in special order
        if tree.data == "assignment":
            # Want to visit rhand before lhand to put rhand on the stack first
            logger.trace("Processing assignment, using custom traversal")
            self.visit(tree.children[1])
            self.visit(tree.children[0])
            self._call_userfunc(tree)
        elif tree.data == "method_invocation":
            # Want to visit method args in reverse order to put calling object on stack last
            logger.trace("Processing method_invocation, using custom traversal")
            for child in reversed(tree.children):
                self.visit(child)
            self._call_userfunc(tree)

        elif tree.data == "if_structure" or tree.data == "while_structure":
            # Let control structures handle themselves, do not visit children
            self._call_userfunc(tree)

        elif tree.data.startswith("cond"):
            # and/or/not (has short circuit logic). Do not visit children, let method handle it
            self._call_userfunc(tree)

        else:
            # Default to normal traversal
            return super().visit(tree)

        return tree


def gen_asm_code(tree, main_class, idents):
    logger.trace("Attempting to construct the code generator")
    quack_gen = QuackASMGen(main_class=main_class, identifiers=idents)
    logger.debug("Attempting to walk the tree to generate ASM")
    quack_gen.visit(tree)
    logger.debug("Attempting to generate the final asm")
    asm = quack_gen.get_asm(main_class)
    logger.debug("Successfully generated asm code")
    return asm
