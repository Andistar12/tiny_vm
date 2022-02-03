.class Factorial:Obj

.method $constructor
.local factorial,iterator,str_i
	const 1
	store factorial
	const 0
	store iterator
	const "Iteration "
	store str_i
	const 1
	load iterator
	call Int:plus
	store iterator
	load iterator
	load factorial
	call Int:times
	store factorial
	load str_i
	call String:print
	pop
	load iterator
	call Int:print
	pop
	const ": "
	call String:print
	pop
	load factorial
	call Int:print
	pop
	const "\n"
	call String:print
	pop
	const 1
	load iterator
	call Int:plus
	store iterator
	load iterator
	load factorial
	call Int:times
	store factorial
	load str_i
	call String:print
	pop
	load iterator
	call Int:print
	pop
	const ": "
	call String:print
	pop
	load factorial
	call Int:print
	pop
	const "\n"
	call String:print
	pop
	const 1
	load iterator
	call Int:plus
	store iterator
	load iterator
	load factorial
	call Int:times
	store factorial
	load str_i
	call String:print
	pop
	load iterator
	call Int:print
	pop
	const ": "
	call String:print
	pop
	load factorial
	call Int:print
	pop
	const "\n"
	call String:print
	pop
	const 1
	load iterator
	call Int:plus
	store iterator
	load iterator
	load factorial
	call Int:times
	store factorial
	load str_i
	call String:print
	pop
	load iterator
	call Int:print
	pop
	const ": "
	call String:print
	pop
	load factorial
	call Int:print
	pop
	const "\n"
	call String:print
	pop
	const 1
	load iterator
	call Int:plus
	store iterator
	load iterator
	load factorial
	call Int:times
	store factorial
	load str_i
	call String:print
	pop
	load iterator
	call Int:print
	pop
	const ": "
	call String:print
	pop
	load factorial
	call Int:print
	pop
	const "\n"
	call String:print
	pop
	return 0
