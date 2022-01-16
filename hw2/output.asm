.class Sample:Obj

.method $constructor
.local a,b
	const 2
	store a
	load a
	const 3
	call Int:plus
	store b
	load b
	call Int:print
	return 0
