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

// Definition of a program: a bunch of statements
?program: statement*                                -> program

// Definition of a statement: an expression or variable assignment or control structure
?statement: c_expr ";"                              -> statement
    | l_expr "=" c_expr ";"       -> assignment
    | l_expr ":" identifier "=" c_expr ";"          -> assignment_decl
    // We do this mess to desugar it later
    | "if" c_expr statement_block ("elif" c_expr statement_block)* ("else" statement_block)?        -> if_structure
    | "while" c_expr statement_block                -> while_structure

// Statement block: curly brace of statements
?statement_block: "{" statement* "}"                -> statement_block

// Definition of a left-hand expression: identifier, or object.identifier
?l_expr: identifier                                 -> identifier_lhand
// TODO add object field for l_expr

// Definition of an identifier: non digit character followed by alphanumeric
?identifier: CNAME                                  -> identifier


// Define special type to handle short circuiting, at highest precedence
?c_expr: cc_expr
    | c_expr "and" cc_expr                           -> cond_and
    | c_expr "or" cc_expr                            -> cond_or

// Define comparison operations at very high precedence
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
    | r_expr "." method_name "(" method_args? ")"   -> method_invocation

?r_expr_prod: r_expr_atom
    | r_expr_prod "*" r_expr_atom                   -> method_mul
    | r_expr_prod "/" r_expr_atom                   -> method_div

?r_expr_atom: l_expr                                -> identifier_rhand
    | ESCAPED_STRING                                -> string_literal
    | LONG_STRING                                   -> longstring_literal
    | INT                                           -> int_literal
    | "true"                                        -> boolean_literal_true
    | "false"                                       -> boolean_literal_false
    | "none"                                        -> nothing_literal
    | "-" c_expr                                    -> method_neg
    | "not" c_expr                                  -> cond_not
    | "(" c_expr ")"


?method_name: identifier                            -> identifier_method
?method_args: r_expr ("," r_expr)*                  -> method_args

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
        logger.trace("Transforming method_invocation by swapping calling object and method identifier")
        tree.children[0], tree.children[1] = tree.children[1], tree.children[0]
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
        logger.trace("Replacing identifier_rhand with identifier")
        tree.children[0] = tree.children[0].children[0]
        return tree

    def identifier_method(self, tree):
        logger.trace("Replacing identifier_method with identifier")
        return tree.children[0]


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


def visualize(tree, filename):
    # Visualizes a tree as a PNG stored at filename

    logger = logging.getLogger("quack-parser")

    try:
        logger.trace("Attempting to visualize tree")
        lark_tree.pydot__tree_to_png(tree, filename)
    except Exception as e:
        logger.warn("Failed to visualize tree", e)


def parse(prgm_text):
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
    tree = IfStatementCleanup().transform(tree)
    tree = MethodInvokeCleanup().transform(tree)
    tree = StringLiteralCleanup().transform(tree)
    tree = IdentifierCleanup().transform(tree)
    logger.trace(f"Transformed tree: {tree}")
    logger.debug("Successfully transformed the tree")

    return tree

