.class PascalTriangle:Obj

.method $constructor
.local triangle_height,row,column,target,result,i
	const 15
	store triangle_height
	const 0
	store row
	jump whilecond_1
whileloop_1:
	const "Row "
	call String:print
	pop
	const 1
	load row
	call Int:plus
	call Int:print
	pop
	const ": "
	call String:print
	pop
	const 0
	store column
	jump whilecond_2
whileloop_2:
	load column
	store target
	load target
	load row
	call Int:minus
	load target
	call Int:more
	jump_ifnot ifend_1
ifbranch1_1:
	load target
	load row
	call Int:minus
	store target
ifend_1:
	const 1
	store result
	const 0
	store i
	jump whilecond_3
whileloop_3:
	const 1
	load i
	call Int:plus
	load i
	load row
	call Int:minus
	load result
	call Int:times
	call Int:divide
	store result
	const 1
	load i
	call Int:plus
	store i
whilecond_3:
	load target
	load i
	call Int:less
	jump_if whileloop_3
whileend_3:
	load result
	call Int:print
	pop
	const " "
	call String:print
	pop
	const 1
	load column
	call Int:plus
	store column
whilecond_2:
	const 1
	load row
	call Int:plus
	load column
	call Int:less
	jump_if whileloop_2
whileend_2:
	const "\n"
	call String:print
	pop
	const 1
	load row
	call Int:plus
	store row
whilecond_1:
	load triangle_height
	load row
	call Int:less
	jump_if whileloop_1
whileend_1:
	return 0
