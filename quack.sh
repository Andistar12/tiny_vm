#!/bin/bash

# This automatically compiles and executes each program available

# ------

# The location of the tiny_vm binary (and any CLI flags to run with)
TINY_VM="./tiny_vm"

# The location of the OBJ library folder
OBJ_LIB="OBJ/"

# The output folder for the compiler
OUT="out/"

# The homework folder to grade
COMPILER_FOLDER=hw3

# The compiler to invoke
COMPILER="python3 $COMPILER_FOLDER/compiler.py -o $OUT"

# ------

SRC_FILES=$(ls -Sr $COMPILER_FOLDER/src)

for f in $SRC_FILES; do
    echo "------------------------------------------"
    echo 
    echo "-> Compiling $f"
    echo 

    # Get the basename which is also the class
    file_path="$COMPILER_FOLDER/src/$f" # File path
    bn="${f%.*}" # File basename

    # Compile the program
    $COMPILER $file_path

    # Copy JSON generated files into OBJ
    json_files=$(ls -Sr $OUT | grep json)
    for j in $json_files; do
        cp $OUT/$j $OBJ_LIB
    done

    echo
    echo "-> Running $bn"
    echo

    $TINY_VM $bn

    echo 
    echo "-> Finished running $bn"
    echo 
done
