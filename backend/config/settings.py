import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

class Settings:
    # Deployment environment
    DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEV")
    
    # API Keys
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Database paths based on environment
    if DEPLOYMENT_ENV == "LAMBDA":
        SQLITE_DB_PATH = "/tmp/mlbdraftoracle.db"
        MEMORY_DIR = "/tmp/memory"
    else:
        SQLITE_DB_PATH = "/app/sqlite-data/mlbdraftoracle.db"
        MEMORY_DIR = "/app/memory"
    
    # MCP server paths
    MCP_WORKING_DIR = "/app" if DEPLOYMENT_ENV == "LAMBDA" else os.getcwd()
    
    @property
    def is_dev(self):
        return self.DEPLOYMENT_ENV == "DEV"
    
    @property
    def is_lambda(self):
        return self.DEPLOYMENT_ENV == "LAMBDA"
    
    @property
    def is_production(self):
        return self.DEPLOYMENT_ENV == "PRODUCTION"

settings = Settings()