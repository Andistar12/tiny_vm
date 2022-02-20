"""
Performs type inferencing on the given tree
Also performs type checking on conditionals to make sure they are Boolean
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper
import copy

from default_class_map import default_class_map

logger = logging.getLogger("type-inferencer")

# Default classes for certain tree nodes
tree_type_table = {
    "boolean_literal_false": "Boolean",
    "boolean_literal_true": "Boolean",
    "nothing_literal": "Nothing",
    "int_literal": "Int",
    "string_literal": "String",
    "cond_and": "Boolean",
    "cond_not": "Boolean",
    "cond_or": "Boolean",
    "this_ptr": "$"
}

def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

LATTICE_TOP = "$T" # Top of the lattice
LATTICE_BOTTOM = "$B" # Bottom of the lattice

class TypeInferencer(Visitor_Recursive):

    def __init__(self):
        self.changed = False
        self.curr_class = "" # Name of current class we are checking
        self.curr_method = "" # Name of current method we are checking
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
            # Check for default cases
            if ident.data == "this_ptr":
                return self.curr_class

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
                return self.class_map[clazz]["field_list"].get(name, LATTICE_BOTTOM)

            # Identifiers may be nested but will have a token eventually
            elif ident.data.startswith("identifier"):
                name = self.get_ident_name(ident.children[0])
                return self.class_map[self.curr_class]["method_locals"][self.curr_method].get(name, LATTICE_BOTTOM)

            elif ident.data == "method_invocation":
                # See what type the calling object is first
                clazz = self.infer_type(ident.children[1])
                # Look for return type of method
                method = self.get_ident_name(ident.children[0])
                if method not in self.class_map[clazz]["method_returns"]:
                    return LATTICE_BOTTOM
                    # compile_error(f"Attempted to get return type of unknown method {method} in class {clazz}")
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

    def set_ident_type(self, ident, new_type):
        # Sets the type of an identifier to the given type

        logger.trace(f"Setting type of {ident} to {new_type}")

        if new_type == LATTICE_TOP:
            compile_error(f"Attempted to set data type of field to LATTICE_TOP")
        if new_type == LATTICE_BOTTOM:
            compile_error(f"Attempted to set data type of field to LATTICE_BOTTOM")

        if ident.data.startswith("identifier_field"):
            if "this" in ident.data:
                clazz = self.curr_class
                name = self.get_ident_name(ident.children[0])
            else:
                clazz = self.infer_type(ident.children[0])
                name = self.get_ident_name(ident.children[1])
            if clazz not in self.class_map:
                compile_error(f"Attempted to get field from unknown class {clazz}")
            self.class_map[clazz]["field_list"][name] = new_type


        elif ident.data.startswith("identifier"):
            name = self.get_ident_name(ident.children[0])
            self.class_map[self.curr_class]["method_locals"][self.curr_method][name] = new_type
        else:
            compile_error(f"Attempted to set type to {new_type} of unknown tree {ident}")


    def if_structure(self, tree):
        # Check first child is actually a conditional (subclass of Boolean)
        clazz = self.infer_type(tree.children[0])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("If conditional does not have Boolean value")
        return tree

    def while_structure(self, tree):
        # Check first child is actually a conditional (subclass of Boolean)
        clazz = self.infer_type(tree.children[0])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("While conditional does not have Boolean value")
        return tree

    def cond_and(self, tree):
        # Check both children are actually booleans
        clazz = self.infer_type(tree.children[0])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("And expression does not have Boolean value")
        clazz = self.infer_type(tree.children[1])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("And expression does not have Boolean value")
        return tree

    def cond_or(self, tree):
        # Check both children are actually booleans
        clazz = self.infer_type(tree.children[0])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("Or expression does not have Boolean value")
        clazz = self.infer_type(tree.children[1])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("Or expression does not have Boolean value")
        return tree
   
    def cond_not(self, tree):
        # Check child is actually boolean
        clazz = self.infer_type(tree.children[0])
        if self.lca(clazz, "Boolean") != "Boolean":
            compile_error("Not expression does not have Boolean value")
        return tree

    def assignment(self, tree):

        # Get identifier name
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Attempting to infer type of {ident} in tree {tree}")

        # Get current type of left hand side
        prev_type = self.infer_type(tree.children[0])

        # See what the new type is
        new_type = self.infer_type(tree.children[1])

        # Resolve with LCA
        curr_type = self.lca(prev_type, new_type)
        if curr_type != prev_type:
            self.set_ident_type(tree.children[0], curr_type)
            self.changed = True
        logger.debug(f"Previously {ident} was {prev_type}, now is {new_type}, resolving as {curr_type}")
        return tree

    def assignment_decl(self, tree):
        # Similar to assignment, but we also then remove the explicit declaration 
        # and transform it into a regular assignment node

        # Get identifier name
        ident = self.get_ident_name(tree.children[0])
        logger.trace(f"Attempting to infer type of {ident} in tree {tree}")

        # See what it currently is, or default to bottom of lattice
        prev_type = self.infer_type(tree.children[0])

        # See what its declared type is
        decl_type = self.get_ident_name(tree.children[1])
    
        # Resolve with LCA
        curr_type = self.lca(prev_type, decl_type)
        if curr_type != prev_type:
            self.set_ident_type(tree.children[0], curr_type)
            self.changed = True
        logger.debug(f"Previously {ident} was {prev_type}, declared as {decl_type}, resolving as {curr_type}")

        # Transform then defer to assignment
        tree.data = "assignment"
        tree.children = [tree.children[0], tree.children[2]]
        return self.assignment(tree)

    def clazz(self, tree):
        self.curr_class = self.get_ident_name(tree.children[0])
        superclass = self.get_ident_name(tree.children[1])

        if superclass not in self.class_map:
            compile_error(f"Class {self.curr_class} inherits from unknown superclass {superclass}")

        if self.curr_class not in self.class_map:
            # First time seeing it, add to class hierarchy
            cm = copy.deepcopy(self.class_map[superclass])
            cm["superclass"] = superclass
            cm["method_locals"] = {}
            self.class_map[self.curr_class] = cm

        return tree

    def class_method(self, tree):
        # Add return type
        method_name = self.get_ident_name(tree.children[0])
        method_return = self.get_ident_name(tree.children[2])
        self.curr_method = method_name
        self.class_map[self.curr_class]["method_returns"][method_name] = method_return

        # Add formal arguments to local scope
        if self.curr_method not in self.class_map[self.curr_class]["method_locals"]:
            # First time seeing method, add to hierarchy
            local = {}
            args = []
            arg_names = []
            for i in range(0, len(tree.children[1].children), 2):
                name = self.get_ident_name(tree.children[1].children[i])
                clazz = self.get_ident_name(tree.children[1].children[i+1])
                local[name] = clazz
                args.append(clazz)
                arg_names.append(name)
            self.class_map[self.curr_class]["method_locals"][self.curr_method] = local
            self.class_map[self.curr_class]["method_args"][self.curr_method] = args
            self.class_map[self.curr_class]["method_arg_names"][self.curr_method] = arg_names

        logger.trace(f"Local scope for class {self.curr_class} method {method_name} is now {self.class_map[self.curr_class]['method_locals'][self.curr_method]}")
        return tree

    def visit(self, tree):
        if tree.data == "clazz":
            # Pre-order traversal
            tree = self.clazz(tree)
            self.visit(tree.children[2])

        elif tree.data == "class_method":
            # Complicated traversal
            # First do pre-order
            tree = self.class_method(tree)

            # Then visit children
            self.visit(tree.children[-1])

            # Then check formal arguments
            for i in range(0, len(tree.children[1].children), 2):
                name = self.get_ident_name(tree.children[1].children[i])
                decl_clazz = self.get_ident_name(tree.children[1].children[i+1])

                inferred_type = self.class_map[self.curr_class]["method_locals"][self.curr_method][name]
                if inferred_type != decl_clazz: 
                    compile_error(f"Formal argument {name} was declared {decl_clazz} but has inferred type {inferred_type}")

        else:
            return super().visit(tree)

        return tree

def infer(tree):
    # Performs type inferencing on the tree
    logger.trace("Attempting to perform type inferencing")
    i = TypeInferencer();
    i.changed = True
    while i.changed:
        i.changed = False
        i.visit(tree)

    logger.trace(f"Successfully performed type inferencing. Got {i.class_map}")

    return i.class_map


if __name__ == "__main__":
    # Test the type inference LCA algorithm
    ty = TypeInference()
    print(f"Expect Obj, got {ty.lca('Obj', 'Obj')}")
    print(f"Expect Obj, got {ty.lca('Int', 'Obj')}")
    print(f"Expect Int, got {ty.lca('Int', 'Int')}")
    print(f"Expect Int, got {ty.lca('Int', LATTICE_BOTTOM)}")
    print(f"Expect {LATTICE_TOP}, got {ty.lca('Int', LATTICE_TOP)}")
