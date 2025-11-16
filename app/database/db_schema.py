from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

# --- 1. User Model (Authentication/Account) ---

class UserBase(SQLModel):
    """Base fields for a User account."""
    username: str = Field(index=True, unique=True)
    password: str 

class User(UserBase, table=True):
    """The User model, linked to the 'user' table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Define the relationship to the UserProfile model
    profile: Optional["UserProfile"] = Relationship(back_populates="user")


# --- 2. User Profile Model (Placeholder) ---

class UserProfileBase(SQLModel):
    """Base fields for a User's default marketing context."""
    company_name: str 
    target_audience_persona: str 

class UserProfile(UserProfileBase, table=True):
    """The UserProfile model, linked to the 'userprofile' table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key (FK) to link back to the User. unique=True enforces the one-to-one
    user_id: int = Field(foreign_key="user.id", unique=True) 

    # Define the relationship back to the User model
    user: User = Relationship(back_populates="profile")