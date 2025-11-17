import os
import secrets
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone 

from jose import JWTError, jwt
from fastapi import Depends, Request, HTTPException, status, Response
from sqlmodel import select
from app.database.db_schema import User 
from app.database.db import SessionDep

import bcrypt

# --- JWT Configuration 
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32)) 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 
JWT_COOKIE_NAME = "access_token" 

# --- Password Hasher ---
class PasswordHasher:
    """Utility class for hashing and verifying passwords."""
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
        
# --- JWT Utility Function ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT with the user data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta 
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) 
    
    to_encode.update({"exp": expire, "sub": "access_token"})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
    
# --- Utility to set cookie ---

def set_auth_cookie(response: Response, user_id: int):
    """Generates a new token and sets the JWT cookie on the response."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user_id}, expires_delta=access_token_expires
    )
    
    # Calculate cookie expiration time
    cookie_expires_dt = datetime.now(timezone.utc) + access_token_expires 
    
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=access_token,
        httponly=True, 		
        secure=False, 		
        samesite="Lax",
        # Set cookie expiration based on token expiration
        expires=int(cookie_expires_dt.timestamp())
    )
    return response

# --- Authentication Dependencies ---

async def get_user_id_from_token(request: Request) -> int:
    """
    Reads, decodes, and validates the JWT from the cookie or header,
    returning ONLY the user ID from the payload (no database lookup).
    """
    
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        # API call: Token is in the Authorization header
        token = auth_header.split(" ")[1]
    else:
        # Browser call: Check for token in the cookie
        token = request.cookies.get(JWT_COOKIE_NAME)

    if not token:
        # Redirect to login if no token is found in header or cookie
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Not authenticated (Missing Bearer Token or Cookie)",
            headers={"Location": "/login"}
        )

    try:
        # 1. Decode and verify the JWT signature and claims
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Extract the user ID 
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            raise JWTError("User ID not found in token payload")
        
        return user_id

    except JWTError:
        # This catches token tampering, expiration, and invalid structure
        # We redirect to /logout to properly clear the invalid cookie
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Invalid or expired token",
            headers={"Location": "/login"} 
        )


async def get_current_user(
    session: SessionDep,
    user_id: Annotated[int, Depends(get_user_id_from_token)]
) -> User:
    """
    Retrieves the full User object from the database using the ID from the token.
    """
    # 3. Retrieve the user from the database
    user_statement = select(User).where(User.id == user_id)
    user_result = await session.exec(user_statement)
    user = user_result.one_or_none()
    
    if not user:
         raise HTTPException(status_code=401, detail="Unauthorized - User not found")

    return user # Return the full User object


# Type hint for the dependency result (returns the whole User object)
ActiveUser = Annotated[User, Depends(get_current_user)]
# Type hint for the dependency result (returns just the loaded ID)
ActiveUserID = Annotated[int, Depends(get_user_id_from_token)]