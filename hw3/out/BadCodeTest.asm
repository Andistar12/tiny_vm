.class BadCodeTest:Obj

.method $constructor
.local x,y
	const 5
	store x
	const 2
	load x
	call Int:less
	jump_ifnot ifbranch2_1
ifbranch1_1:
	const 2
	store y
	const "nope"
	call String:print
	pop
	jump ifend_1
ifbranch2_1:
	const 3
	store y
ifend_1:
	load y
	call Int:print
	pop
	return 0
