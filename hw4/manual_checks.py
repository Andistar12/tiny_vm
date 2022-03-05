"""
Static semantic
Manual checks including
 - No loops in class hierarchy
 - Class redefinition
 - Method redefinition
 - Variable or method name that matches class
 - Method invocation argument length match
 - Check return type within method is subclass of declared return type 

Covariance/contravariance checks for method overriding happen in type_inf
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

from default_class_map import default_class_map
from type_inf import LATTICE_TOP, LATTICE_BOTTOM, tree_type_table

logger = logging.getLogger("manual-checks")



def compile_error(msg):
    # Caught some compile-time error
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

def cycle_check(classes):
    """
    Checks for cycle in clazzes, which is a list of (class, superclass)
    Based on union find algorithm
    """
    sc = {}
    for clazz, superclass in classes:
        class_set = sc.get(clazz, clazz)

        superclass_set = sc.get(superclass, superclass)

        if class_set != superclass_set:
            # They belong to different sets. Merge disjoint set

            for c in sc:
                if sc[c] == class_set:
                    sc[c] = superclass_set
            sc[superclass] = superclass_set
            sc[clazz] = superclass_set
        else:
            # Part of same set. Cycle found!
            return True

    return False
        

class ManualChecks(Visitor_Recursive):

    def __init__(self, class_map=default_class_map):
        self.class_map = class_map
        self.uniq_classes = set()
        self.uniq_methods = set()

        # Check no cycles in class graph
        classes = [(x, self.class_map[x]["superclass"]) for x in class_map]
        logger.trace(f"Performing cycle check with class hierarchy {classes}")
        if cycle_check(classes):
            compile_error(f"Cycle detected in the class hierarchy!")
        logger.debug("Cycle detection completed with no errors")

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
            if c not in self.class_map:
                compile_error(f"Cannot find class {c}")
            c = self.class_map[c]["superclass"]
        c = clazz2
        while c != "$":
            clazz2_lineage.insert(0, c)
            if c not in self.class_map:
                compile_error(f"Cannot find class {c}")
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
                    name = self.get_ident_name(ident.children[0])
                else:
                    clazz = self.infer_type(ident.children[0])
                    name = self.get_ident_name(ident.children[1])
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
                    compile_error(f"Attempted to get return type of unknown method {method} in class {clazz}")
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

    def identifier_lhand(self, tree):
        logger.trace(f"Checking if ident does not clash with existing class for tree {tree}")
        ident = self.get_ident_name(tree)
        if ident in self.uniq_classes:
            compile_error(f"Identifier {ident} has clashing name with existing class")

    def identifier_field_lhand(self, tree):
        self.identifier_lhand(tree) 

    def identifier_field_lhand_this(self, tree):
        self.identifier_lhand(tree)

    def identifier_rhand(self, tree):
        self.identifier_lhand(tree)

    def identifier_field_rhand(self, tree):
        self.identifier_lhand(tree)

    def identifier_field_rhand_this(self, tree):
        self.identifier_lhand(tree)

    def method_invocation(self, tree):
        method = self.get_ident_name(tree.children[0])
        logger.trace(f"Checking method invocation of {method} in {self.curr_method} of {self.curr_class}")
        logger.trace(f"{tree}")
        clazz = self.infer_type(tree.children[1])
        given_args = tree.children[2:]
        if len(given_args) > 0 and given_args[0].data == "method_args":
            # Look at children
            given_args = given_args[0].children
        method_args = self.class_map[clazz]["method_args"][method]

        if len(given_args) != len(method_args):
            compile_error(f"Method invocation of {method} within class method {self.curr_method} of {self.curr_class} has mismatched arg count. Expected {len(method_args)} got {len(given_args)}")

        for i, child in enumerate(given_args):
            decl_type = self.class_map[clazz]["method_args"][method][i]
            infr_type = self.infer_type(child)

            if self.lca(decl_type, infr_type) != decl_type:
                compile_error(f"Method invocation of {method} within class method {self.curr_method} of {self.curr_class} has unexpected type for arg {i}, expected {decl_type} got {infr_type}")

    def return_statement(self, tree):
        logger.trace(f"Checking return statement {self.curr_method} of {self.curr_class}")
        decl_type = self.class_map[self.curr_class]["method_returns"][self.curr_method]
        infr_type = self.infer_type(tree.children[0])

        if self.lca(decl_type, infr_type) != decl_type:
            compile_error(f"Method return within class method {self.curr_method} of {self.curr_class} has unexpected type, expected {decl_type} got {infr_type}")

    def class_method(self, tree):
        method = self.get_ident_name(tree.children[0])
        logger.trace(f"Checking method redefinition of {method} of {self.curr_class}")
        if method in self.uniq_methods:
            compile_error(f"Detected redefinition of method {method} in class {self.curr_class}")
        if method == self.curr_class:
            compile_error(f"Method {method} has identical name as its class")
        self.uniq_methods.add(method)
        self.curr_method = method
        return tree

    def clazz(self, tree):
        clazz = self.get_ident_name(tree.children[0])
        logger.trace(f"Checking class redefinition of {clazz}")
        if clazz in self.uniq_classes:
            compile_error(f"Detected redefinition of class {clazz}")
        self.uniq_classes.add(clazz)
        self.curr_class = clazz
        self.uniq_methods = set()
        return tree


    def visit(self, tree):

        if not isinstance(tree, Tree):
            return tree

        # For class and class method, preorder traversal
        elif tree.data == "clazz":
            
            self.clazz(tree)
            self.visit(tree.children[2])

        elif tree.data == "class_method":
   
            self.class_method(tree)
            for child in tree.children:
                self.visit(child)

        else:
            # Default to super
            return super().visit(tree)

        return tree


def check(tree, class_map):
    logger.trace("Attempting to perform final tree and class hierarchy validation")
    mc = ManualChecks(class_map);
    mc.visit(tree)
    logger.debug("Successfully checked tree and class hierarchy")


if __name__ == "__main__":
    set1 = [("class1", "class2"), ("class2", "class3"), ("class3", "class4")]
    print(set1)
    print(cycle_check(set1))

    set2 = [("class1", "class2"), ("class2", "class3"), ("class3", "class4"), ("class4", "class1")]
    print(set2)
    print(cycle_check(set2))

