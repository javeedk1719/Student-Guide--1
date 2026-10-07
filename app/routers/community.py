from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import CommunityPost, User
from app.schemas.community import CommunityUserOut, PostCreate, PostOut

router = APIRouter(prefix="/api/community", tags=["Community"])


def _relation(my_year: Optional[int], their_year: Optional[int]) -> Optional[str]:
    if not my_year or not their_year:
        return None
    if their_year > my_year:
        return "senior"
    if their_year < my_year:
        return "junior"
    return "peer"


@router.get("/users", response_model=List[CommunityUserOut])
def discover_users(role: Optional[str] = Query(default=None, max_length=80),
                   relation: Optional[str] = Query(default=None, pattern="^(senior|junior|peer)$"),
                   same_college: bool = True,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(User).options(joinedload(User.community_profile)).filter(User.id != user.id)
    if same_college:
        query = query.filter(func.lower(User.college) == user.college.strip().lower())
    if role:
        query = query.filter(User.career_role == role)

    my_year = user.community_profile.study_year if user.community_profile else None
    result = []
    for u in query.order_by(User.name).limit(200).all():
        cp = u.community_profile
        year = cp.study_year if cp else None
        rel = _relation(my_year, year)
        if relation and rel != relation:
            continue
        result.append(CommunityUserOut(
            id=u.id, name=u.name, college=u.college, career_role=u.career_role,
            skill_level=u.skill_level, study_year=year, relation=rel,
            bio=cp.bio if cp else None, interests=(cp.interests or []) if cp else []))
    return result[:100]


def _post_out(post: CommunityPost, me: User) -> PostOut:
    return PostOut(id=post.id, author_id=post.author_id, author_name=post.author.name,
                   author_role=post.author.career_role, college=post.college, type=post.type,
                   title=post.title, body=post.body, role_tag=post.role_tag,
                   created_at=post.created_at, is_mine=post.author_id == me.id)


@router.get("/posts", response_model=List[PostOut])
def list_posts(role: Optional[str] = Query(default=None, max_length=80),
               type: Optional[str] = Query(default=None, pattern="^(question|resource|project_idea|discussion)$"),
               same_college: bool = True,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CommunityPost).options(joinedload(CommunityPost.author))
    if same_college:
        query = query.filter(func.lower(CommunityPost.college) == user.college.strip().lower())
    if role:
        query = query.filter(CommunityPost.role_tag == role)
    if type:
        query = query.filter(CommunityPost.type == type)
    posts = query.order_by(CommunityPost.created_at.desc()).limit(50).all()
    return [_post_out(p, user) for p in posts]


@router.post("/posts", response_model=PostOut, status_code=201)
def create_post(data: PostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = CommunityPost(author_id=user.id, college=user.college.strip(), type=data.type,
                         title=data.title, body=data.body, role_tag=data.role_tag or None)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_out(post, user)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if post is None or post.author_id != user.id:
        raise HTTPException(status_code=404, detail="Post not found.")
    db.delete(post)
    db.commit()
