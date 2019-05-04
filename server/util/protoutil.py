#coding: utf-8

def copy_simple_field(pb_object,obj,fields = None,not_fields = None):
	for f in pb_object.DESCRIPTOR.fields:
		if f.label == f.LABEL_REPEATED:
			continue
		if f.type == f.TYPE_MESSAGE:
			continue
		if not hasattr(obj,f.name):
			continue
		if not_fields != None and f.name in not_fields:
			continue
		if fields != None and not f.name in fields:
			continue
		#print "setattr",f.name	
		v = getattr(obj,f.name)
		if v != None:
			setattr(pb_object,f.name,v)


def copy_repeated_field(pb_object,obj,fields = None,not_fields = None):
	for f in pb_object.DESCRIPTOR.fields:
		if f.label != f.LABEL_REPEATED:
			continue
		if f.type == f.TYPE_MESSAGE:
			continue

		if not_fields != None and f.name in not_fields:
			continue

		if fields != None and not f.name in fields:
			continue
		field = getattr(pb_object,f.name)
		for i in xrange(1,10):
			field_name = f.name + str(i)
			if not hasattr(obj,field_name):
				continue
			v = getattr(obj,field_name)
			if v != None:
				field.append(v)
			
			
if __name__ == "__main__":
    import doctest
    doctest.testmod()
	
			
			