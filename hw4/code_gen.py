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
from type_inf import tree_type_table

logger = logging.getLogger("asm-code-gen")


def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)


# Walks the tree and generates the end asm
class QuackASMGen(Visitor_Recursive):

    def __init__(self, main_class="Main", class_map = default_class_map, identifiers={}):
        self.asm = {} # Stores each assembly instruction
        self.main_class = main_class

        # Specifies which class and method we are in
        self.curr_class = ""
        self.curr_method = ""

        # Control flow short circuit helpers
        self.label_counts = {}
        self.sc_true = None
        self.sc_false = None

        # Setup method signatures of default
        self.class_map = class_map

    def gen_label(self, prefix):
        # Generates a new label with given prefix
        num = self.label_counts.get(prefix, 0) + 1
        self.label_counts[prefix] = num
        return f"{prefix}_{num}"

    def infer_type(self, ident):
        # Attempts to infer the type of this tree

        if isinstance(ident, Tree):
            # Check for default cases
            #if ident.data == "this_ptr":
            #    return self.curr_class

            if ident.data in tree_type_table:
                return tree_type_table[ident.data]

            # Check for fields
            elif ident.data.startswith("identifier_field"):
                if "this" in ident.data:
                    clazz = self.curr_class
                    name = ident.children[0].value
                else:
                    clazz = self.infer_type(ident.children[0])
                    name = ident.children[1].value
                if clazz not in self.class_map:
                    compile_error(f"Attempted to get field from unknown class {clazz}")
                return self.class_map[clazz]["field_list"][name]

            # Identifiers may be nested but will have a token eventually
            elif ident.data.startswith("identifier"):
                name = self.get_ident_name(ident.children[0])
                return self.class_map[self.curr_class]["method_locals"][self.curr_method][name]

            elif ident.data == "method_invocation":
                # See what type the calling object is first
                clazz = self.infer_type(ident.children[1])
                # Look for return type of method
                method = self.get_ident_name(ident.children[0])
                if method not in self.class_map[clazz]["method_returns"]:
                    compile_error(f"Attempted to get return type of unknown method {method} in ident of class {clazz}")
                return self.class_map[clazz]["method_returns"][method]

            elif ident.data == "obj_instantiation":
                return self.get_ident_name(ident.children[0])
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
        # Gets the actual name of an identifier

        if isinstance(ident, Tree):
            # For identifiers, just recurse
            if ident.data.startswith("identifier"):
                if "field" in ident.data and "this" not in ident.data:
                    return self.get_ident_name(ident.children[1])
                return self.get_ident_name(ident.children[0]) # Recurse on only child
            else:
                compile_error(f"Attempted to get identifier name in unknown tree type {ident.data} {ident}")
        elif isinstance(ident, Token):
            return ident.value
        else:
            compile_error(f"Attempted to get identifier name in unrecognizable object {ident}")
      
    def get_asm(self):

        logger.trace("Writing assembly for program")
        ret_asm = {}

        # Return the ASM code in a dictionary per class
        for clazz in self.asm:
            logger.trace(f"Writing assembly for class {clazz}")
            class_code = []

            # Add class info
            superclass = self.class_map[clazz]["superclass"]
            class_code.append(f".class {clazz}:{superclass}")
            for field in self.class_map[clazz]["field_list"]:
                class_code.append(f".field {field}")

            # Forward declare methods
            for method in self.class_map[clazz]["method_arg_names"]:
                if method != "$constructor":
                    class_code.append(f".method {method} forward")

            # Add method
            for method in self.class_map[clazz]["method_arg_names"]:
                logger.trace(f"Writing assembly for method {method} in class {clazz}")
                class_code.append("")
                class_code.append(f".method {method}")

                # Add method args and class code
                method_args = self.class_map[clazz]["method_arg_names"][method]
                local_vars = [x for x in self.class_map[clazz]["method_locals"][method] if x not in method_args]
                if len(method_args) > 0:
                    class_code.append(f".args {','.join(method_args)}")
                if len(local_vars) > 0:
                    class_code.append(f".local {','.join(local_vars)}")

                # Generate method code
                for line in self.asm[clazz][method]:
                    if line.startswith(".label"):
                        class_code.append(line[7:] + ":")
                    else:
                        class_code.append("\t" + line)

            ret_asm[clazz] = class_code

        logger.trace("Generated assembly for program")
        logger.trace(ret_asm)
        return ret_asm

    def add_asm(self, line):
        # Adds a line of assembly to the output
        logger.debug("Generated assembly: " + line)
        code = self.asm[self.curr_class][self.curr_method]
        code.append(line)
        self.asm[self.curr_class][self.curr_method] = code

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

    def identifier_field_rhand_this(self, tree):
        logger.debug(f"Processed identifier_field_rhand_this: {tree}")
        ident = self.get_ident_name(tree.children[0])
        self.add_asm(f"load $")
        self.add_asm(f"load_field $:{ident}")

    def identifier_field_lhand_this(self, tree):
        logger.debug(f"Processed identifier_field_lhand_this: {tree}")
        ident = self.get_ident_name(tree.children[0])
        self.add_asm(f"load $")
        self.add_asm(f"store_field $:{ident}")

    def identifier_field_rhand(self, tree):
        logger.debug(f"Processed identifier_field_rhand: {tree}")
        ident = self.get_ident_name(tree.children[1])
        # Calling object shjould already be on the stack
        clazz = self.infer_type(tree.children[0])
        self.add_asm(f"load_field {clazz}:ident")

    def statement(self, tree):
        logger.trace(f"Processed statement: {tree}")

    def identifier_field_lhand(self, tree):
        logger.debug(f"Processed identifier_field_lhand: {tree}")
        ident = self.get_ident_name(tree.children[1])
        # Calling object shjould already be on the stack
        clazz = self.infer_type(tree.children[0])
        self.add_asm(f"store_field {clazz}:ident")

    def assignment(self, tree):
        logger.debug(f"Processed assignment: {tree}")

        # Identifier for local variable (without field)
        if "field" not in tree.children[0].data:
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

    def this_ptr(self, tree):
        logger.debug(f"Processed this pointer: {tree}")
        self.add_asm("load $")

    def method_invocation(self, tree):
        logger.debug(f"Processed method invocation: {tree}")
        clazz = self.infer_type(tree.children[1]) # Get object class
        ident = self.get_ident_name(tree.children[0]) # Get method name
        
        self.add_asm(f"call {clazz}:{ident}")
        
        # Pop the nothings
        if clazz == "$":
            clazz = self.curr_class
        ret_type = self.class_map[clazz]["method_returns"][ident]
        if ret_type == "Nothing":
            self.add_asm("pop")

    def method_args(self, tree):
        logger.trace(f"Processed method args: {tree}")

    def return_statement(self, tree):
        logger.trace(f"Processed return_statement: {tree}")
        args = self.class_map[self.curr_class]["method_args"][self.curr_method]
        self.add_asm(f"return {len(args)}")

    def cond_and(self, tree):
        # Needs a label to use skip over. See if there's an active label
        # set by a control structure first
        label = self.sc_false if self.sc_false else self.gen_label("and")
        logger.trace(f"Processed cond_and with label {label}: {tree}")
        
        # Visit first child
        self.visit(tree.children[0])

        # Jump if this is false
        self.add_asm(f"jump_ifnot {label}")

        # Visit second child
        self.visit(tree.children[1])

        # Add label
        self.add_asm(f".label {label}")

    def cond_or(self, tree):
        # Needs a label to use skip over. See if there's an active label
        # set by a control structure first
        label = self.sc_true if self.sc_true else self.gen_label("or")
        logger.trace(f"Processed cond_or with label {label}: {tree}")
        
        # Visit first child
        self.visit(tree.children[0])

        # Jump if this is true
        self.add_asm(f"jump_if {label}")

        # Visit second child
        self.visit(tree.children[1])

        # Add label
        self.add_asm(f".label {label}")

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

    def clazz(self, tree):
        logger.trace(f"Processed clazz: {tree}")

        # First set current class
        self.curr_class = self.get_ident_name(tree.children[0])
        self.asm[self.curr_class] = {}

        # Now visit third child, which is class body
        self.visit(tree.children[2])

    def class_method(self, tree):
        logger.trace(f"Processed method: {tree}")

        # First set current method
        self.curr_method = self.get_ident_name(tree.children[0])
        self.asm[self.curr_class][self.curr_method] = []

        # Now visit body (fourth child)
        self.visit(tree.children[3])

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

        elif tree.data == "clazz":
            # Let class handle itself
            self._call_userfunc(tree)

        elif tree.data == "class_method":
            # Let method handle itself
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
    asm = quack_gen.get_asm()
    logger.debug("Successfully generated asm code")
    return asm
