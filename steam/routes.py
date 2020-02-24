from steam import app
from flask import render_template, request
import json
import ast
from .constants import *

import psycopg2
conn = psycopg2.connect(user = "postgres",password = "montyhanda",host = "127.0.0.1",port = "5432",database = "project")
cur = conn.cursor()

@app.route('/home')
def home():
	try:
		cur.execute("SELECT name,release_date,appid FROM games WHERE appid IS NOT NULL ORDER BY positive_ratings DESC, name ASC limit 10")
		rows = cur.fetchall()
		games = []
		if len(rows)>0:
			for tup in rows:
				D = {}
				D["name"] = tup[0]
				D["release_date"] = tup[1]
				D["appid"] = tup[2]
				games.append(D)
		return render_template('home.html', user="DEFAULT",games = games)
	except Exception as e:
		print(e)
		return ""


@app.route('/login')
def login():
	return ""


#return game description, website url, support url, tags and requirements using appid
@app.route('/game_details')
def game_details():
	appid = request.args.get('appid') ###
	if appid == None:
		return "No appid provided"
	try:
		variables = {}
		cur.execute("SELECT detailed_description FROM games_description WHERE appid="+str(appid))
		rows = cur.fetchall()
		print("here1")
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
		print("here2")
		cur.execute("SELECT pc_requirements,mac_requirements,linux_requirements FROM requirements WHERE appid="+str(appid))
		rows = cur.fetchall()
		if len(rows)>0:
			wr = ast.literal_eval(rows[0][0])
			mr = ast.literal_eval(rows[0][1])
			lr = ast.literal_eval(rows[0][2])
			if type(wr) == type({}):
				windows_requirements = wr['minimum']
			else:
				windows_requirements = None
			if type(mr) == type({}):
				mac_requirements = mr['minimum']
			else:
				mac_requirements = None
			if type(lr)==type({}):
				linux_requirements = lr['minimum']
			else:
				linux_requirements = None
		else:
			windows_requirements = None
			mac_requirements = None
			linux_requirements = None
		print("here3")
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
			variables["tags"] = tup[10].split(";") #list
			variables["achievements "] = tup[11]
			variables["positive_ratings"] = tup[12]
			variables["negative_ratings"] = tup[13]
			variables["average_playtime"] = tup[14]
			variables["player_count"] = tup[16]
			variables["price"] = float(tup[17])*93.13 #in inr
		else:
			variables["name"] = None
			variables["release_date"] = None
			variables["is_english"] = None
			variables["developer"] = None
			variables["platforms"] = None
			variables["required_age"] = None
			variables["genres"] = None
			variables["tags"] = None
			variables["achievements "] =  None
			variables["positive_ratings"] =  None
			variables["negative_ratings"] =  None
			variables["average_playtime"] =  None
			variables["player_count"] =  None
			variables["price"] = None
		print("here4")
		variables["description"] = description
		variables["website"] = website
		variables["steam_page"] = steam_page
		variables["windows_requirements"] = windows_requirements
		variables["linux_requirements"] = linux_requirements
		variables["mac_requirements"] = mac_requirements
		variables["appid"] = appid

		return render_template('game_details.html', user="DEFAULT",vars = variables)
	except Exception as e:
		print(e)
		return str(e)

@app.route('/reviews')
def reviews():
	appid = request.args.get('appid') ###
	page_num = request.args.get('page_num') ###
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
		return render_template('reviews.html', user="DEFAULT",reviews = rev, appid=appid)
	except Exception as e:
		print(e)
		return ""

@app.route('/screenshots')
def screenshots():
	appid = request.args.get('appid') ###
	if appid == None:
		return "No appid provided"
	try:
		cur.execute("SELECT screenshots FROM media_data WHERE appid="+str(appid))
		html = """""";
		rows = cur.fetchall()
		res = []
		if len(rows)>0:
			for ss in ast.literal_eval(rows[0][0]):
				D = {}
				D['path_full'] = ss['path_full']
				D['path_thumbnail'] = ss['path_thumbnail']
				res.append(D)
			return render_template('screenshots.html',user="DEFAULT",screenshots=res)
		else:
			return "ERROR"
	except Exception as e:
		print(e)
		return "EXCEPTION"