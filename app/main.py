from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

# --- 1. FastAPI App Initialization ---

app = FastAPI()

# --- 2. Template and Static File Configuration ---

# Define the base directory of the application relative to this script
BASE_DIR = Path(__file__).resolve().parent.parent

# Use absolute paths for templates and static files to ensure Docker path resolution works
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Mount the static directory to serve CSS and JS files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# --- 3. UI Routes ---

@app.get("/", response_class=RedirectResponse, name="home")
async def home_redirect():
    """Redirects the root path to the sign-up page."""
    # This ensures navigating to http://localhost:8000/ works
    return RedirectResponse(url="/signup", status_code=status.HTTP_302_FOUND)

@app.get("/signup", response_class=HTMLResponse, name="show_signup_form")
async def show_signup_form(request: Request):
    """
    Renders the sign-up form page. This is the only critical view 
    needed to test the frontend and template loading.
    """
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"request": request}
    )