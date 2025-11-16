from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

# --- User Model ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str # NOTE: In a real app, this would be hashed

    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    
# --- UserProfile Model ---

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Ensure only one profile per user
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    
    # MARKETING INPUT FIELDS
    company_name: str
    product_description: str
    target_audience: str
    tone_of_voice: str
    
    # Relationships
    user: User = Relationship(back_populates="profile")