from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import Student, User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if user_in.username and db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if user_in.role == UserRole.student and user_in.course is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course is required for students")

    user = User(
        email=user_in.email,
        password=hash_password(user_in.password),
        urole=user_in.role,
        username=user_in.username,
        name=user_in.name,
        phone=user_in.phone,
    )
    db.add(user)
    db.flush()

    if user_in.role == UserRole.student:
        db.add(
            Student(
                id=user.id,
                course=user_in.course,
                courselevel=user_in.courselevel,
                type=user_in.student_type,
                careergoal=user_in.careergoal,
                rollno=user_in.rollno,
                mneeds=user_in.mneeds,
            )
        )

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # OAuth2PasswordRequestForm uses "username" as the field name for the identifier
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user
