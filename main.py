from typing import Annotated

from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.exceptions import RequestValidationError

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, PostUpdate, UserResponse, UserCreate, UserUpdate

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

# posts: list[dict] = [
#     {
#         "id": 1,
#         "title": "First Post",
#         "content": "This is the content of the first post.",
#         "date_posted": "2024-06-05",
#         "author": "user 1"
#     },
#     {
#         "id": 2,
#         "title": "Second Post",
#         "content": "This is the content of the second post.",
#         "date_posted": "2024-06-06",
#         "author": "user 2"
#     },
#     {
#         "id": 3,
#         "title": "Third Post",
#         "content": "This is the content of the third post.",
#         "date_posted": "2024-06-07",
#         "author": "user 2"
#     }
    
# ]



@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    results = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = results.scalars().all()
    return templates.TemplateResponse(
        request, 
        "home.html", 
        {"posts": posts, "title": "Home"}
    )

@app.get("/posts/{post_id}", include_in_schema=False)
async def get_post(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return templates.TemplateResponse(
            request, 
            "post.html", 
            {"post": post, "title":  post.title }
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def get_user_posts_page(
    request: Request, 
    user_id: int, 
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = await db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"}
    )


@app.post(
    "/api/users", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already exists"
        )

    result = await db.execute(
        select(models.User).where(models.User.email == user.email)
    )

    existing_email = result.scalars().first()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already exists"
        )

    new_user = models.User(
        username=user.username,
        email=user.email,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    existing_user = result.scalars().first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_update_data = user.model_dump(exclude_unset=True)
    for field, value in user_update_data.items():
        setattr(existing_user, field, value)

    await db.commit()
    await db.refresh(existing_user)
    return existing_user

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    existing_user = result.scalars().first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    await db.delete(existing_user)
    await db.commit()


# @app.get("/posts/author/{author}", include_in_schema=False)
# def get_posts_by_author(request: Request, author: str):
#     author_posts = [post for post in posts if post["author"] == author]
#     if not author_posts:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posts not found for this author")
#     return templates.TemplateResponse(
#         request, 
#         "post.html", 
#         {"request": request, "posts": author_posts, "title":  f"Posts by {author}" }
#     )


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts

@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == new_post.id))
    return result.scalars().first()

@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")



@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(post_id: int, post_update: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post_update.title is not None:
        post.title = post_update.title
    if post_update.content is not None:
        post.content = post_update.content
    await db.commit()
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post.id))
    return result.scalars().first()


@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def patch_post(post_id: int, post_update: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post_update_data = post_update.model_dump(exclude_unset=True)
    for field, value in post_update_data.items():
        setattr(post, field, value)
    await db.commit()
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post.id))
    return result.scalars().first()



@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        await db.delete(post)
        await db.commit()
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

# @app.get("/api/posts/author/{author}")
# def get_posts_by_author(author: str):
#     author_posts = [post for post in posts if post["author"] == author]
#     if not author_posts:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posts not found for this author")
#     return author_posts


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail 
        else "An error occurred, please try again."
    )
    
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )
    

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request data. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )