from fastapi import FastAPI, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession # Used for type hinting the session dependency

# Import functions and models from the new database structure
from app.database.db import create_db_and_tables, get_session
from app.database.db_schema import User # Only need User here for login/signup logic

# --- 1. FastAPI App Initialization ---

app = FastAPI()

# --- 2. Startup and Shutdown Events ---

@app.on_event("startup")
async def on_startup():
    """
    Called when the application starts up. This ensures tables are created 
    using the logic defined in app/database/db.py.
    """
    await create_db_and_tables()

# --- 3. Template and Static File Configuration ---

# Mount the static directory to serve CSS and JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")


# --- 4. UI Routes with Logic ---

@app.get("/", response_class=RedirectResponse, name="home")
async def home_redirect():
    """Redirects the root path to the sign-up page."""
    # We now redirect to the login page as it's the main entry point
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

# --- SIGNUP ROUTES ---

@app.get("/signup", response_class=HTMLResponse, name="show_signup_form")
async def show_signup_form(request: Request):
    """Renders the sign-up form page."""
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"request": request}
    )

@app.post("/signup", name="handle_signup")
async def handle_signup(
    session: Annotated[AsyncSession, Depends(get_session)], 
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """
    Handles the form submission and saves the new User to the database.
    """
    
    # 1. Check if user already exists
    result = await session.exec(select(User).where(User.username == username))
    existing_user = result.first()
    
    if existing_user:
        return HTMLResponse(content=f"User '{username}' already exists. Please choose another username.", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        # 2. Create the new User
        new_user = User(username=username, password=password)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        print(f"User {username} created successfully with ID: {new_user.id}")
        return RedirectResponse(url="/agent", status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        print(f"Database error during signup: {e}")
        await session.rollback()
        return HTMLResponse(content="An unexpected error occurred during registration.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- LOGIN ROUTES ---

@app.get("/login", response_class=HTMLResponse, name="show_login_form")
async def show_login_form(request: Request):
    """Renders the login form page."""
    # Passing 'error=None' initially so the template renders correctly
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"request": request, "error": None}
    )


@app.post("/login", name="handle_login")
async def handle_login(
    request: Request, # Need Request here to re-render the template on failure
    session: Annotated[AsyncSession, Depends(get_session)], 
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """
    Handles login form submission, checks credentials, and redirects on success.
    """
    
    # Check if a user exists with BOTH the matching username AND password
    # NOTE: In a production application, you MUST hash and salt passwords (e.g., using passlib)
    result = await session.exec(
        select(User).where(User.username == username, User.password == password)
    )
    user = result.first()
    
    if user:
        # Successful login
        # TODO: Implement session management (e.g., set a cookie) here
        return RedirectResponse(url="/agent", status_code=status.HTTP_302_FOUND)
    else:
        # Failed login, re-render the login page with an error message
        error_message = "Invalid username or password. Please try again."
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"request": request, "error": error_message},
            status_code=status.HTTP_401_UNAUTHORIZED # 401 status for unauthorized access attempt
        )


# --- 5. Success Placeholder Route ---

@app.get("/agent", response_class=HTMLResponse)
async def main_agent_page(request: Request):
    """Renders the success/placeholder page."""
    return templates.TemplateResponse(
        request=request,
        name="agent_placeholder.html",
        context={"request": request}
    )