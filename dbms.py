import unicodedate
counter=0
f_out = open('temp.csv','w')
with open('steam_reviews 2.json','r') as f:
	f_out.write("username, product_id, review, found_funny, hours, date\n")
	for line in f:
		p = ast.literal_eval(line.split('\n')[0])
		try:
			product_id = int(p['product_id'])
		except:
			continue
		try:
			username = p['username']
		except:
			username = "UNKNOWN_USER"
		if(len(username)>32):
			continue
		try:
			review = p['text']
		except:
			review = ''
		try:
			found_funny = p['found_funny']
		except:
			found_funny = 0
		try:
			hours = p['hours']
		except:
			hours = 0.0
		try:
			date = p['date']
		except:
			date = '2000-01-01' #default
		username = unicodedata.normalize('NFKD', username).encode('ascii','ignore').replace("\"","\'")
		review = unicodedata.normalize('NFKD', review).encode('ascii','ignore').replace("\"","\'")
		f_out.write("\""+username+"\","+str(product_id)+",\""+review+"\","+str(found_funny)+","+str(hours)+",\""+date+"\"\n")
		if(counter%1000==0):
			f_out.flush()
		counter+=1
	f_out.flush()
	f_out.close()