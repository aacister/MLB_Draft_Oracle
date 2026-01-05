import os
from backend.data.postgresql.connection import get_engine
from backend.data.postgresql.models import Base

os.environ['DEPLOYMENT_ENVIRONMENT'] = 'LAMBDA'
os.environ['USE_POSTGRESQL'] = 'true'
os.environ['DB_SECRET_ARN'] = 'arn:aws:secretsmanager:...'  # Your ARN



engine = get_engine()
Base.metadata.create_all(bind=engine)
print("✓ Tables created successfully")