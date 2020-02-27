import os
""" API config File """
from steam.constants import *
class Config(object):
    """ Parent configuration class """
    DEBUG = False
    TESTING = False
    Database_Url = os.getenv("Main_Database")
    SECRET_KEY = SECRET
class DevelopmentConfig(Config):
    """ Configuration for development environment """
    DEBUG = True
    Database_Url = Main_Database
class TestingConfig(Config):
    """ Configuratio(env) zonecc@trevor:/var/codezonecc/My Diary$n for the testing environment """
    TESTING = True
    DEBUG = True
    Database_Url = Test_Database
#for heroku in case I decide to host the app but that's it
class ProductionConfig(Config):
    """ Configuration for the production environment """
    DEBUG = False
    TESTING = False
    Database_Url = DATABASE_URL
app_config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}