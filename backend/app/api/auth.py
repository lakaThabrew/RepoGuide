from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from app.database.supabase import get_supabase
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])

class AuthBody(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class ProfileBody(BaseModel):
    full_name: str
    username: str

class ResetBody(BaseModel):
    email: str
class ConfirmBody(BaseModel):
    token: str

def get_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    return authorization.split(" ")[1]

@router.post("/signup")
def signup(body: AuthBody):
# Password validation removed (handled by Supabase)
    import uuid
    sb = get_supabase()
    try:
        res = sb.auth.sign_up({"email": body.email, "password": body.password})
        if res.user:
            username = f"{body.email.split('@')[0]}-{str(uuid.uuid4())[:8]}"
            sb.table("profiles").upsert({
                "id": res.user.id,
                "full_name": body.full_name or "",
                "username": username
            }).execute()
        
        # Depending on supabase version, res might not have a dict directly
        # res.user and res.session are objects. We can serialize them.
        return {
            "user": res.user.model_dump() if res.user else None, 
            "session": res.session.model_dump() if res.session else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signin")
def signin(body: AuthBody):
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "user": res.user.model_dump() if res.user else None, 
            "session": res.session.model_dump() if res.session else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset-password")
def reset_password(body: ResetBody):
    sb = get_supabase()
    try:
        sb.auth.reset_password_email(body.email)
        return {"message": "Email sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.post("/confirm")
def confirm_email(body: ConfirmBody):
    sb = get_supabase()
    try:
        # Verify the signup OTP/token (Supabase method may vary)
        verification = sb.auth.verify_otp(token=body.token, type="signup") 
        return {"detail": "Email confirmed", "verification": verification}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/profile")
def get_profile(token: str = Depends(get_token)):
    sb = get_supabase()
    try:
        res = sb.auth.get_user(token)
        if not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        profile_res = sb.table("profiles").select("*").eq("id", res.user.id).execute()
        return {
            "user": res.user.model_dump(), 
            "profile": profile_res.data[0] if profile_res.data else {}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/profile")
def update_profile(body: ProfileBody, token: str = Depends(get_token)):
    sb = get_supabase()
    try:
        res = sb.auth.get_user(token)
        if not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        sb.table("profiles").upsert({
            "id": res.user.id,
            "full_name": body.full_name,
            "username": body.username
        }).execute()
        return {"message": "Profile updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
