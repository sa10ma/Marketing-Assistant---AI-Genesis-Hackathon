import os
from typing import Annotated
from contextlib import asynccontextmanager
from datetime import timedelta, timezone
import datetime 

from fastapi import FastAPI, Depends, Request, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from sqlmodel import select

from app.database.db import create_db_and_tables, SessionDep
from app.services.authentication import (
    create_access_token, 
    ActiveUser, 
    ActiveUserID, # <-- IMPORTED ActiveUserID
    JWT_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    set_auth_cookie
)
from app.database.db_schema import User, UserProfile 
from app.qdrant_rag import create_qdrant_collection


# --- Application Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables before the app starts serving requests
    await create_db_and_tables()
    create_qdrant_collection()
    yield

app = FastAPI(lifespan=lifespan)

# --- Templates and Static Files ---

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Routes ---

# 1. Home Page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request): 
    """Renders the home page, showing the user's status."""
    return templates.TemplateResponse(
        request=request, 
        name="index.html",
        context={"request": request}
    )

# 1b. Agent Placeholder Page (Fake Agent Page)
@app.get("/agent", response_class=HTMLResponse)
async def show_agent_placeholder(
    request: Request, 
    user: ActiveUser,
    session: SessionDep):
    """
    Renders the temporary agent page after profile setup.
    Requires authentication via ActiveUser dependency.
    """
    result = await session.exec(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.one_or_none()
    
    return templates.TemplateResponse(
        request=request, 
        name="agent_placeholder.html",
        context={"request": request, "user_id": user.id, "profile":profile}
    )

# 1c. Sign Up Page
@app.get("/signup", response_class=HTMLResponse)
async def show_signup_form(request: Request):
    """Renders the sign-up form."""
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"request": request, "error": None}
    )

@app.post("/signup")
async def handle_signup(
    request: Request, 
    session: SessionDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()]
):
    """
    Handles sign-up form submission, creates a new user, 
    logs them in automatically, and redirects to /profile.
    """
    
    # Check if user already exists
    existing_user_statement = select(User).where(User.username == username)
    existing_user = (await session.exec(existing_user_statement)).one_or_none()
    
    if existing_user:
        return templates.TemplateResponse(
            request=request, 
            name="signup.html", 
            context={"request": request, "error": "Username already taken."}
        )
    
    # 1. Create new user
    new_user = User(username=username, password=password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # 2. Prepare Redirect Response
    response = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    
    # 3. Log user in by generating a JWT token and setting a cookie
    response = set_auth_cookie(response, new_user.id) 
    
    return response

# 2. Login Page
@app.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    """Renders the login form."""
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"request": request, "error": None}
    )

@app.post("/login")
async def handle_login(
    request: Request, 
    session: SessionDep, 
    username: Annotated[str, Form()],
    password: Annotated[str, Form()]
):
    """Handles login form submission, creates a JWT, and sets a cookie."""
    
    # 1. Look up user by username and password
    user_statement = select(User).where(User.username == username, User.password == password)
    user_result = await session.exec(user_statement)
    user = user_result.one_or_none()

    if user:
        # 2. Prepare Redirect Response
        response = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
        
        # 3. Set the cookie
        response = set_auth_cookie(response, user.id) 
        
        return response
    else:
        # 3. Show error.
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"request": request, "error": "Invalid username or password"}
        )

# 3. Profile Setup Page
@app.get("/profile", response_class=HTMLResponse)
async def show_profile_form(
    request: Request,
    session: SessionDep, 
    user: ActiveUser 
):
    """Renders the profile form, pre-filling data if it exists."""
    
    # Fetch existing profile data for the current user
    result = await session.exec(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.one_or_none()
    
    # Prepare context data
    context = {
        "request": request,
        "profile": profile, 
        "user_id": user.id
    }

    # Render the template
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context=context
    )

@app.post("/profile")
async def handle_profile_submit(
    session: SessionDep, 
    user_id: ActiveUserID, # <-- NEW: Injecting the reliably loaded ID from the token
    company_name: Annotated[str, Form()],
    product_description: Annotated[str, Form()],
    target_audience: Annotated[str, Form()],
    tone_of_voice: Annotated[str, Form()],
):
    """
    Handles profile form submission (creation or update).
    Re-issues a fresh cookie to stabilize the session before redirecting.
    """
    
    # 1. Check if a profile already exists
    # Using the reliably loaded user_id
    result = await session.exec(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.one_or_none()
    
    if profile:
        # Update existing profile
        profile.company_name = company_name
        profile.product_description = product_description
        profile.target_audience = target_audience
        profile.tone_of_voice = tone_of_voice
    else:
        # Create new profile
        profile = UserProfile(
            user_id=user_id, # Using the reliably loaded user_id
            company_name=company_name,
            product_description=product_description,
            target_audience=target_audience,
            tone_of_voice=tone_of_voice,
        )
    
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    
    # 2. Prepare Redirect Response to /agent
    response = RedirectResponse(url="/agent", status_code=status.HTTP_303_SEE_OTHER)
    
    # 3. Re-issue a fresh JWT cookie for the subsequent GET /agent request
    response = set_auth_cookie(response, user_id)
    
    return response

# 4. Logout Route
@app.post("/logout")
async def handle_logout(response: Response): 
    """Clears the JWT cookie and redirects to login."""
    # 1. Delete the JWT cookie (which holds the token)
    response.delete_cookie(key=JWT_COOKIE_NAME)
    
    # 2. Redirect to the login page
    return RedirectResponse(
        url="/login", 
        status_code=status.HTTP_303_SEE_OTHER
    )