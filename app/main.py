from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated, List, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession 
from pydantic import ValidationError # Added for optional error handling

# Import functions and models from the new database structure
from app.database.db import create_db_and_tables, get_session
from app.database.db_schema import User, UserProfile # Import UserProfile
from app.qdrant_rag import create_qdrant_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables before the app starts serving requests
    await create_db_and_tables()
    create_qdrant_collection()

    yield
    # Shutdown: (No specific shutdown logic needed for this simple case)

app = FastAPI(lifespan=lifespan)

# --- 3. Template and Static File Configuration ---

# Mount the static directory to serve CSS and JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# --- TEMP: Global Variable to simulate User ID until session management is built ---
# NOTE: In a production application, this MUST be replaced with proper session/cookie management.
# For now, we'll use a hardcoded ID for testing data persistence.
ACTIVE_USER_ID = 1

# --- 4. UI Routes with Logic ---

@app.get("/", response_class=RedirectResponse, name="home")
async def home_redirect():
    """Redirects the root path to the login page."""
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
    request: Request,
):
    """
    Handles the form submission and saves the new User to the database.
    """
    global ACTIVE_USER_ID
    
    # 1. Check if user already exists
    result = await session.exec(select(User).where(User.username == username))
    existing_user = result.first()
    
    if existing_user:
        error_message = f"User '{username}' already exists. Please choose another username."
        return templates.TemplateResponse(
            request=request, 
            name="signup.html", 
            context={"request": request, "error": error_message},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 2. Create the new User
        new_user = User(username=username, password=password)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # TEMP: Set the global user ID for testing persistence
        ACTIVE_USER_ID = new_user.id
        
        print(f"User {username} created successfully with ID: {new_user.id}")
        return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        print(f"Database error during signup: {e}")
        await session.rollback()
        return HTMLResponse(content="An unexpected error occurred during registration.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- LOGIN ROUTES ---

@app.get("/login", response_class=HTMLResponse, name="show_login_form")
async def show_login_form(request: Request):
    """Renders the login form page."""
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"request": request, "error": None}
    )


@app.post("/login", name="handle_login")
async def handle_login(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)], 
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """
    Handles login form submission, checks credentials, and redirects on success.
    """
    global ACTIVE_USER_ID
    
    result = await session.exec(
        select(User).where(User.username == username, User.password == password)
    )
    user = result.first()
    
    if user:
        # TEMP: Set the global user ID for testing persistence
        ACTIVE_USER_ID = user.id 
        print(f"User ID {user.id} logged in successfully. Active ID set.")
        return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)
    else:
        error_message = "Invalid username or password. Please try again."
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"request": request, "error": error_message},
            status_code=status.HTTP_401_UNAUTHORIZED
        )


# --- 5. User Profile / Core App Route ---

@app.get("/profile", response_class=HTMLResponse, name="show_profile_form")
async def show_profile_form(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Renders the profile form, pre-filling data if a profile already exists for the active user.
    """
    # TEMP: Using ACTIVE_USER_ID until proper session management is in place
    user_id = ACTIVE_USER_ID
    
    profile_data: Optional[UserProfile] = None
    
    if user_id:
        result = await session.exec(select(UserProfile).where(UserProfile.user_id == user_id))
        profile_data = result.first()
        print("result.first ==============", profile_data)
        
    context = {
        "request": request,
        "profile": profile_data, # Pass existing profile data if found
    }
    
    return templates.TemplateResponse(
        request=request,
        name="user_profile_form.html",
        context=context
    )

@app.post("/profile", name="handle_profile_submit")
async def handle_profile_submit(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    company_name: Annotated[str, Form()],
    product_description: Annotated[str, Form()],
    target_audience: Annotated[str, Form()],
    tone_of_voice: Annotated[str, Form()],
):
    """
    Handles the submission of the user profile form, creating or updating the profile.
    """
    # TEMP: Using ACTIVE_USER_ID until proper session management is in place
    user_id = ACTIVE_USER_ID
    
    if not user_id:
        # Should not happen if login/signup was successful, but a safeguard
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    try:
        # 1. Check if a profile already exists for this user
        result = await session.exec(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.first()

        form_data = {
            "company_name": company_name,
            "product_description": product_description,
            "target_audience": target_audience,
            "tone_of_voice": tone_of_voice,
        }
        
        if profile:
            # 2. Update existing profile
            for key, value in form_data.items():
                setattr(profile, key, value)
            session.add(profile)
            message = "Profile updated successfully!"
        else:
            # 3. Create new profile
            new_profile = UserProfile(user_id=user_id, **form_data)
            session.add(new_profile)
            message = "Profile created successfully!"

        await session.commit()
        
        # Redirect back to the form with a success message (optional: fetch data for prefill)
        return RedirectResponse(url="/profile", status_code=status.HTTP_302_SEE_OTHER)

    except Exception as e:
        print(f"Database error during profile save: {e}")
        await session.rollback()
        # Re-render form with error state
        context = {
            "request": request,
            "error": "Failed to save profile data due to a server error.",
            "form_data": form_data # Pass back submitted data to prefill fields
        }
        return templates.TemplateResponse(
            request=request, 
            name="user_profile_form.html", 
            context=context,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# # --- 6. Database Data View (Debug/Demo) ---

# @app.get("/users", response_class=HTMLResponse, name="show_users")
# async def show_users(
#     request: Request,
#     session: Annotated[AsyncSession, Depends(get_session)], 
# ):
#     """
#     Fetches and displays all registered users and their profiles from the database.
#     """
#     # Fetch all users
#     result = await session.exec(select(User, UserProfile).join(UserProfile, isouter=True))
#     rows: List[tuple[User, Optional[UserProfile]]] = result.all()
    
#     user_data = []
#     for user, profile in rows:
#         user_data.append({
#             "id": user.id,
#             "username": user.username,
#             "password": user.password,
#             "profile": profile, # Pass the profile object directly
#         })

#     return templates.TemplateResponse(
#         request=request,
#         name="user_list.html",
#         context={"request": request, "users": user_data}
#     )