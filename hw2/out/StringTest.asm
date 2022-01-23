.class StringTest:Obj

.method $constructor
.local t,s
	const "hello world"
	store t
	load t
	call String:print
	const " \\\\should see two backslashes\nthis is a literal string\n"
	store s
	load s
	call String:print
	return 0
