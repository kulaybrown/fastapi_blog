from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

posts: list[dict] = [
    {
        "id": 1,
        "title": "First Post",
        "content": "This is the content of the first post.",
        "date_posted": "2024-06-05",
        "author": "user 1"
    },
    {
        "id": 2,
        "title": "Second Post",
        "content": "This is the content of the second post.",
        "date_posted": "2024-06-06",
        "author": "user 2"
    },
    {
        "id": 3,
        "title": "Third Post",
        "content": "This is the content of the third post.",
        "date_posted": "2024-06-07",
        "author": "user 2"
    }
    
]



@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(
        request, 
        "home.html", 
        {"request": request, "posts": posts, "title": "Home"}
    )

@app.get("/posts/{post_id}", include_in_schema=False)
def get_post(request: Request, post_id: int):
    for post in posts:
        if post["id"] == post_id:
            return templates.TemplateResponse(
                request, 
                "post.html", 
                {"request": request, "posts": [post], "title":  post['title'] }
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/posts/author/{author}", include_in_schema=False)
def get_posts_by_author(request: Request, author: str):
    author_posts = [post for post in posts if post["author"] == author]
    if not author_posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posts not found for this author")
    return templates.TemplateResponse(
        request, 
        "post.html", 
        {"request": request, "posts": author_posts, "title":  f"Posts by {author}" }
    )


@app.get("/api/posts")
def get_posts():
    return posts

@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    for post in posts:
        if post["id"] == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

@app.get("/api/posts/author/{author}")
def get_posts_by_author(author: str):
    author_posts = [post for post in posts if post["author"] == author]
    if not author_posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posts not found for this author")
    return author_posts


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail 
        else "An error occurred, please try again."
    )
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
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