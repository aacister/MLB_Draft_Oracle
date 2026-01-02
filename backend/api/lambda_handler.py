from mangum import Mangum
from backend.api.main import app

# Wrap FastAPI app with Mangum for Lambda compatibility
handler = Mangum(app, lifespan="off")