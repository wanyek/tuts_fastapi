from typing import List, Optional
from fastapi import Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func
from ..database import get_db
from .. import models, schemas, oauth2

router = APIRouter(prefix="/posts", tags=["Posts"])


# -----------------------------------------------------------------------------
@router.get("", response_model=List[schemas.PostOut])
def get_posts(
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
    limit: int = 5,
    skip: int = 0,
    search: Optional[str] = "",
):

    posts = (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Post.id == models.Vote.post_id, isouter=True)
        .group_by(models.Post.id)
        .filter(models.Post.title.contains(search.lower().strip()))
        .limit(limit)
        .offset(skip)
        .all()
    )
    return posts


# -----------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    created_post = models.Post(owner_id=current_user.id, **post.dict())
    db.add(created_post)
    db.commit()
    db.refresh(created_post)

    return created_post


# -----------------------------------------------------------------------------
@router.get(
    "/{id}",
    response_model=schemas.PostOut,
)
def get_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):

    post = (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Post.id == models.Vote.post_id, isouter=True)
        .group_by(models.Post.id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} was not found",
        )
    return post


# -----------------------------------------------------------------------------
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):

    post = db.query(models.Post).filter(models.Post.id == id)

    post_val = post.first()

    if post_val == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} does not exist",
        )
    print(post_val.id)
    print(current_user.id)
    if post_val.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )

    post.delete(synchronize_session=False)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------------------------------------
@router.put("/{id}", response_model=schemas.Post)
def update_post(
    id: int,
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):

    post_query = db.query(models.Post).filter(models.Post.id == id)

    post_val = post_query.first()

    if post_val == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post with id: {id} does not exits",
        )

    if post_val.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )

    post_query.update(post.dict(), synchronize_session=False)

    db.commit()

    return post_query.first()
