"""
Performs type inferencing on the given tree
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

from default_class_map import default_class_map

logger = logging.getLogger("type-inferencer")


def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

LATTICE_TOP = "$T" # Top of the lattice
LATTICE_BOTTOM = "$B" # Bottom of the lattice

class TypeInferencer(Visitor_Recursive):

    def __init__(self):
        self.idents = {}
        self.changed = False
        self.class_map = default_class_map

    def lca(self, clazz1, clazz2):
        # Least common ancestor algorithm
        logger.trace(f"Performing lca algorithm with operands {clazz1} {clazz2}")

        # Checks for top/bottom of lattice
        if clazz1 == LATTICE_TOP or clazz2 == LATTICE_TOP:
            return LATTICE_TOP
        if clazz1 == LATTICE_BOTTOM:
            return clazz2
        if clazz2 == LATTICE_BOTTOM:
            return clazz1

        # Do actual LCA algorithm by comparing superclass lineage
        clazz1_lineage = []
        clazz2_lineage = []
        c = clazz1
        while c != "$":
            clazz1_lineage.insert(0, c)
            c = self.class_map[c]["superclass"]
        c = clazz2
        while c != "$":
            clazz2_lineage.insert(0, c)
            c = self.class_map[c]["superclass"]

        if clazz1_lineage[0] != clazz2_lineage[0]:
            # No match found, return type error
            return LATTICE_TOP
        
        i = 0
        while i < len(clazz1_lineage) and i < len(clazz2_lineage) and clazz1_lineage[i] == clazz2_lineage[i]:
            i += 1

        return clazz1_lineage[i-1]


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
                return self.idents.get(ident.children[0].value, LATTICE_BOTTOM)
            elif ident.data.startswith("identifier"):
                # Nested "identifier" tree nodes
                return self.infer_type(ident.children[0])

            elif ident.data == "method_invocation":
                # See what type the calling object is first
                clazz = self.infer_type(ident.children[1])
                # Look for return type of method
                method = self.get_ident_name(ident.children[0])
                if method not in self.class_map[clazz]["method_returns"]:
                    compile_error(f("Attempted to get return type of unknown method {method} in class {clazz}"))
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

    def assignment(self, tree):
        # Get identifier name
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Attempting to infer type of {ident} in tree {tree}")

        # See what it currently is, or default to bottom of lattice
        prev_type = self.idents.get(ident, LATTICE_BOTTOM)
        
        # See what the new type is
        new_type = self.infer_type(tree.children[1])

        # Resolve with LCA
        curr_type = self.lca(prev_type, new_type)
        if curr_type != prev_type:
            self.idents[ident] = curr_type
            self.changed = True
        logger.debug(f"Previously {ident} was {prev_type}, now is {new_type}, resolving as {curr_type}")
        return tree

    def assignment_decl(self, tree):
        # Similar to assignment, but we also then remove the explicit declaration

        # Get identifier name
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Attempting to infer type of {ident} in tree {tree}")

        # See what it currently is, or default to bottom of lattice
        prev_type = self.idents.get(ident, LATTICE_BOTTOM)

        # See what its declared type is
        decl_type = self.get_ident_name(tree.children[1])
    
        # Resolve with LCA
        curr_type = self.lca(prev_type, decl_type)
        if curr_type != prev_type:
            self.idents[ident] = curr_type
            self.changed = True
        self.idents[ident] = curr_type
        logger.debug(f"Previously {ident} was {prev_type}, declared as {decl_type}, resolving as {curr_type}")

        # Transform then defer to assignment
        tree.data = "assignment"
        tree.children = [tree.children[0], tree.children[2]]
        return self.assignment(tree)
        

def infer(tree):
    # Performs type inferencing on the tree
    logger.trace("Attempting to perform type inferencing")
    i = TypeInferencer();
    i.changed = True
    while i.changed:
        i.changed = False
        i.visit(tree)

    logger.trace("Successfully performed type inferencing. Got {i.idents}")
    return i.idents


if __name__ == "__main__":
    # Test the type inference LCA algorithm
    ty = TypeInference()
    print(f"Expect Obj, got {ty.lca('Obj', 'Obj')}")
    print(f"Expect Obj, got {ty.lca('Int', 'Obj')}")
    print(f"Expect Int, got {ty.lca('Int', 'Int')}")
    print(f"Expect Int, got {ty.lca('Int', LATTICE_BOTTOM)}")
    print(f"Expect {LATTICE_TOP}, got {ty.lca('Int', LATTICE_TOP)}")
