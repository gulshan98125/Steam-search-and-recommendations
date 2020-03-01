from flask import Flask

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key'
# config = {
#     "DEBUG": True,          # some Flask specific configs
#     "CACHE_TYPE": "simple", # Flask-Caching related configs
#     "CACHE_DEFAULT_TIMEOUT": 300
# }
# app.config.from_mapping(config)

from steam import routes