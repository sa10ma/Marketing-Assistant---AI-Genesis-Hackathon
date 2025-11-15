from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Marketing Agent Hackathon App",
    #on_startup=[create_db_and_tables] # Run table creation when app starts
)


# Mount Static Files (for CSS/JS) - URL path /static maps to the 'static' directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Template Engine - Looks for HTML files in the 'templates' directory
templates = Jinja2Templates(directory="templates")

# --- 3. Root Routes (UI Pages) ---

# Renders the main input form page (using the name "show_input_form" for url_for)
@app.get("/", response_class=HTMLResponse, name="show_input_form")
async def show_input_form(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="input.html", 
        context={"request": request, "post_content": ""}
    )

# Renders the login page (using the name "show_login" for url_for)
# @app.get("/login", response_class=HTMLResponse, name="show_login")
# async def show_login(request: Request):
#     return templates.TemplateResponse(
#         request=request, name="login.html", context={"request": request}
#     )


# --- 4. API/Form Submission Routes ---

# Example: POST route to handle form submission and generate content
# @app.post("/generate", response_class=HTMLResponse)
# async def handle_generate_post(
#     request: Request,
#     # ... Form() data inputs ...
#     # session: Session = Depends(get_session) # Example DB dependency
# ):
#     # 1. Validate inputs (FastAPI does this automatically)
#     # 2. Call RAG Agent (e.g., generated_post = generate_content(...))
#     # 3. Save Post History to PostgreSQL
#     # 4. Re-render the input page with the result
#     pass