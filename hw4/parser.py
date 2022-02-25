"""
Handles parsing the language and perform tree transformation cleanup
"""

from lark import Lark, v_args, Tree, Token, tree as lark_tree
from lark.visitors import Transformer
import sys
import logging
import log_helper

logger = logging.getLogger("quack-parser")

def compile_error(msg):
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

# The quack grammar for lexical and syntactic analysis
quack_grammar = """
?start: program

// Definition of a program: classes then a bunch of statements
?program: clazz* statement*                         -> program

// Definition of a class: see manual
?clazz: "class" identifier "(" formal_args? ")" ("extends" identifier)? class_body              -> clazz

// Formal arguments
?formal_args: identifier ":" identifier ("," identifier ":" identifier)*                        -> formal_args

?formal_arg: identifier 

// Class body: statements then methods
?class_body: "{" statement* class_method* "}"       -> class_body

?class_method: "def" identifier "(" formal_args? ")" (":" identifier)? statement_block          -> class_method

// Definition of a statement: an expression or variable assignment or control structure
?statement: c_expr ";"                              -> statement
    | l_expr "=" c_expr ";"                         -> assignment
    | l_expr ":" identifier "=" c_expr ";"          -> assignment_decl

    // We do this mess to desugar it later
    | "if" c_expr statement_block ("elif" c_expr statement_block)* ("else" statement_block)?    -> if_structure
    
    | "while" c_expr statement_block                -> while_structure
    | "return" (c_expr)? ";"                        -> return_statement
    | "typecase" c_expr "{" (type_alt)* "}"         -> typecase_statement

// Type alternative: for typecase
?type_alt: identifier ":" identifier statement_block -> type_alt

// Statement block: curly brace of statements
?statement_block: "{" statement* "}"                -> statement_block

// Definition of a left-hand expression: identifier, or object.identifier
?l_expr: identifier                                 -> identifier_lhand
    | "this" "." identifier                         -> identifier_field_lhand_this
    | r_expr_access "." identifier                  -> identifier_field_lhand

// Definition of an identifier: non digit character followed by alphanumeric
?identifier: CNAME                                  -> identifier


// Define special type to handle short circuiting, at lowest precedence
?c_expr: cc_expr
    | c_expr "and" cc_expr                           -> cond_and
    | c_expr "or" cc_expr                            -> cond_or

// Define comparison operations at very low priority
?cc_expr: r_expr
    | cc_expr "==" r_expr                            -> method_eq
    | cc_expr "<=" r_expr                            -> method_leq
    | cc_expr ">=" r_expr                            -> method_geq
    | cc_expr "<" r_expr                             -> method_lt
    | cc_expr ">" r_expr                             -> method_gt

// Definition of a right-hand expression: an identifier, literal, binary operator, or method invocation
// Arranged to handle arithmetic precedence
?r_expr: r_expr_prod
    | r_expr "+" r_expr_prod                        -> method_add
    | r_expr "-" r_expr_prod                        -> method_sub

// Mult/div is higher precedence than add and sub
?r_expr_prod: r_expr_access
    | r_expr_prod "*" r_expr_access                 -> method_mul
    | r_expr_prod "/" r_expr_access                 -> method_div

// Method/field is next precedence
// Redundant with l_expr, but simplifies code generation by labeling tree differently
?r_expr_access: r_expr_unary
    | r_expr_access "." method_name "(" method_args? ")"   -> method_invocation
    | "this" "." identifier                         -> identifier_field_rhand_this
    | "this" "." method_name "(" method_args? ")"   -> method_invocation_self
    | r_expr_access "." identifier                    -> identifier_field_rhand

// Unary operations
?r_expr_unary: r_expr_atom
    | "-" c_expr                                    -> method_neg
    | "not" c_expr                                  -> cond_not

// Smallest possible unit (ignoring recursion)
?r_expr_atom: "(" c_expr ")"
    | identifier "(" method_args ")"                -> obj_instantiation
    | ESCAPED_STRING                                -> string_literal
    | LONG_STRING                                   -> longstring_literal
    | INT                                           -> int_literal
    | "true"                                        -> boolean_literal_true
    | "false"                                       -> boolean_literal_false
    | "none"                                        -> nothing_literal
    | "this"                                        -> this_ptr
    | identifier                                    -> identifier_rhand

// Method name and arguments
?method_name: identifier                            -> identifier_method
?method_args: c_expr ("," c_expr)*                  -> method_args

// Useful provided defaults
%import common.INT
%import common.ESCAPED_STRING
%import common.CNAME
%import python.LONG_STRING

// Ignore whitespace
%import common.WS_INLINE
%import common.WS
%ignore WS
%ignore WS_INLINE

// Ignore comments
%import common.C_COMMENT
%import common.CPP_COMMENT
%ignore C_COMMENT
%ignore CPP_COMMENT
"""

@v_args(tree=True)
class MethodInvokeCleanup(Transformer):
    # Desugars method invocations

    def method_invocation(self, tree):
        logger.trace("Transforming method_invocation by swapping receiving object and method identifier")
        tree.children[0], tree.children[1] = tree.children[1], tree.children[0]
        return tree

    def method_invocation_self(self, tree):
        logger.trace("Transforming method_invocation_self adding this pointer as receiving object")
        tree.children.insert(1, Tree("this_ptr", []))
        tree.data = "method_invocation"
        return tree

    def method_add(self, tree):
        logger.trace("Desugaring method_add into invocation of plus")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "plus"))
        return tree

    def method_sub(self, tree):
        logger.trace("Desugaring method_sub into invocation of minus")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "minus"))
        return tree

    def method_mul(self, tree):
        logger.trace("Desugaring method_mul into invocation of times")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "times"))
        return tree

    def method_div(self, tree):
        logger.trace("Desugaring method_div into invocation of divide")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "divide"))
        return tree

    def method_neg(self, tree):
        logger.trace("Desugaring method_neg into invocation of negate")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "negate"))
        return tree

    def method_eq(self, tree):
        logger.trace("Desugaring method_eq into invocation of equals")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "equals"))
        return tree

    def method_leq(self, tree):
        logger.trace("Desugaring method_leq into invocation of atmost")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "atmost"))
        return tree

    def method_geq(self, tree):
        logger.trace("Desugaring method_geq into invocation of atleast")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "atleast"))
        return tree

    def method_lt(self, tree):
        logger.trace("Desugaring method_geq into invocation of less")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "less"))
        return tree

    def method_gt(self, tree):
        logger.trace("Desugaring method_gt into invocation of more")
        tree.data = "method_invocation"
        tree.children.insert(0, Token("CNAME", "more"))
        return tree


@v_args(tree=True)
class IdentifierCleanup(Transformer):
    # Cleans up the nested identifier mess created by the grammar

    def identifier_rhand(self, tree):
        logger.trace("Replacing identifier_rhand with identifier token")
        tree.children[0] = tree.children[0].children[0]
        return tree

    def identifier_method(self, tree):
        logger.trace("Replacing identifier_method with identifier token")
        return tree.children[0]

    def identifier_field_rhand_this(self, tree):
        logger.trace("Replacing identifier_field_rhand_this with identifier token")
        tree.children[0] = tree.children[0].children[0]
        return tree

    def identifier_field_lhand_this(self, tree):
        logger.trace("Replacing identifier_field_lhand_this with identifier token")
        tree.children[0] = tree.children[0].children[0]
        return tree


@v_args(tree=True)
class StringLiteralCleanup(Transformer):
    # Fixes string literals to be escaped onto one line

    def longstring_literal(self, tree):
        logger.trace("Desugaring longstring_literal into string_literal")

        tree.data = "string_literal"

        # Remove surrounding quotes
        s = tree.children[0].value
        if s.startswith("\"\"\"") or s.startswith("'''"):
            s = s[3:-3]
        if s.startswith("\""):
            s = s[1:-1]

        # Unescaping this string was difficult, I tried re.escape(s), 
        # s.encode(unicode_escape), ast.literal_eval(s), r({}).format(s)
        # TODO there has to be a cleaner way to encode string literals
        s = "\"" + repr(s)[1:-1] + "\""
        tree.children[0].value = s
        return tree        

@v_args(tree=True)
class IfStatementCleanup(Transformer):
    # Converts if-elif-else statements into nested if-else statements

    def if_structure(self, tree):
        logger.trace(f"Desugaring if-elif-else into nested if-else statements {tree}")

        # Get what's part of this if statement
        cond, true_branch = tree.children[0], tree.children[1]

        # See whether there's an else branch
        else_branch = None
        if len(tree.children) % 2 != 0:
            else_branch = tree.children[-1]
            tree.children.pop()

        # Collect all elif branches (c_expr, statement_block)
        elif_branches = [(tree.children[i], tree.children[i+1]) for i in range(2, len(tree.children), 2)]

        # Generate nested if else statements
        nested_ifs = else_branch
        for elif_branch in reversed(elif_branches):
            if nested_ifs == None:
                # Init if tree with just one branch
                nested_ifs = Tree("if_structure", [elif_branch[0], elif_branch[1]])
            else:
                # Otherwise nest a tree 
                nested_ifs = Tree("if_structure", [elif_branch[0], elif_branch[1], nested_ifs])

        # Remake tree using nested ifs as else branch
        tree.children = [cond, true_branch]
        if nested_ifs != None:
            tree.children.append(nested_ifs)
        return tree

@v_args(tree=True)
class LooseStatementCleanup(Transformer):
    # Puts the "class-less" statements into their own class

    def __init__(self, main_class):
        self.main_class = main_class

    def program(self, tree):
        logger.trace(f"Desugaring loose statements into new class {self.main_class}")

        # Get classes and statements
        clazzes = []
        statements = []
        for item in tree.children:
            if item.data == "clazz":
                clazzes.append(item)
            else:
                statements.append(item)

        # Create new class
        clazz_body = Tree("class_body", statements)
        clazzes.append(Tree("clazz", [Tree("identifier", [Token("CNAME", self.main_class)]), clazz_body]))

        # Add it to the tree
        tree.children = clazzes
        return tree

@v_args(tree=True)
class ConstructorCleanup(Transformer):
    # Makes a class_method for class constructors
    # Also guarantees every class has an explicit superclass node, use "Obj" if not present
    # And every method has a formal argument list

    def clazz(self, tree):
        clazz_name = tree.children[0].children[0].value
        logger.trace(f"Desugaring loose constructor statements into new method $constructor for {clazz_name}")

        # Separate class methods from constructor statements
        class_methods = []
        constructor_statements = []
        for item in tree.children[-1].children:
            if item.data == "class_method":
                if item.children[1].data != "formal_args":
                    item.children.insert(1, Tree("formal_args", []))
                class_methods.append(item)
            else:
                constructor_statements.append(item)

        # Make the constructor method
        constructor_args = tree.children[1]
        if constructor_args.data != "formal_args":
            constructor_args = Tree("formal_args", [])
        else:
            tree.children.pop(1)
        constructor_method = Tree("class_method", [
            Tree("identifier", [Token("CNAME", "$constructor")]),
            constructor_args, 
            Tree("identifier", [Token("CNAME", clazz_name)]), # Return type
            Tree("statement_block", constructor_statements)
        ])

        # Add constructor
        class_methods.insert(0, constructor_method)
        tree.children[-1].children = class_methods

        # Add superclass
        if tree.children[1].data != "identifier":
            # Need to explicitly add class, use Obj
            tree.children.insert(1, Tree("identifier", [Token("CNAME", "Obj")]))
        return tree

@v_args(tree=True)
class MethodReturnCleanup(Transformer):
    # Adds a blank return statement at the end of every class method, if one is not present
    # For the constructor, it will simply "return this"
    # Also replaces blank returns with "return none"

    def class_method(self, tree):
        method_name = tree.children[0].children[0].value
        method_statements = tree.children[-1].children

        # TODO bug involving if statements with returns on every branch
        if len(method_statements) == 0 or method_statements[-1].data != "return_statement":
            logger.trace(f"Adding return statement to end of method {method_name}")
            node = Tree("return_statement", [Tree("nothing_literal", [])])

            # If constructor, return "this" instead of something else
            if method_name == "$constructor":
                node.children[0].data = "this_ptr"
            
            method_statements.append(node)
        return tree

    def return_statement(self, tree):
        if len(tree.children) == 0:
            logger.trace("Desugaring blank return to return none")
            tree.children.append(Tree("nothing_literal", []))
        return tree
            

def visualize(tree, filename):
    # Visualizes a tree as a PNG stored at filename

    logger = logging.getLogger("quack-parser")

    try:
        logger.trace("Attempting to visualize tree")
        lark_tree.pydot__tree_to_png(tree, filename)
    except Exception as e:
        logger.warn("Failed to visualize tree", e)


def parse(prgm_text, main_class="Main"):
    # Lexes and parses the prgm

    logger = logging.getLogger("quack-parser")

    # Lex the program
    logger.debug("Attempting to parse the grammer")
    quack_lexer = Lark(quack_grammar, parser="lalr")
    logger.debug("Atetmpting to generate the tree")
    tree = quack_lexer.parse(prgm_text)
    logger.debug("Successfully generated the AST")

    # Cleanup the tree
    logger.debug("Attempting to transform the tree")
    tree = IfStatementCleanup().transform(tree) # Turn elif into nested ifs
    tree = MethodInvokeCleanup().transform(tree) # Desugar binary ops +-*/ to method invocation
    tree = StringLiteralCleanup().transform(tree) # Convert """ literals to "
    tree = IdentifierCleanup().transform(tree) # Cleanup identifier mess grammar creates
    tree = LooseStatementCleanup(main_class).transform(tree) # Move classless statements into their own class
    tree = ConstructorCleanup().transform(tree) # Add tree node for constructor method
    tree = MethodReturnCleanup().transform(tree) # Make every method end with return statement
    logger.trace(f"Transformed tree: {tree}")
    logger.debug("Successfully transformed the tree")

    return tree

