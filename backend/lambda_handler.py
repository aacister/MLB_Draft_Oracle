from mangum import Mangum
from backend.api.main import app

# Create the Lambda handler
handler = Mangum(app, lifespan="off")