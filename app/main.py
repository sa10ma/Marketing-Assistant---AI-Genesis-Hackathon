from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated

# --- 1. FastAPI App Initialization ---

# Initialize the application without any database startup hook
app = FastAPI()

# --- 2. Template and Static File Configuration ---

# Mount the static directory to serve CSS and JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# --- 3. UI Routes ---

@app.get("/", response_class=RedirectResponse, name="home")
async def home_redirect():
    """Redirects the root path to the sign-up page."""
    return RedirectResponse(url="/signup", status_code=status.HTTP_302_FOUND)

@app.get("/signup", response_class=HTMLResponse, name="show_signup_form")
async def show_signup_form(request: Request):
    """Renders the sign-up form page."""
    # This renders templates/signup.html which extends templates/base.html
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"request": request}
    )

@app.post("/signup", name="handle_signup")
async def handle_signup(
    # We still use Form() to extract the values from the request payload
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """
    Handles the form submission. Since we have no backend, we just
    confirm receipt and redirect to the next page.
    """
    # FIX: Replaced complex, broken HTML generation with a simple redirect.
    print(f"Sign up form submitted for user: {username}. Redirecting to /agent.")
    return RedirectResponse(url="/agent", status_code=status.HTTP_302_FOUND)


# --- 4. Main Agent Route Placeholder (Success Page) ---

@app.get("/agent", response_class=HTMLResponse)
async def main_agent_page(request: Request):
    """Renders a simple placeholder success page."""
    # This renders the new success page: templates/agent_placeholder.html
    return templates.TemplateResponse(
        request=request,
        name="agent_placeholder.html",
        context={"request": request}
    )