from fastapi import FastAPI

# Import API routers
from inventory import router as inventory_router
from orders import router as orders_router

# -------------------------------------------------------------------
# Create FastAPI application
# -------------------------------------------------------------------

app = FastAPI(
    title="Warehouse Management System API",
    description="REST API for inventory management and order processing.",
    version="1.0.0"
)

# -------------------------------------------------------------------
# Register API Routes
# -------------------------------------------------------------------

app.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Inventory"]
)

app.include_router(
    orders_router,
    prefix="/orders",
    tags=["Orders"]
)

# -------------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------------

@app.get("/")
def root():
    """
    Simple endpoint to verify that the API is running.
    """

    return {
        "message": "Warehouse Management System API is running.",
        "status": "online"
    }

# -------------------------------------------------------------------
# Application Startup Event
# -------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """
    Executes once when the application starts.

    In a production application this is where you might:
    - Test the PostgreSQL connection
    - Connect to Redis
    - Load configuration
    - Initialize logging
    """

    print("Warehouse Management System started successfully.")