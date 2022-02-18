# Project discussion

I do custom tree traversal on each node (in code_gen.py). This made way more sense to me than having custom nodes, as vast majority of nodes work just fine using post-order traversal (the default for `Visitor_Recursive`).

Logic for the `not` operator is kinda wack, I ended up making a new native method for negation if we aren't in a conditional.

In code_gen.py, I have program-wide flags `sc_true` and `sc_false` representing branches to jump to in the event of a short circuit. These are set by if and while loop structures. If they are not set then we are not in a conditional, and the and/or logic will auto generate their own branches to jump to in lieu. Otherwise, the code generation is always the same.

Elif statements are desugared into nested if/else statements (this happens in parser.py) although in code_gen.py I still have logic to check whether an else branch is present or not before generating anything.

# File walkthrough (in execution order)

* compiler.py: Entrypoint for compiler, handles CLI args and file I/O
* log_helper.py: Handles console logging
* parser.py: Contains the grammar, parses the program and does tree transformations for AST cleanup
* ident_usage.py: Verifies that all variables are initialized before their usage
* type_inf.py: Performs type inference and type checking on the program
* default_class_map.py: Contains information about default classes and methods
* code_gen.py: Performs code generation
* assembly.py: Assembles the code (uses asm.conf, opdefs.txt)

