from steam import app
from flask import render_template, request, jsonify
import json
import ast
from flask import redirect, url_for, flash, session
from .constants import *
import hashlib
import datetime
import numpy as np
import psycopg2
from scipy import spatial
import time
from datetime import datetime

#conn = psycopg2.connect(user = "postgres",password = "montyhanda",host = "127.0.0.1",port = "5432",database = "proj_temp")
#conn = psycopg2.connect(user = "postgres",password = "lhasa",host = "127.0.0.1",port = "5432",database = "steam_project")
conn = psycopg2.connect(user = "group_24",password = "456-932-282",host = "10.17.50.126",port = "5432",database = "group_24")
cur = conn.cursor()

movie_vec_list = []

@app.before_first_request
def function_to_run_only_once():
	cur.execute("select * from tags")
	full_tags_table = cur.fetchall()
	for tup in full_tags_table:
		appid = tup[0]
		movie_vec = np.array(tup[1:])
		movie_vec = movie_vec / np.sum(movie_vec)
		movie_vec_list.append((appid,movie_vec))

@app.route('/home')
@app.route('/')
def home():
	#home page show top bought games, top favorited games
	#inner join to get names of games from games table
	try:
		cur.execute("SELECT games.name, games.appid FROM mat_top10_bought,games where games.appid=mat_top10_bought.appid");
		rows = cur.fetchall()
		top10bought = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["appid"] = tup[1]
				top10bought.append(D)

		cur.execute("SELECT games.name, games.appid FROM mat_top10_fav,games where games.appid=mat_top10_fav.appid");
		rows = cur.fetchall()
		top10fav = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["appid"] = tup[1]
				top10fav.append(D)
		# if user is logged in then recommended games for you
		recommended = getRecommended()
		conn.commit()
		return render_template('home.html', user="DEFAULT", top10fav=top10fav, top10bought=top10bought, recommended=recommended)
	except Exception as e:
		conn.rollback()
		print("home", e)
		return "Some error occured"


@app.route('/all_games')
def all_games():
	try:
		cur.execute("SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY positive_ratings DESC, name ASC OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY ");
		rows = cur.fetchall()
		games = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["release_date"] = tup[1]
				D["appid"] = tup[2]
				D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "FREE" #in inr
				D["positive_ratings"] = tup[4]
				D["negative_ratings"] = tup[5]
				games.append(D)
		cur.execute("SELECT count(*) from games")
		rows = cur.fetchall()
		if len(rows)>0:
			totalRows = rows[0][0]
		else:
			totalRows = 0
		conn.commit()
		return render_template('all_games.html', user="DEFAULT",games = games, totalRows=totalRows)
	except Exception as e:
		conn.rollback()
		print("all_games",e)
		return "Some error occured"

#return game description, website url, support url, tags and requirements using appid
@app.route('/game_details')
def game_details():
	appid = request.args.get('appid').replace("'","&#39") ###
	if appid == None:
		return "No appid provided"
	try:
		variables = {}
		cur.execute("SELECT detailed_description FROM games_description WHERE appid="+str(appid))
		rows = cur.fetchall()
		if len(rows)>0:
			description = rows[0][0]
		else:
			description = None
		cur.execute("SELECT website,support_url FROM support WHERE appid="+str(appid))
		rows = cur.fetchall()
		if(len(rows)>0):
			website = rows[0][0]
			steam_page = rows[0][1]
		else:
			website = None
			steam_page = None
		cur.execute("SELECT pc_requirements,mac_requirements,linux_requirements FROM requirements WHERE appid="+str(appid))
		rows = cur.fetchall()
		if len(rows)>0:
			wr = ast.literal_eval(rows[0][0])
			mr = ast.literal_eval(rows[0][1])
			lr = ast.literal_eval(rows[0][2])
			try:
				windows_requirements = wr['minimum']
			except:
				windows_requirements = None
			try:
				mac_requirements = mr['minimum']
			except:
				mac_requirements = None
			try:
				linux_requirements = lr['minimum']
			except:
				linux_requirements = None
		else:
			windows_requirements = None
			mac_requirements = None
			linux_requirements = None
		
		cur.execute('''
		SELECT column_name
		FROM information_schema.columns
		where table_name   = 'tags'
			;
		''')
		tags_list = cur.fetchall()
	#	print(tags_list)
		cur.execute("SELECT * FROM tags WHERE appid="+str(appid));
		rows = cur.fetchall()
		tags = []
		if len(rows)>0:
			arr = [(rows[0][i], tags_list[i][0]) for i in range(1, len(tags_list))]
			arr.sort(reverse = True)
			tup = rows[0]
			for i in range(0,len(tags_list)-1):
				if int(arr[i][0])>0:
					tags.append(arr[i][1])

		cur.execute("SELECT * FROM games WHERE appid="+str(appid))
		rows = cur.fetchall()
		if len(rows)>0:
			tup = rows[0]
			variables["name"] = tup[1]
			variables["release_date"] = tup[2]
			variables["is_english"] = tup[3]
			variables["developer"] = tup[4]
			variables["platforms"] = tup[6].split(";") #list
			variables["required_age"] = tup[7]
			variables["genres"] = tup[9]
			variables["tags"] = tags
			variables["achievements "] = tup[11]
			variables["positive_ratings"] = tup[12]
			variables["negative_ratings"] = tup[13]
			variables["average_playtime"] = tup[14]
			variables["player_count"] = tup[16]
			variables["price"] = round(float(tup[17])*93.13,2)
		else:
			variables["name"] = None
			variables["release_date"] = None
			variables["is_english"] = None
			variables["developer"] = None
			variables["platforms"] = None
			variables["required_age"] = None
			variables["genres"] = None # ; seperated
			variables["tags"] = [] # ; seperated
			variables["achievements "] =  None
			variables["positive_ratings"] =  None
			variables["negative_ratings"] =  None
			variables["average_playtime"] =  None
			variables["player_count"] =  None
			variables["price"] = None
		variables["description"] = description
		variables["website"] = website
		variables["steam_page"] = steam_page
		variables["windows_requirements"] = windows_requirements
		variables["linux_requirements"] = linux_requirements
		variables["mac_requirements"] = mac_requirements
		variables["appid"] = appid
		if 'user' in session:
			username = session['user']
			cur.execute("SELECT appid FROM favourites WHERE username = '" + str(username) + "'")
			session['user_obj']['favs'] = [a[0] for a in cur.fetchall()]

			cur.execute("SELECT * FROM transactions WHERE username = '" + str(username) + "' and appid = " + str(appid))
			if len(cur.fetchall())==0:
				variables['owned'] = 1
			else:
				variables['owned'] = 0
			
			cur.execute("SELECT money FROM wallets WHERE username = '" + str(username) + "'")
			row = cur.fetchall()
			money = row[0][0]
			variables['user_money'] = money
		conn.commit()
		return render_template('game_details.html', user="DEFAULT",vars = variables)
	except Exception as e:
		conn.rollback()
		print("game_details",e)
		return "Some error occured"

@app.route('/reviews')
def reviews():
	appid = request.args.get('appid').replace("'","&#39") ###
	page_num = request.args.get('page_num').replace("'","&#39") ###
	if appid == None:
		return "No appid provided"
	if page_num == None:
		return "No offset provided"
	try:
		cur.execute("SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY found_funny DESC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY ")
		#return a list of dictionary
		rev = []
		rows = cur.fetchall()
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["username"] = tup[0]
				D["review"] = tup[1]
				D["found_funny"] = tup[2]
				D["hours"] = tup[3]
				D["date"] = tup[4]
				rev.append(D)
		conn.commit()
		return render_template('reviews.html', user="DEFAULT",reviews = rev, appid=appid)
	except Exception as e:
		print("reviews",e)
		conn.rollback()
		return "Some error occured"

@app.route('/reviews_POST', methods=['POST'])
def reviews_POST():
	appid = request.form.get('appid').replace("'","&#39") ###
	page_num = request.form.get('page_num').replace("'","&#39") ###
	method = request.form.get('method').replace("'","&#39")
	if appid == None:
		return "No appid provided"
	if page_num == None:
		return "No offset provided"

	if method == 'found_funny_asc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY found_funny ASC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	elif method == 'found_funny_desc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY found_funny DESC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	elif method == 'hours_asc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY hours ASC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	elif method == 'hours_desc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY hours DESC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	elif method == 'date_asc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY date ASC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	elif method == 'date_desc':
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY date DESC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
	else:
		#default by found funny desc
		query = "SELECT username,review,found_funny,hours,date FROM reviews WHERE appid="+str(appid)+" ORDER BY found_funny DESC, username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "

	try:
		cur.execute(query)
		#return a list of dictionary
		rev = []
		rows = cur.fetchall()
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["username"] = tup[0]
				D["review"] = tup[1]
				D["found_funny"] = tup[2]
				D["hours"] = tup[3]
				D["date"] = str(tup[4])
				rev.append(D)
		conn.commit()
		return json.dumps(rev)
	except Exception as e:
		print("reviews",e)
		conn.rollback()
		return "Some error occured"




@app.route('/screenshots')
def screenshots():
	appid = request.args.get('appid').replace("'","&#39") ###
	if appid == None:
		return "No appid provided"
	try:
		cur.execute("SELECT screenshots FROM media_data WHERE appid="+str(appid))
		html = """""";
		rows = cur.fetchall()
		res = []
		conn.commit()
		if len(rows)>0:
			for ss in ast.literal_eval(rows[0][0]):
				D = {}
				D['path_full'] = ss['path_full']
				D['path_thumbnail'] = ss['path_thumbnail']
				res.append(D)
			return render_template('screenshots.html',user="DEFAULT",screenshots=res)
		else:
			return "No screenshots found"
	except Exception as e:
		print("screenshots",e)
		conn.rollback()
		return "Some error occured"

@app.route('/searchGames',methods=['POST'])
def searchGames():
	if request.method == 'POST':
		searchString = request.form.get('string').replace("'","&#39")
		page_num = request.form.get('page_num').replace("'","&#39")
		method = request.form.get('method').replace("'","&#39")
		if searchString=="" or page_num=="" or int(page_num)<=0:
			return json.dumps("[]")
		page_num = int(page_num)
		searchString = searchString.lower() #to remove any caps problem

		if method == 'release_date_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY release_date ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'release_date_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY release_date DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'price_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY (price::float) ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'price_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY (price::float) DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'positive_ratings_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY positive_ratings ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'positive_ratings_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY positive_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'negative_ratings_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY negative_ratings ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'negative_ratings_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY negative_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		else:
			#default by positive ratings
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY positive_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		
		try:
			cur.execute(query);
		except Exception as e:
			print("searchGames1",e)
			conn.rollback()
			return "Some error occured 1"
		rows = cur.fetchall()
		games = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["release_date"] = str(tup[1])
				D["appid"] = tup[2]
				D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "FREE" #in inr
				D["positive_ratings"] = tup[4]
				D["negative_ratings"] = tup[5]
				games.append(D)
		#for counting total matching games
		try:
			cur.execute("SELECT count(*) from games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%'")
			conn.commit()
		except Exception as e:
			print("searchGames2",e)
			conn.rollback()
			return "Some error occured 2"
		rows = cur.fetchall()
		if len(rows)>0:
			totalRows = rows[0][0]
		else:
			totalRows = 0
		games.append({"totalRows": totalRows}) #last object becomes totalRows
		return json.dumps(games)
	else:
		return "Invalid Request"

@app.route('/getGames',methods=['POST'])
def getGames():
	if request.method == 'POST':
		page_num = request.form.get('page_num').replace("'","&#39")
		method = request.form.get('method').replace("'","&#39")
		if method == 'release_date_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY release_date ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'release_date_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY release_date DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'price_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY (price::float) ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'price_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY (price::float) DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'positive_ratings_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY positive_ratings ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'positive_ratings_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY positive_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'negative_ratings_asc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY negative_ratings ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		elif method == 'negative_ratings_desc':
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY negative_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		else:
			#default by positive ratings DESC
			query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL ORDER BY positive_ratings DESC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "
		if int(page_num)<=0:
			return json.dumps("[]")
		try:
			cur.execute(query);
			rows = cur.fetchall()
			games = []
			if len(rows)>0:
				for tup in rows:
					D = {}
					D["name"] = tup[0]
					D["release_date"] = str(tup[1])
					D["appid"] = tup[2]
					D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "FREE" #in inr
					D["positive_ratings"] = tup[4]
					D["negative_ratings"] = tup[5]
					games.append(D)
			conn.commit()
			return json.dumps(games)
		except Exception as e:
			print("getGames",e)
			conn.rollback()
			return "Some error occured"
	else:
		return "Invalid Request"

@app.route('/manageUser', methods=['GET','POST'])
def manageUser():
	#when admin is user then only open this page
	if 'admin' in session:
		if request.method == 'GET':
			page_num = 1
		else:
			page_num = request.form.get('page_num').replace("'","&#39")
		page_num = int(page_num)
		if page_num <=0:
			return "Bad page number"
		try:
			cur.execute("SELECT username, isbanned FROM users WHERE isadmin=false ORDER BY username ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY ")
			rows = cur.fetchall()
			userslist = []
			for tup in rows:
				userObj = {}
				userObj['username'] = tup[0]
				userObj['isbanned'] = str(tup[1]).lower()
				userslist.append(userObj)
			# conn.commit()
			return render_template('manage_user.html',user="DEFAULT", userslist = userslist)
		except Exception as e:
			# conn.rollback()
			print("manageUser",e)
			return "Some error occured"
	else:
		return "you don't have rights to perform this action"


@app.route('/banUser', methods=['POST'])
def banUser():
	#only when the request is made by admin
	if 'admin' in session:
		if request.method == 'POST':
			username = request.form.get('username').replace("'","&#39")
			username = str(username)
			try:
				cur.execute("UPDATE users SET isbanned=true WHERE username='"+username+"'")
				conn.commit()
				return "successfully banned user "+ username
			except Exception as e:
				conn.rollback()
				print("banuser",e)
				return "Some error occured"
		else:
			return "Bad request"
	else:
		return "you don't have rights to perform this action"

@app.route('/unbanUser', methods=['POST'])
def unbanUser():
	#only when the request is made by admin
	if 'admin' in session:
		if request.method == 'POST':
			username = request.form.get('username').replace("'","&#39")
			username = str(username)
			try:
				cur.execute("UPDATE users SET isbanned=false WHERE username='"+username+"'")
				conn.commit()
				return "unbanned user "+ username
			except Exception as e:
				print("unbanuser", e)
				conn.rollback()
				return "Some error occured"
		else:
			return "Bad request"
	else:
		return "you don't have rights to perform this action"

@app.route('/register')
def register():
	try:
	#	cur.execute("SELECT * from users")
	#		rows = cur.fetchall()
	#	if len(rows)>0:
	#		users = [r[0] for r in rows]
	#	else:
	#		users = []
		return render_template('register.html')
	except Exception as e:
		print(e)
		return ""

@app.route('/register',methods=['POST'])
def regUser():
	usr_id = request.form.get('username').replace("'","&#39")
	pass_ = request.form.get('password').replace("'","&#39")
	pass_hash = hashlib.sha256(pass_.encode()).hexdigest()
#	print(usr_id, pass_, 'details')

	cur.execute("SELECT * FROM users WHERE username = '" + str(usr_id) + "'")
	row = cur.fetchall()
	if len(row)!=0:
		flash('User already exists.')
		return redirect(url_for('register'))
	
	try:
		cur.execute("INSERT INTO users (username, password) VALUES ('" + str(usr_id)+"','" + str(pass_hash)+"' );")
		conn.commit()
		cur.execute("INSERT INTO wallets (username) VALUES ('" + str(usr_id)+"')")
		conn.commit()
		session['user'] = usr_id
		user = {}
		user['username'] = session['user']
		user['favs'] = []
		session['user_obj'] = user
		return redirect(url_for('home'))
	except Exception as e:
		print('Exception')
		print(e)
		return redirect(url_for('register'))

@app.route('/login', methods = ['POST', 'GET'])
def login():
	if request.method == 'GET':
		return render_template('login.html')

	if request.method == 'POST':
		usr_id = request.form.get('username').replace("'","&#39")
		pass_ = request.form.get('password').replace("'","&#39")
		pass_hash = hashlib.sha256(pass_.encode()).hexdigest()
	#	print(usr_id, pass_, 'details')

		cur.execute("SELECT * FROM users WHERE username = '" + str(usr_id) + "'")
		row = cur.fetchall()
		if len(row)==0:
			flash('User does not exists.')
			return redirect(url_for('login'))
		if row[0][1]!=pass_hash:
			flash('Incorrect password.')
			return redirect(url_for('login'))
		if row[0][3]!=False:
			flash('You have been banned!')
			return redirect(url_for('login'))

		try:
			if row[0][2]:
				session['admin'] = usr_id
			session['user'] = usr_id
			cur.execute("SELECT appid FROM favourites WHERE username = '" + str(usr_id) + "'")
			user = {}
			user['username'] = session['user']
			user['favs'] = [a[0] for a in cur.fetchall()]
			session['user_obj'] = user
			return redirect(url_for('home'))
		except Exception as e:
			print('Exception')
			print(e)
			return redirect(url_for('login'))


@app.route('/logout')
def logout():
	session.pop('user', None)
	session.pop('user_obj', None)
	if 'admin' in session:
		session.pop('admin', None)
	return redirect(url_for('home'))

@app.route('/profile')
def profile():
	if 'user' not in session:
		flash('You need to be logged in to see your profile.')
		return redirect(url_for('login'))

	usr_id = session['user']
	return render_template('profile.html', username = usr_id)

@app.route('/toggle_fav')
def toggle_fav():
	appid = request.args.get('appid').replace("'","&#39")
	username = session['user']
	if appid == None:
		return "No appid provided"
	try:
		cur.execute("SELECT appid FROM favourites where appid = "+str(appid)+" and username = '" + str(username) +"'")
		row = cur.fetchall()
		print(row)
		if len(row)!=0:
			cur.execute("delete from favourites where appid = "+str(appid)+" and username = '" + str(username) +"'")
			conn.commit()
			return str(appid) + " removed from favourites"
		else:
			cur.execute("insert into favourites values ("+str(appid)+", '" + str(username) +"')")
			conn.commit()
			return "game has been added to favourites"
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/get_fav')
def get_fav():
	username = session['user']
	try:
		cur.execute("SELECT name,release_date,appid,price FROM games WHERE appid in (SELECT appid FROM favourites where username = '" + str(username) +"')")
		rows = cur.fetchall()
		games = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["release_date"] = tup[1]
				D["appid"] = tup[2]
				D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "FREE" #in inr
				games.append(D)
		return render_template('fav_games.html', games = games)
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/wallet')
def my_wallet():
	username = session['user']
	try:
		cur.execute("SELECT money FROM wallets WHERE username = '" + str(username) + "'")
		row = cur.fetchall()
		money = row[0][0]
		return render_template('wallet.html', money = money)
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/add_money')
def add_money():
	username = session['user']
	try:
		amount = float(request.args.get('amount').replace("'","&#39"))
		print(amount)
		cur.execute("SELECT money FROM wallets WHERE username = '" + str(username) + "'")
		row = cur.fetchall()
		money = row[0][0]
		amount+=money
		cur.execute("update wallets set money = " + str(amount) + " where username = '" + str(username) + "'")
		conn.commit()
		session['user_obj']['money'] = amount
		return "Success. " + str(amount-money) + " has been added to your wallet."
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/game_transaction')
def game_transaction():
	username = session['user']
	appid = request.args.get('appid').replace("'","&#39")
	ts = str(psycopg2.TimestampFromTicks(time.time()))
	price = request.args.get('price').replace("'","&#39")
	try:
		amount = float(request.args.get('amount').replace("'","&#39"))
		print(amount)
		cur.execute("SELECT money FROM wallets WHERE username = '" + str(username) + "'")
		row = cur.fetchall()
		money = row[0][0]
		amount+=money
		cur.execute('''
		BEGIN TRANSACTION;
		update wallets set money = {amt} where username = '{usr}';
		insert into transactions values ({appid}, '{usr}', {price}, {ts});
		END TRANSACTION;
		'''.format(amt = amount, usr = username, appid = appid, price = price, ts = ts))
		conn.commit()
		return "Success. " + str(appid) + " has been added to your library."
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/get_money')
def get_money():
	username = session['user']
	try:
		cur.execute("SELECT money FROM wallets WHERE username = '" + str(username) + "'")
		row = cur.fetchall()
		money = row[0][0]
		return str(money)
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/add_game')
def add_game():
	username = session['user']
	appid = request.args.get('appid').replace("'","&#39")
	ts = psycopg2.TimestampFromTicks(time.time())
	price = request.args.get('price').replace("'","&#39")
	try:
		cur.execute("insert into transactions values ("+str(appid)+", '" + str(username) +"', " + str(price) + ", " + str(ts) +")")
		conn.commit()
		return "game is added to your library."
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/game_lib')
def game_lib():
	username = session['user']
	try:
		cur.execute("SELECT name,release_date,appid,price FROM games WHERE appid in (SELECT appid FROM transactions where username = '" + str(username) +"')")
		rows = cur.fetchall()
		games = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["release_date"] = tup[1]
				D["appid"] = tup[2]
				D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "unknown" #in inr
				games.append(D)
		return render_template('library.html', games = games)
	except Exception as e:
		print('Exception')
		print(e)
		return str(e)

@app.route('/addMoney', methods=['POST'])
def addMoney():
	#only admin can use this method
	if 'admin' in session:
		if request.method == 'POST':
			username = request.form.get('username').replace("'","&#39")
			amount = request.form.get('amount').replace("'","&#39")
			username = str(username)
			amount = round(float(amount),2)
			try:
				cur.execute("UPDATE wallets SET money = money+"+str(amount)+" WHERE username='"+username+"'")
				conn.commit()
				return "added money to wallet of user "+ username
			except Exception as e:
				print("addMoney",e)
				conn.rollback()
				return "Some error occured!"
		else:
			return "Bad request"
	else:
		return "you don't have rights to perform this action"


@app.route('/addGame', methods=['POST'])
def addGame():
	#only admin can call this function
	if 'admin' in session:
		if request.method == 'POST':
			name = request.form.get('name').replace("'","&#39")
			release_date = request.form.get('release_date')
			description = request.form.get('description').replace("'","&#39")
			developers = request.form.get('developers').replace("'","&#39")
			publishers = request.form.get('publishers').replace("'","&#39")
			platforms = request.form.get('platforms').replace("'","&#39")
			required_age = request.form.get('required_age')
			categories = request.form.get('categories').replace("'","&#39")
			genres = request.form.get('genres').replace("'","&#39")
			tags = request.form.getlist('tags[]')
			achievements = request.form.get('achievements')
			price = request.form.get('price')
			price = float(price)
			price /=93.13 #to convert to gbp
			price = round(price,2)
			try:
				cur.execute("SELECT MAX(appid) from games");
				rows = cur.fetchall()
				appidmax = int(rows[0][0])
				newappid = appidmax+1
			except Exception as e:
				print("addGame1",e)
				conn.rollback()
				return "Some error occured1!"

			tags_set = set(tags)
			tags_temp = []
			for tg in TAGS_LIST:
				if tg in tags_set:
					tags_temp.append('1')
				else:
					tags_temp.append('0')
			try:

				cur.execute(
					'''
					BEGIN TRANSACTION;
					
					INSERT INTO games (appid, name,release_date,is_english,developer,publisher,platforms,required_age,categories,genres,steamspy_tags,achievements,positive_ratings,negative_ratings,average_playtime,median_playtime,owners_range,price)
									VALUES ({newappid},'{name}','{release_date}',1,'{developers}','{publishers}','{platforms}',{required_age},'{categories}','{genres}','{tags}',{achievements},0,0,0,0,'0-20000',{price});

				 	INSERT INTO tags values ({newappid},{tagsString});

				 	INSERT INTO games_description (appid, detailed_description, about_game, short_description)
							VALUES ({newappid}, '{description}', '{description}', '{description}');

					COMMIT TRANSACTION;
					'''.format(newappid=newappid, name=name, release_date=release_date, developers=developers,publishers=publishers,platforms=platforms,required_age=required_age,categories=categories,
						genres=genres,tags=";".join(tags),achievements=achievements,price=str(price), tagsString= ",".join(tags_temp),
						description=description)
					)

				# cur.execute(
				# 			'''
				# 			INSERT INTO games (appid, name,release_date,is_english,developer,publisher,platforms,required_age,categories,genres,steamspy_tags,achievements,positive_ratings,negative_ratings,average_playtime,median_playtime,owners_range,price)
				# 			VALUES ({newappid},'{name}','{release_date}',1,'{developers}','{publishers}','{platforms}',{required_age},'{categories}','{genres}','{tags}',{achievements},0,0,0,0,'0-20000',{price})
				# 			'''.format(newappid=newappid, name=name, release_date=release_date, developers=developers,publishers=publishers,platforms=platforms,required_age=required_age,categories=categories,
				# 				genres=genres,tags=tags,achievements=achievements,price=str(price))
				# 			)
				# cur.execute('''
				# 			INSERT INTO games_description (appid, detailed_description, about_game, short_description)
				# 			VALUES ({newappid}, '{description}', '{description}', '{description}')
				# 			'''.format(newappid=newappid, description=description))
				conn.commit()
				return "added game "+name
			except Exception as e:
				print("addGame2",e)
				conn.rollback()
				return "Some error occured2!"
		else:
			return "Bad request"
	else:
		return "you don't have rights to perform this action"


# @app.route('/admin')
# def admin():
# 	return render_template('admin_page.html',user="DEFAULT")

@app.route('/deleteGame', methods=['POST'])
def deleteGame():
	#only admin can call this function
	if 'admin' in session:
		if request.method == 'POST':
			appid = request.form.get('appid')
			try:
				cur.execute("DELETE FROM games where appid="+str(appid));
				conn.commit()
				return "successfully deleted!"
			except Exception as e:
				print("deleteGame",e)
				conn.rollback()
				return "Some error occured!"
		else:
			return "Invalid request"
	else:
		return "you don't have rights to perform this action"


@app.route('/getMoneyOfUser', methods=['POST'])
def getMoneyOfUser():
	if request.method == 'POST':
		username = request.form.get('username').replace("'","&#39")
		try:
			cur.execute("SELECT money from wallets where username='"+str(username)+"'")
			rows = cur.fetchall()
			if len(rows)>0:
				money = str(round(float(rows[0][0]), 1))+" INR"
			else:
				money = "unable to fetch money"
			conn.commit()
			return money
		except Exception as e:
			conn.rollback()
			print("getMoneyOfUser",e)
			return "unable to fetch money"
	else:
		return "Invalid request"


@app.route('/submit_review', methods=['POST'])
def add_review():
	if request.method == 'POST':
		review_text = request.form.get('review_text').replace("'","&#39")
		appid = request.form.get('appid').replace("'","&#39")
		if 'user' in session:
			username = session['user']
		else:
			username = ""
		#to check whether given user owns this game or not then only allow him to submit review
		cur.execute("SELECT * from transactions where appid="+appid+" AND username='"+username+"'")
		rows = cur.fetchall()
		if len(rows)>0:
			try:
				#given user has the rights to review this game
				cur.execute('''
							INSERT INTO reviews (username, appid,review,found_funny,hours,date)
							VALUES ('{username}',{appid},'{review_text}',0,0,'{today_date}')
							'''.format(username=username, appid=appid, review_text=review_text, today_date=datetime.today().strftime('%Y-%m-%d')))
				conn.commit()
				return "successfully submitted your review"
			except Exception as e:
				conn.rollback()
				print("addReview",e)
				return "some error occured"
	else:
		return "Invalid request"

@app.route('/movies')
def movies():
	appid = request.args.get('appid').replace("'","&#39") ###
	if appid == None:
		return "No appid provided"
	try:
		cur.execute("SELECT movies FROM media_data WHERE appid="+str(appid))
		rows = cur.fetchall()
		res = []
		conn.commit()
		if len(rows)>0:
			if not rows[0][0]:
				return "there are no videos for this game"
			for movobj in ast.literal_eval(rows[0][0]):
				try:
					D = {}
					D['name'] = movobj['name']
					D['thumbnail'] = movobj['thumbnail']
					D['lqlink'] = movobj['webm']['480']
					D['hqlink'] = movobj['webm']['max']
					res.append(D)
				except:
					continue
			return render_template('movies.html',user="DEFAULT",movies=res)
		else:
			return "there are no videos for this game"
	except Exception as e:
		print("movies",e)
		conn.rollback()
		return "Some error occured"


def getRecommended():
	#given a username, generate recommendation for that user
	if 'user' in session:
		username = session['user']
	else:
		return "Not logged in"

	user_vec = np.zeros(len(TAGS_LIST))
	users_favorited = set() #appid consisting of already users favorites
	count = 0
	#first generate tag vector of this user using his favorites and taking average of all the tags
	cur.execute("select * from tags,favourites where username='"+username+"' AND tags.appid=favourites.appid")
	rows = cur.fetchall()
	for tup in rows:
		appid = tup[0]
		users_favorited.add(appid)
		row_vec = np.array(tup[1:-3]) #to trim out some columns not in tags
		row_vec = row_vec/np.max(row_vec)
		user_vec += row_vec
		count += 1
	user_vec = user_vec/count #to take average
	# print(user_vec)
	# print(len(user_vec))
	# print(len(TAGS_LIST))
	#go over the tags table and find the consine similarity corresponding to the appid in the tag table
	recommended = []
	for vec_tup in movie_vec_list:
		similarity = 1 - spatial.distance.cosine(user_vec, vec_tup[1])
		recommended.append((vec_tup[0],similarity))
	recommended.sort(key=lambda x: x[1] ,reverse=True)
	simValues = [x[1] for x in recommended if x[0] not in users_favorited][:10]
	recommended = [x[0] for x in recommended if x[0] not in users_favorited][:10]
	if(len(recommended)<10):
		#very rare case
		recommended.extend([10,10,10,10,10,10,10,10,10,10])
		recommended = recommended[:10]

	try:
		cur.execute('''
					SELECT appid,name from games where appid={one} or appid={two} or appid={three} or appid={four} or appid={five}
					or appid={six} or appid={seven} or appid={eight} or appid={nine} or appid={ten}
					'''.format(one=recommended[0],two=recommended[1],three=recommended[2],four=recommended[3],five=recommended[4],
						six=recommended[5], seven=recommended[6], eight=recommended[7], nine=recommended[8], ten=recommended[9],))
	except Exception as e:
		print("getRecommended",e)
	rows = cur.fetchall()
	result = []
	hashmap = {}
	for tup in rows:
		hashmap[tup[0]] = tup[1]
	for i in range(len(recommended)):
		D = {}
		D["appid"] = recommended[i]
		D["name"] = hashmap[recommended[i]]
		D["similarity"] = simValues[i]
		result.append(D)
	return result

@app.route('/refresh_views')
def refresh_views():
	try:
		cur.execute('''
		REFRESH MATERIALIZED VIEW mat_top10_fav;
		REFRESH MATERIALIZED VIEW mat_top10_bought;
		''')
		conn.commit()
		return 'Views refreshed'
	except Exception as e:
		conn.rollback()
		print("getMoneyOfUser",e)
		return "unable to fetch money"

@app.route('/advanced_search')
def advanced_search():
	return render_template('advanced_search.html',user="DEFAULT")

@app.route('/advancedSearchGames',methods=['POST'])
def advancedSearchGames():
	if request.method == 'POST':
		name = request.form.get('name').replace("'","&#39").lower() ###
		publisher = request.form.get('publisher').replace("'","&#39").lower() ###
		genre = request.form.get('genre').replace("'","&#39").lower() ###
		platform = request.form.get('platform').replace("'","&#39").lower() ###
		price_lessthan_or_equal = request.form.get('price_lessthan_or_equal').replace("'","&#39").lower() ###
		price_greaterthan_or_equal = request.form.get('price_greaterthan_or_equal').replace("'","&#39").lower() ###
		selected_tags = request.form.getlist('selected_tags[]')
		# query = "SELECT name,release_date,appid,price,positive_ratings,negative_ratings FROM games WHERE appid IS NOT NULL AND LOWER(name) LIKE '%"+ searchString +"%' ORDER BY release_date ASC, name ASC OFFSET "+ str((int(page_num)-1)*10) +" ROWS FETCH NEXT 10 ROWS ONLY "

		#first select appids from tags where row has non zero for all the tags in the selected_tags
		query = ""
		if len(selected_tags)>0:
			query = "SELECT games.appid, games.name, games.release_date, games.price, games.positive_ratings, games.negative_ratings FROM games, tags WHERE games.appid=tags.appid "
			for tag in selected_tags:
				query += "AND \""+tag+"\" <> 0 "
		else:
			query = "SELECT games.appid, games.name, games.release_date, games.price, games.positive_ratings, games.negative_ratings from games WHERE appid IS NOT NULL"
		
		if name != '':
			query += " AND LOWER(name) LIKE '%"+ name +"%'"

		if publisher != '':
			query += " AND LOWER(publisher) LIKE '%"+ publisher +"%'"

		if genre != '':
			query += " AND LOWER(genres) LIKE '%"+ genre +"%'"

		if platform != '':
			query += " AND LOWER(platforms) LIKE '%"+ platform +"%'"

		if price_lessthan_or_equal != '':
			query += " AND (price::float) <= "+ str(round(float(price_lessthan_or_equal)/93.13, 2))

		if price_greaterthan_or_equal != '':
			query += " AND (price::float) >= "+ str(round(float(price_greaterthan_or_equal)/93.13, 2))

		try:
			cur.execute(query)
			rows = cur.fetchall()
			games = []
			for tup in rows:
				D = {}
				D["appid"] = tup[0]
				D["name"] = tup[1]
				D["release_date"] = tup[2]
				D["price"] = str(round(float(tup[3])*93.13, 1))+" INR" if float(tup[3])!=0.0 else "FREE" #in inr
				D["positive_ratings"] = tup[4]
				D["negative_ratings"] = tup[5]
				games.append(D)
			conn.commit()
			return json.dumps(games)
		except Exception as e:
			conn.rollback()
			print("advanced_search",e)
			return "Some error occured"
		
	else:
		return "Invalid request"