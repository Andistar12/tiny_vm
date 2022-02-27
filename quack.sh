#!/bin/bash

# This automatically compiles and executes each program available

# ------

# The location of the tiny_vm binary (and any CLI flags to run with)
TINY_VM="./tiny_vm"

# The location of the OBJ library folder
OBJ_LIB="OBJ/"

# The output folder for the compiler
OUT="out"

# The homework folder to grade
COMPILER_FOLDER=hw4

# The compiler to invoke
COMPILER="python3 $COMPILER_FOLDER/compiler.py -o $OUT -j $OBJ_LIB"

# ------

echo
echo "Script Parameters":
echo "TINY_VM location: $TINY_VM"
echo "OBJ lib folder: $OBJ_LIB"
echo "Compiler output folder: $OUT"
echo "Compiler working directory: $COMPILER_FOLDER"
echo "Compiler exec command: $COMPILER"
echo

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
    if ! $COMPILER $file_path; then
        echo
        continue
    fi

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
