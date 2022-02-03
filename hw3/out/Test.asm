.class Test:Obj

.method $constructor
	const 5
	const 3
	call Int:plus
	call String:print
	pop
	const "hello world\n"
	call String:print
	pop
	const "\nel psy congroo\n"
	call String:print
	pop
	return 0
