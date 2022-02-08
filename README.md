# HW 3

I added a Bash script `quack.sh` which compiles and runs all available Quack programs at one time. Just run the script with no CLI arguments. You may need to change the parameters at the top of the script to set the correct tiny_vm binary location and etc.

Implementation discussion can be found in `hw3/README.md`

To manually compile and run a program:

1. `cd hw3` to go to the hw3 folder
2. Run `python3 compiler.py <source file>`, you can use `src/PascalTriangle.qk` as an example
3. `cd ../` to go to root folder
4. `cp <obj file> OBJ/` to make object code visible to the vm. For PascalTriangle.qk it is in `hw3/out/PascalTriangle.json`
5. Now run `./tiny_vm <main class>` for PascalTriangle.qk it is `PascalTriangle`

# HW 2

I integrated the assembler into my compiler to streamline compilation. Main class name and output files are by default inferred from the input source file name, can be overriden. Run the compiler with `-h` for more info.

Do the following to get it to work:

1. `cd hw2` to go to the hw2 folder
2. Run `python3 compiler.py <source file>`, you can use `src/Factorial.qk` as an example
3. `cd ../` to go to root folder
4. `cp <obj file> OBJ/` to make object code visible to the vm. For Factorial.qk it is in `hw2/out/Factorial.json`
5. Now run `./tiny_vm <main class>` for Factorial.quack it is `Factorial`


# HW 1

Do the following to get it to work:

1. `cd hw1` to go to the hw1 folder
2. Now run `python3 calc.py "expression" > output.asm` where expression is an arithmetic expression (ex `(-1) * (2 + 8 / 4)`) and output.asm is the output assembly
3. Now `cd ..` to go to the parent folder
4. Now assemble that output.asm via `python3 assemble.py hw1/output.asm > sample.json`
5. Now run `./tiny_vm` to run the program


# tiny_vm
A tiny virtual machine interpreter for Quack programs

## Work in progress

This is intended to become the core of an interpreter for the Winter 2022
offering of CIS 461/561 compiler construction course at University of Oregon, 
if I can ready it in time. 

