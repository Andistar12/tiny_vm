"""
Handles parsing the language. ASM code generation is in code_gen.py
"""

from lark import Lark, v_args, Tree, Token
from lark.visitors import Visitor_Recursive
import sys
import logging
import log_helper

logger = logging.getLogger("parser")

def compile_error(msg):
    logger.fatal(f"COMPILE ERROR: {msg}")
    sys.exit(1)

# The quack grammar for lexical and syntactic analysis
quack_grammar = """
?start: program

// Definition of a program: a bunch of statements
?program: statement*                                -> program
    
// Definition of a statement: an expression or variable assignment
?statement: r_expr ";"                              -> statement
    | l_expr (":" CNAME)? "=" r_expr ";"            -> assignment

// Definition of a left-hand expression: identifier, or object.identifier
?l_expr: identifier                                 -> identifier_lhand
// TODO add object field for l_expr

// Definition of an identifier: non digit character followed by alphanumeric
?identifier: ["_" | LETTER] CNAME*                  -> identifier

// Definition of a right-hand expression: an identifier, literal, binary operator, or method invocation
// Arranged to handle precedence

?r_expr: r_expr_prod
    | r_expr "+" r_expr_prod                        -> method_add
    | r_expr "-" r_expr_prod                        -> method_sub
    | r_expr "." method_name "(" method_args? ")"   -> method_invocation

?r_expr_prod: r_expr_atom
    | r_expr_prod "*" r_expr_atom                   -> method_mul
    | r_expr_prod "/" r_expr_atom                   -> method_div

?r_expr_atom: l_expr                                -> identifier_rhand
    | ESCAPED_STRING                                -> string_literal
    | LONG_STRING                                   -> string_literal
    | INT                                           -> int_literal
    | "true"                                        -> boolean_literal_true
    | "false"                                       -> boolean_literal_false
    | "none"                                        -> nothing_literal
    | "-" r_expr_atom                               -> method_neg
    | "(" r_expr ")"                                -> identifier_rhand

    
?method_name: identifier                            -> identifier_method
?method_args: r_expr ("," r_expr)*                  -> method_args

// Useful provided defaults
%import common.INT
%import common.ESCAPED_STRING
%import common.WORD
%import common.LETTER
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

def parse(prgm_text):
    # Lexes and parses the prgm

    logger = logging.getLogger("quack-parser")

    # Lex the program
    logger.debug("Attempting to parse the grammer")
    quack_lexer = Lark(quack_grammar, parser="lalr")
    logger.debug("Atetmpting to generate the tree")
    tree = quack_lexer.parse(prgm_text)
    logger.debug("Successfully generated the AST")

    return tree

