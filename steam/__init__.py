from flask import Flask

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key'

from steam import routes