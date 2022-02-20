"""
Static semantic
Checks that the given tree consistently assigns identifiers before their usage
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

from default_class_map import default_class_map

logger = logging.getLogger("ident-usage")


def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)


class IdentUsageCheck(Visitor_Recursive):

    def __init__(self):
        self.constructor = False # Whether we are currently in a constructor
        self.idents = set()
        self.class_idents = set()
        self.class_idents_seen = set()

    def get_ident_name(self, ident):
        # Gets the actual name of the identifier

        if isinstance(ident, Tree):
            # For identifiers, just recurse
            if ident.data == "identifier":
                return ident.children[0].value # Child is a token
            elif ident.data.startswith("identifier"):
                return self.get_ident_name(ident.children[0]) # Recurse on only child
            else:
                compile_error(f"Attempted to get identifier name in unknown tree type {ident.data} {ident}")
        elif isinstance(ident, Token):
            return ident.value
        else:
            compile_error(f"Attempted to get identifier name in unrecognizable tree {ident}")


    def identifier_lhand(self, tree):
        # We have now seen this variable, keep track of it
        ident = self.get_ident_name(tree)
        logger.trace(f"Logging identifier {ident} as seen from tree {tree}")
        self.idents.add(ident)

    def identifier_field_lhand_this(self, tree):
        # Note it only checks within the class, let type checker handle cross-class
        # Have now seen this field variable, add to class
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Logging field identifier {ident} as seen from tree {tree}")
        if self.constructor: # Class fields must defined in constructor
            self.class_idents.add(ident)
        self.class_idents_seen.add(ident)

    def identifier_field_rhand_this(self, tree):
        # We must check if we've seen this field variable. Check later, mark as seen now
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Checking whether field identifier {ident} has been seen at tree {tree}")
        self.class_idents_seen.add(ident)

    def identifier_rhand(self, tree):
        # We must check if we've seen this variable
        ident = self.get_ident_name(tree)
        logger.trace(f"Checking whether identifier {ident} has been seen at tree {tree}")
        if ident not in self.idents:
            compile_error(f"Identifier {ident} has not been declared/assigned yet")


    def visit(self, tree):

        if not isinstance(tree, Tree):
            return tree

        # For class, flush class identifier list
        elif tree.data == "class":
            self.class_idents = set()
            self.class_idents_seen = set()
            self.idents = set()
            
            class_name = self.get_ident_name(tree.children[0])
            logger.trace(f"Class {class_name} has base ident set {self.idents}") 

            # Now visit class body
            self.visit(tree.children[-1])

            # Now make sure every identifier seen has been used
            logger.debug(f"Checking class field usage for clas {class_name} with detected field set {self.class_idents}") 
            for ident in self.class_idents_seen:
                if ident not in self.class_idents:
                    compile_error(f"Class field {ident} used before declaration somewhere")
            self.class_idents_seen = set()


        elif tree.data == "class_method":
            # First set constructor mode on/off
            if tree.children[0].children[0].value == "$constructor":
                self.constructor = True
            else:
                self.constructor = False

            # Add formal args to method set
            f_args = tree.children[1].children
            self.idents = set()
            for i in range(0, len(f_args), 2):
                self.idents.add(f_args[i].children[0].value)

            method_name = self.get_ident_name(tree.children[0])
            logger.trace(f"Method {method_name} has base ident set {self.idents}") 

            # Now visit method body
            self.visit(tree.children[-1])

        # For if statement, need to take the intersection of both branches
        elif tree.data == "if_structure":

            ident = self.idents.copy()
            class_idents = self.class_idents.copy()

            # First visit conditional
            self.visit(tree.children[0])

            # Then visit branch 1 and get identiifers
            self.visit(tree.children[1])
            ident_branch1 = self.idents.copy()
            class_idents1 = self.class_idents.copy()
            self.idents = class_idents
            self.idents = ident

            # Then visit branch 2 (if exists) and get identifiers
            if len(tree.children) > 2:
                self.visit(tree.children[2])
            ident_branch2 = self.idents.copy()
            class_idents2 = self.class_idents.copy()
            
            # Finally, take intersection
            logger.trace(f"branch1={ident_branch1} branch2={ident_branch2}")
            logger.trace(f"branch1={class_idents1} branch2={class_idents2}")
            self.idents = ident_branch1.intersection(ident_branch2)
            self.class_idents = class_idents1.intersection(class_idents2)

        # For while statement, just throw away any changes
        elif tree.data == "while_structure":

            ident = self.idents.copy()
            class_idents = self.class_idents.copy()

            # First visit conditional
            self.visit(tree.children[0])

            # Now visit child then reset idents
            self.visit(tree.children[1])
            self.idents = ident
            self.class_idents = class_idents

        else:
            # Default to super
            return super().visit(tree)

        return tree


def check(tree):
    logger.trace("Attempting to check identifier declaration consistency")
    iuc = IdentUsageCheck();
    iuc.visit(tree)
    logger.debug("Successfully checked identifier declaration consistency")

