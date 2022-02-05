.class CondTest:Obj

.method $constructor
.local x,z,y
	const 5
	store x
	const 0
	load x
	call Int:equals
	jump_ifnot ifend_1
ifbranch1_1:
	const "This is incorrect!\n"
	call String:print
	pop
ifend_1:
	const 4
	load x
	call Int:more
	jump_ifnot ifbranch2_1
ifbranch1_2:
	const "This is correct!\n"
	call String:print
	pop
	jump ifend_2
ifbranch2_1:
	const "This is incorrect!\n"
	call String:print
	pop
ifend_2:
	const 4
	load x
	call Int:less
	jump_ifnot ifbranch2_2
ifbranch1_3:
	const "This is incorrect!\n"
	call String:print
	pop
	jump ifend_3
ifbranch2_2:
	const 5
	load x
	call Int:atleast
	jump_ifnot ifend_4
ifbranch1_4:
	const "This is also correct!\n"
	call String:print
	pop
ifend_4:
ifend_3:
	const 3
	load x
	call Int:equals
	jump_ifnot ifbranch2_3
ifbranch1_5:
	const "This is incorrect!\n"
	call String:print
	pop
	jump ifend_5
ifbranch2_3:
	const 2
	load x
	call Int:atmost
	jump_ifnot ifbranch2_4
ifbranch1_6:
	const "This is also incorrect!\n"
	call String:print
	pop
	jump ifend_6
ifbranch2_4:
	const "This is correct!\n"
	call String:print
	pop
ifend_6:
ifend_5:
	load x
	store z
	load x
	load z
	call Obj:equals
	jump_ifnot ifbranch2_5
ifbranch1_7:
	const "I think this is correct!\n"
	call String:print
	pop
	jump ifend_7
ifbranch2_5:
	const "I think this is incorrect!\n"
	call String:print
	pop
ifend_7:
	const 5
	load x
	call Int:equals
	jump_ifnot and_1
	load x
	load z
	call Obj:equals
	call Boolean:negate
and_1:
	store y
	const "This should be false: "
	call String:print
	pop
	load y
	call Boolean:print
	pop
	const "\n"
	call String:print
	pop
	load x
	load z
	call Obj:equals
	jump_if ifbranch1_8
	const 4
	load z
	call Obj:equals
ifbranch1_8:
	jump_ifnot ifbranch2_6
ifbranch1_8:
	const "This is correct\n"
	call String:print
	pop
	jump ifend_8
ifbranch2_6:
	const "This is incorrect\n"
	call String:print
	pop
ifend_8:
	return 0
