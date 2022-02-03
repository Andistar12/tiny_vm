.class StringTest:Obj

.method $constructor
.local t,s
	const "hello"
	store t
	load t
	call String:print
	pop
	const " \\\\should see two backslashes\nthis is a literal string\n"
	store s
	load s
	call String:print
	pop
	const "world"
	const " "
	load t
	call String:plus
	call String:plus
	store t
	load t
	call String:print
	pop
	return 0
