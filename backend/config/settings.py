
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
    
    # S3 Configuration for SQLite persistence (keep for backwards compatibility)
    S3_BUCKET = os.getenv("S3_DB_BUCKET", "mlbdraftoracle-sqlite-425865275846")
    S3_DB_KEY = "mlbdraftoracle.db"
    S3_MEMORY_BUCKET = os.getenv("S3_MEMORY_BUCKET", "mlbdraftoracle-memory-425865275846")
    
    # RDS PostgreSQL Configuration
    DB_SECRET_ARN = os.getenv("DB_SECRET_ARN")  # ARN of secret in Secrets Manager
    
    # Database selection based on environment
    USE_POSTGRESQL = os.getenv("USE_POSTGRESQL", "false").lower() == "true"
    
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
    
    @property
    def use_rds(self):
        """Determine if we should use RDS PostgreSQL"""
        # Use RDS if:
        # 1. Explicitly enabled via USE_POSTGRESQL env var, OR
        # 2. In Lambda/Production environment AND DB_SECRET_ARN is set
        if self.USE_POSTGRESQL:
            return True
        if (self.is_lambda or self.is_production) and self.DB_SECRET_ARN:
            return True
        return False

settings = Settings()