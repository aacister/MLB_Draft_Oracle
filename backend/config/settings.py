import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

class Settings:
    # Deployment environment
    DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEV")
    
    # API Keys
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # AWS Configuration
    AWS_REGION = os.getenv("AWS_REGION_NAME", "us-east-2")
    
    # RDS PostgreSQL Configuration (PRIMARY DATABASE)
    # Single DB_URL replaces DB_SECRET_ARN
    DB_URL = os.getenv("DB_URL")
    
    # FORCE PostgreSQL usage - always use RDS
    USE_POSTGRESQL = True
    
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
    
    @property
    def use_rds(self):
        """Always use RDS PostgreSQL"""
        return True

settings = Settings()