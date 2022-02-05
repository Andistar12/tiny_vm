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
        self.idents = set()

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
            compile_error(f"Attempted to get identifier name in unrecognizable tree {ident}")


    def identifier_lhand(self, tree):
        # We have now seen this variable, keep track of it
        ident = self.get_ident_name(tree)
        logger.trace(f"Logging identifier {ident} as seen from tree {tree}")
        self.idents.add(ident)

    def identifier_rhand(self, tree):
        # We must check if we've seen this variable
        ident = self.get_ident_name(tree)
        logger.trace(f"Checking whether identifier {ident} has been seen at tree {tree}")
        if ident not in self.idents:
            compile_error(f"Identifier {ident} has not been declared/assigned yet")


    def visit(self, tree):

        if not isinstance(tree, Tree):
            return tree

        # For if statement, need to take the intersection of both branches
        elif tree.data == "if_structure":

            ident = self.idents.copy()

            # First visit conditional
            self.visit(tree.children[0])

            # Then visit branch 1 and get identiifers
            self.visit(tree.children[1])
            ident_branch1 = self.idents.copy()
            self.idents = ident

            # Then visit branch 2 (if exists) and get identifiers
            if len(tree.children) > 2:
                self.visit(tree.children[2])
            ident_branch2 = self.idents.copy()
            
            # Finally, take intersection
            logger.trace(f"branch1={ident_branch1} branch2={ident_branch2}")
            self.idents = ident_branch1.intersection(ident_branch2)

        # For while statement, just throw away any changes
        elif tree.data == "while_structure":

            ident = self.idents.copy()

            # First visit conditional
            self.visit(tree.children[0])

            # Now visit child then reset idents
            self.visit(tree.children[1])
            self.idents = ident

        else:
            # Default to super
            return super().visit(tree)

        return tree


def check(tree):
    logger.trace("Attempting to check identifier declaration consistency")
    iuc = IdentUsageCheck();
    iuc.visit(tree)
    logger.debug("Successfully checked identifier declaration consistency")

