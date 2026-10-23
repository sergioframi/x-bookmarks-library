from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any,Literal
from zipfile import BadZipFile,ZipFile

from fastapi import BackgroundTasks,Depends,FastAPI,Header,HTTPException,Query,Request,Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict,Field

from .classifier import normalize_tag,rebuild_search_documents
from .config import ensure_session_secret,settings
from .db import connect,initialize_schema
from .model_cache import model_cache_status
from .progress import (EnrichmentBusy,acquire_enrichment_lock,create_enrichment_job,
    enrichment_status,recover_interrupted,release_enrichment_lock)
from .search import SearchEngine,filter_candidates
from .security import create_session,hash_password,read_session,verify_password
from .taxonomy_discovery import (apply_discovery,discover_taxonomy,
    refresh_prototypes_from_feedback,taxonomy_status)
from .xarchive_sync import (MAX_ARCHIVE_BYTES,authenticate_device,bootstrap_archive,
    create_pairing_code,pair_device,process_sync,run_incremental_embeddings)


STATIC=Path(__file__).parent/"static"
app=FastAPI(title="Biblioteca privada de bookmarks",version="1.0.0",docs_url=None,redoc_url=None)


@app.on_event("startup")
def startup():
    settings.database_path.parent.mkdir(parents=True,exist_ok=True)
    ensure_session_secret()
    with connect(settings.database_path) as connection:
        initialize_schema(connection)
        recover_interrupted(connection)
        if settings.password_hash:
            connection.execute("""INSERT OR IGNORE INTO app_users(username,password_hash,session_version)
              VALUES(?,?,1)""",(settings.username,settings.password_hash))
        connection.commit()


@app.middleware("http")
async def security_headers(request:Request,call_next):
    if request.url.path=="/api/v1/xarchive/sync":
        length=request.headers.get("content-length")
        if length and int(length)>MAX_ARCHIVE_BYTES*2:
            return Response("payload demasiado grande",status_code=413)
    response=await call_next(request)
    response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY",
      "Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(), microphone=(), geolocation=()",
      "Content-Security-Policy":"default-src 'self'; img-src 'self' https: data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"})
    return response


def session_data(request:Request)->dict:
    data=read_session(request.cookies.get("xb_session"),settings.session_secret)
    if not data: raise HTTPException(401,"Autenticación requerida")
    with connect(settings.database_path) as connection:
        user=connection.execute("SELECT session_version FROM app_users WHERE username=?",(data.get("sub"),)).fetchone()
    if not user or int(data.get("sv",1))!=int(user["session_version"]):
        raise HTTPException(401,"La sesión ya no es válida")
    return data


def csrf_session(request:Request,x_csrf_token:str|None=Header(None))->dict:
    data=session_data(request)
    if not x_csrf_token or x_csrf_token!=data.get("csrf"): raise HTTPException(403,"CSRF inválido")
    return data


def db():
    connection=connect(settings.database_path)
    try: yield connection
    finally: connection.close()


def device_session(authorization:str|None=Header(None),connection=Depends(db)):
    device=authenticate_device(connection,authorization)
    if not device: raise HTTPException(401,"Dispositivo no autorizado")
    return device


class Login(BaseModel): username:str=Field(max_length=100); password:str=Field(max_length=500)
class InitialSetup(BaseModel):
    username:str=Field(min_length=2,max_length=100)
    password:str=Field(min_length=12,max_length=500)
    locale:Literal["es","en"]="es"
    theme:Literal["light","dark"]="light"
    palette:Literal["mono","ice","lavender","rose","coral"]="ice"
class UpdateOnboarding(BaseModel):
    locale:Literal["es","en"]|None=None
    theme:Literal["light","dark"]|None=None
    palette:Literal["mono","ice","lavender","rose","coral"]|None=None
    step:Literal["welcome","extension","import","categories","category_confirmation","complete"]|None=None
class ChangePassword(BaseModel):
    current_password:str=Field(min_length=1,max_length=500)
    new_password:str=Field(min_length=1,max_length=500)
class UpdateBookmark(BaseModel):
    model_config=ConfigDict(extra="forbid")
    priority:int|None=Field(None,ge=0,le=5)
    notes:str|None=Field(None,max_length=10000); review_date:str|None=None
    category_ids:list[int]|None=None; tag_names:list[str]|None=None
class TaxonomyCandidateChoice(BaseModel):
    id:int
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default="",max_length=500)
    enabled:bool=True
class ApplyTaxonomyDiscovery(BaseModel):
    categories:list[TaxonomyCandidateChoice]=Field(min_length=1,max_length=40)
class CreateCustomView(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    category_ids:list[int]=Field(default_factory=list,max_length=30)
    include_all:bool=False
    is_default:bool=False
class UpdateCustomView(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=100)
    is_default:bool|None=None
class DuplicateCustomView(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=100)
class CreateCustomViewColumn(BaseModel):
    category_id:int|None=None
    title:str=Field(default="",max_length=100)
class UpdateCustomViewColumn(BaseModel):
    category_id:int|None=None
    title:str|None=Field(default=None,max_length=100)
    width:int|None=Field(default=None,ge=300,le=2400)
class ReorderCustomViewColumns(BaseModel):
    column_ids:list[int]=Field(max_length=30)
class PairDevice(BaseModel):
    code:str=Field(min_length=4,max_length=32)
    name:str=Field(default="Chrome",max_length=100)
    extension_version:str|None=Field(default=None,max_length=30)
class SyncPayload(BaseModel):
    scan_id:str=Field(min_length=1,max_length=200)
    archive:dict[str,Any]
    snapshot:dict[str,Any]|None=None


@app.get("/health")
def health():
    try:
        with connect(settings.database_path) as connection:
            connection.execute("SELECT 1").fetchone()
            count=connection.execute("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND bookmark_state NOT IN ('removed','locally_archived')").fetchone()[0]
        return {"status":"ok","bookmarks":count,"semantic_worker":"on_demand_not_resident",
          "embedding_model":model_cache_status(),"fts5":"available"}
    except Exception as exc: raise HTTPException(503,f"database unavailable: {type(exc).__name__}")


def set_session_cookie(response:Response,token:str)->None:
    response.set_cookie("xb_session",token,httponly=True,samesite="strict",secure=settings.cookie_secure,
      max_age=settings.session_hours*3600,path="/")


def onboarding_payload(connection)->dict:
    row=connection.execute("SELECT * FROM onboarding_state WHERE id=1").fetchone()
    profile=connection.execute("SELECT state FROM taxonomy_profiles WHERE id=1").fetchone()
    return {"locale":row["locale"],"theme":row["theme"],"palette":row["palette"],
      "step":row["step"],"completed":bool(row["completed_at"]),
      "bookmarks":connection.execute("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND bookmark_state NOT IN ('removed','locally_archived')").fetchone()[0],
      "devices":connection.execute("SELECT count(*) FROM sync_devices WHERE revoked_at IS NULL").fetchone()[0],
      "taxonomy_state":profile["state"] if profile else "empty",
      "enrichment":enrichment_status(connection)}


@app.get("/api/setup/status")
def setup_status(connection=Depends(db)):
    count=connection.execute("SELECT count(*) FROM app_users").fetchone()[0]
    row=connection.execute("SELECT locale,theme,palette FROM onboarding_state WHERE id=1").fetchone()
    return {"needs_setup":count==0,"preferences":dict(row) if row else {"locale":"es","theme":"light","palette":"ice"}}


@app.post("/api/setup")
def initial_setup(payload:InitialSetup,response:Response,connection=Depends(db)):
    username=payload.username.strip()
    if len(username)<2 or any(ord(character)<32 for character in username):
        raise HTTPException(422,"El nombre debe tener al menos 2 caracteres válidos")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM app_users LIMIT 1").fetchone():
            connection.rollback();raise HTTPException(409,"La cuenta inicial ya está creada")
        connection.execute("INSERT INTO app_users(username,password_hash,session_version) VALUES(?,?,1)",
          (username,hash_password(payload.password)))
        connection.execute("""UPDATE onboarding_state SET locale=?,theme=?,palette=?,step='welcome',
          updated_at=CURRENT_TIMESTAMP WHERE id=1""",(payload.locale,payload.theme,payload.palette))
        connection.commit()
    except HTTPException:raise
    except Exception:
        connection.rollback();raise
    token,csrf=create_session(username,settings.session_secret,settings.session_hours,1)
    set_session_cookie(response,token)
    return {"username":username,"csrf":csrf,"onboarding":onboarding_payload(connection)}


@app.get("/api/onboarding")
def onboarding(connection=Depends(db),_=Depends(session_data)):
    return onboarding_payload(connection)


@app.patch("/api/onboarding")
def update_onboarding(payload:UpdateOnboarding,connection=Depends(db),_=Depends(csrf_session)):
    values=payload.model_dump(exclude_none=True)
    if values.get("step")=="complete":
        profile=connection.execute("SELECT state FROM taxonomy_profiles WHERE id=1").fetchone()
        if not profile or profile["state"]!="active":
            raise HTTPException(409,"Confirma las categorías antes de terminar el onboarding")
    if values:
        assignments=",".join(f"{name}=?" for name in values)
        completed=" ,completed_at=CURRENT_TIMESTAMP" if values.get("step")=="complete" else ""
        connection.execute(f"UPDATE onboarding_state SET {assignments}{completed},updated_at=CURRENT_TIMESTAMP WHERE id=1",
          tuple(values.values()))
        connection.commit()
    return onboarding_payload(connection)


@app.post("/api/login")
def login(payload:Login,response:Response,connection=Depends(db)):
    user=connection.execute("SELECT password_hash,session_version FROM app_users WHERE username=?",(payload.username,)).fetchone()
    if not user or not verify_password(payload.password,user["password_hash"]):
        raise HTTPException(401,"Credenciales incorrectas")
    token,csrf=create_session(payload.username,settings.session_secret,settings.session_hours,user["session_version"])
    set_session_cookie(response,token)
    return {"username":payload.username,"csrf":csrf}


@app.post("/api/account/password")
def change_password(payload:ChangePassword,response:Response,connection=Depends(db),session=Depends(csrf_session)):
    user=connection.execute("SELECT password_hash,session_version FROM app_users WHERE username=?",(session["sub"],)).fetchone()
    if not user or not verify_password(payload.current_password,user["password_hash"]):
        raise HTTPException(400,"La contraseña actual no es correcta")
    if len(payload.new_password)<12:
        raise HTTPException(422,"La nueva contraseña debe tener al menos 12 caracteres")
    if verify_password(payload.new_password,user["password_hash"]):
        raise HTTPException(422,"La nueva contraseña debe ser diferente de la actual")
    changed=connection.execute("""UPDATE app_users SET password_hash=?,session_version=session_version+1,
      updated_at=CURRENT_TIMESTAMP WHERE username=? AND password_hash=?""",
      (hash_password(payload.new_password),session["sub"],user["password_hash"])).rowcount
    if not changed: raise HTTPException(409,"La contraseña cambió durante la operación; inténtalo de nuevo")
    connection.commit()
    version=connection.execute("SELECT session_version FROM app_users WHERE username=?",(session["sub"],)).fetchone()[0]
    token,csrf=create_session(session["sub"],settings.session_secret,settings.session_hours,version)
    set_session_cookie(response,token)
    return {"changed":True,"csrf":csrf}


@app.post("/api/logout")
def logout(response:Response,_=Depends(csrf_session)):
    response.delete_cookie("xb_session",path="/"); return {"ok":True}


@app.get("/api/session")
def current_session(data=Depends(session_data)):
    return {"username":data["sub"],"csrf":data["csrf"]}


def csv_int(value:str|None)->list[int]:
    if not value:return []
    try:return [int(x) for x in value.split(",") if x]
    except ValueError:raise HTTPException(422,"filtro numérico inválido")
def csv_str(value:str|None)->list[str]: return [x for x in (value or "").split(",") if x]
def filters(categories=None,tags=None,authors=None,content_types=None,has_media=None,has_links=None,date_from=None,date_to=None):
    return {"categories":csv_int(categories),"tags":csv_int(tags),"authors":csv_str(authors),
      "content_types":csv_str(content_types),"has_media":has_media,"has_links":has_links,"date_from":date_from,"date_to":date_to}


def original_url(tweet_id:str,handle:str|None)->str:
    return f"https://x.com/{handle}/status/{tweet_id}" if handle and re.fullmatch(r"[A-Za-z0-9_]{1,15}",handle) else f"https://x.com/i/status/{tweet_id}"


def hydrate(connection,hit:dict)->dict:
    row=connection.execute("""SELECT t.*,a.priority,a.notes,a.review_date,
      bq.quote_status,bq.quoted_tweet_id,qt.full_text quote_full_text,qt.display_text quote_display_text,
      qt.author_handle quote_author_handle,qt.author_name quote_author_name
      FROM tweets t JOIN annotations a ON a.tweet_id=t.tweet_id
      LEFT JOIN bookmark_quotes bq ON bq.bookmark_id=t.tweet_id LEFT JOIN tweets qt ON qt.tweet_id=bq.quoted_tweet_id
      WHERE t.tweet_id=? AND t.is_bookmark=1 AND t.bookmark_state NOT IN ('removed','locally_archived')""",(hit["tweet_id"],)).fetchone()
    if not row:return hit
    categories=[dict(r) for r in connection.execute("""SELECT c.id,c.name,c.slug,e.origin,e.confidence,e.evidence_json
      FROM effective_category_assignments e JOIN categories c ON c.id=e.category_id WHERE e.tweet_id=? ORDER BY c.sort_order""",(row["tweet_id"],))]
    tags=[dict(r) for r in connection.execute("""SELECT t.id,t.name,e.origin,e.confidence FROM effective_tag_assignments e JOIN tags t ON t.id=e.tag_id WHERE e.tweet_id=? ORDER BY t.name""",(row["tweet_id"],))]
    types=[r[0] for r in connection.execute("SELECT content_type FROM content_type_assignments WHERE tweet_id=?",(row["tweet_id"],))]
    result=dict(hit); result.update({"tweet_id":row["tweet_id"],"status":row["source_status"],"text":row["display_text"],
      "author":{"handle":row["author_handle"],"name":row["author_name"],"avatar":row["author_avatar"]},
      "created_at":row["created_at_iso"] or row["created_at_raw"],"lang":row["lang"],"original_url":original_url(row["tweet_id"],row["author_handle"]),
      "bookmark_state":row["bookmark_state"],"missing_complete_scans":row["missing_complete_scans"],
      "urls":json.loads(row["urls_json"]),"hashtags":json.loads(row["hashtags_json"]),"media":json.loads(row["media_json"]),
      "card":{"type":row["card_type"],"url":row["card_url"],"title":row["card_title"],"description":row["card_description"]} if any((row["card_title"],row["card_description"],row["card_url"])) else None,
      "quote":{"status":row["quote_status"],"tweet_id":row["quoted_tweet_id"],"text":row["quote_display_text"],"author":{"handle":row["quote_author_handle"],"name":row["quote_author_name"]},"url":original_url(row["quoted_tweet_id"],row["quote_author_handle"]) if row["quoted_tweet_id"] else None} if row["quote_status"] else None,
      "annotation":{"priority":row["priority"],"notes":row["notes"],"review_date":row["review_date"]},
      "categories":categories,"tags":tags,"content_types":types})
    return result


def run_search(connection,kind,q,page,page_size,**kwargs):
    engine=SearchEngine(connection); selected=filters(**kwargs)
    response=engine.text(q,selected,page,page_size) if kind=="text" else engine.hybrid(q,selected,page,page_size)
    response["results"]=[hydrate(connection,hit) for hit in response["results"]]
    return response


@app.get("/api/search/text")
def text_search(q:str="",page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100),categories:str|None=None,tags:str|None=None,authors:str|None=None,content_types:str|None=None,has_media:bool|None=None,has_links:bool|None=None,date_from:str|None=None,date_to:str|None=None,connection=Depends(db),_=Depends(session_data)):
    return run_search(connection,"text",q,page,page_size,categories=categories,tags=tags,authors=authors,content_types=content_types,has_media=has_media,has_links=has_links,date_from=date_from,date_to=date_to)


@app.get("/api/search/hybrid")
def hybrid_search(q:str=Query(min_length=1,max_length=1000),page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100),categories:str|None=None,tags:str|None=None,authors:str|None=None,content_types:str|None=None,has_media:bool|None=None,has_links:bool|None=None,date_from:str|None=None,date_to:str|None=None,connection=Depends(db),_=Depends(session_data)):
    return run_search(connection,"hybrid",q,page,page_size,categories=categories,tags=tags,authors=authors,content_types=content_types,has_media=has_media,has_links=has_links,date_from=date_from,date_to=date_to)


@app.get("/api/bookmarks/{tweet_id}")
def detail(tweet_id:str,connection=Depends(db),_=Depends(session_data)):
    result=hydrate(connection,{"tweet_id":tweet_id,"score":0,"sources":[]})
    if "text" not in result:raise HTTPException(404,"Bookmark no encontrado")
    return result


def apply_update(connection,tweet_id:str,payload:UpdateBookmark,*,rebuild:bool=True):
    if not connection.execute("SELECT 1 FROM tweets WHERE tweet_id=? AND is_bookmark=1",(tweet_id,)).fetchone():raise HTTPException(404,"Bookmark no encontrado")
    fields=[];params=[]
    for name in ("priority","notes","review_date"):
        value=getattr(payload,name)
        if value is not None:fields.append(f"{name}=?");params.append(value)
    if fields:
        params.append(tweet_id); connection.execute(f"UPDATE annotations SET {','.join(fields)},updated_at=CURRENT_TIMESTAMP WHERE tweet_id=?",params)
    if payload.category_ids is not None:
        desired=set(payload.category_ids); valid={r[0] for r in connection.execute("SELECT id FROM categories")};
        if not desired<=valid:raise HTTPException(422,"categoría desconocida")
        effective={r[0] for r in connection.execute("SELECT category_id FROM effective_category_assignments WHERE tweet_id=?",(tweet_id,))}
        for cid in desired:
            connection.execute("DELETE FROM category_suppressions WHERE tweet_id=? AND category_id=?",(tweet_id,cid))
            connection.execute("INSERT OR IGNORE INTO category_assignments(tweet_id,category_id,origin,confidence,evidence_json) VALUES(?,?,'manual',1,'{\"method\":\"manual\"}')",(tweet_id,cid))
        for cid in effective-desired:
            connection.execute("DELETE FROM category_assignments WHERE tweet_id=? AND category_id=? AND origin='manual'",(tweet_id,cid))
            connection.execute("INSERT OR IGNORE INTO category_suppressions(tweet_id,category_id) VALUES(?,?)",(tweet_id,cid))
        refresh_prototypes_from_feedback(connection,desired|effective)
    if payload.tag_names is not None:
        desired={normalize_tag(x):x.strip()[:80] for x in payload.tag_names if x.strip()}
        effective={r["normalized"]:(r["id"],r["origin"]) for r in connection.execute("""SELECT t.id,t.normalized,e.origin FROM effective_tag_assignments e JOIN tags t ON t.id=e.tag_id WHERE e.tweet_id=?""",(tweet_id,))}
        for normalized,name in desired.items():
            connection.execute("INSERT INTO tags(name,normalized) VALUES(?,?) ON CONFLICT(normalized) DO NOTHING",(name,normalized));tid=connection.execute("SELECT id FROM tags WHERE normalized=?",(normalized,)).fetchone()[0]
            connection.execute("DELETE FROM tag_suppressions WHERE tweet_id=? AND tag_id=?",(tweet_id,tid));connection.execute("INSERT OR IGNORE INTO tag_assignments(tweet_id,tag_id,origin,confidence,evidence_json) VALUES(?,?,'manual',1,'{\"method\":\"manual\"}')",(tweet_id,tid))
        for normalized,(tid,origin) in effective.items():
            if normalized not in desired:
                connection.execute("DELETE FROM tag_assignments WHERE tweet_id=? AND tag_id=? AND origin='manual'",(tweet_id,tid));connection.execute("INSERT OR IGNORE INTO tag_suppressions(tweet_id,tag_id) VALUES(?,?)",(tweet_id,tid))
    connection.commit()
    if rebuild: rebuild_search_documents(connection,[tweet_id])


@app.patch("/api/bookmarks/{tweet_id}")
def update(tweet_id:str,payload:UpdateBookmark,connection=Depends(db),_=Depends(csrf_session)):
    apply_update(connection,tweet_id,payload);return hydrate(connection,{"tweet_id":tweet_id,"score":0,"sources":[]})


def custom_view_or_404(connection,view_id:int):
    row=connection.execute("SELECT * FROM custom_views WHERE id=?",(view_id,)).fetchone()
    if not row:raise HTTPException(404,"Vista no encontrada")
    return row


def custom_category_or_404(connection,category_id:int):
    row=connection.execute("SELECT id,name,slug,parent_id FROM categories WHERE id=?",(category_id,)).fetchone()
    if not row:raise HTTPException(422,"La categoría seleccionada no existe")
    return row


def serialize_custom_view(connection,view_id:int)->dict:
    view=custom_view_or_404(connection,view_id)
    columns=[dict(row) for row in connection.execute("""SELECT vc.id,vc.category_id,
      CASE WHEN vc.title='' THEN COALESCE(c.name,'Todo') ELSE vc.title END title,
      vc.title custom_title,COALESCE(c.name,'Todos los guardados') category_name,
      c.slug category_slug,c.parent_id,vc.position,vc.width,
      CASE WHEN vc.category_id IS NULL THEN
       (SELECT count(*) FROM tweets t WHERE t.is_bookmark=1
         AND t.bookmark_state NOT IN ('removed','locally_archived'))
      ELSE (SELECT count(DISTINCT e.tweet_id) FROM effective_category_assignments e
       JOIN tweets t ON t.tweet_id=e.tweet_id
       WHERE e.category_id=vc.category_id AND t.is_bookmark=1
         AND t.bookmark_state NOT IN ('removed','locally_archived')) END count
      FROM custom_view_columns vc LEFT JOIN categories c ON c.id=vc.category_id
      WHERE vc.view_id=? ORDER BY vc.position,vc.id""",(view_id,))]
    return {"id":view["id"],"name":view["name"],"is_default":bool(view["is_default"]),
      "sort_order":view["sort_order"],"updated_at":view["updated_at"],"columns":columns}


@app.get("/api/views")
def custom_views(connection=Depends(db),_=Depends(session_data)):
    ids=[row[0] for row in connection.execute(
      "SELECT id FROM custom_views ORDER BY is_default DESC,sort_order,id")]
    return {"views":[serialize_custom_view(connection,view_id) for view_id in ids]}


@app.post("/api/views")
def create_custom_view(payload:CreateCustomView,connection=Depends(db),_=Depends(csrf_session)):
    name=payload.name.strip()
    if not name:raise HTTPException(422,"El nombre de la vista no puede estar vacío")
    category_ids=list(dict.fromkeys(payload.category_ids))
    for category_id in category_ids:custom_category_or_404(connection,category_id)
    first=connection.execute("SELECT 1 FROM custom_views LIMIT 1").fetchone() is None
    make_default=first or payload.is_default
    if make_default:connection.execute("UPDATE custom_views SET is_default=0")
    order=connection.execute("SELECT COALESCE(max(sort_order),-1)+1 FROM custom_views").fetchone()[0]
    cursor=connection.execute("INSERT INTO custom_views(name,is_default,sort_order) VALUES(?,?,?)",
      (name,int(make_default),order));view_id=cursor.lastrowid
    initial_columns=([None] if payload.include_all else [])+category_ids
    for position,category_id in enumerate(initial_columns):
        connection.execute("INSERT INTO custom_view_columns(view_id,category_id,position) VALUES(?,?,?)",
          (view_id,category_id,position))
    connection.commit();return serialize_custom_view(connection,view_id)


@app.patch("/api/views/{view_id}")
def update_custom_view(view_id:int,payload:UpdateCustomView,connection=Depends(db),_=Depends(csrf_session)):
    custom_view_or_404(connection,view_id);fields=[];values=[]
    if payload.name is not None:
        name=payload.name.strip()
        if not name:raise HTTPException(422,"El nombre de la vista no puede estar vacío")
        fields.append("name=?");values.append(name)
    if payload.is_default is True:
        connection.execute("UPDATE custom_views SET is_default=0 WHERE id<>?",(view_id,))
        fields.append("is_default=1")
    elif payload.is_default is False:fields.append("is_default=0")
    if fields:
        values.append(view_id);connection.execute(
          f"UPDATE custom_views SET {','.join(fields)},updated_at=CURRENT_TIMESTAMP WHERE id=?",values)
        connection.commit()
    return serialize_custom_view(connection,view_id)


@app.post("/api/views/{view_id}/duplicate")
def duplicate_custom_view(view_id:int,payload:DuplicateCustomView,connection=Depends(db),_=Depends(csrf_session)):
    source=custom_view_or_404(connection,view_id)
    name=(payload.name or f"{source['name']} · copia").strip()
    if not name:raise HTTPException(422,"El nombre de la vista no puede estar vacío")
    if len(name)>100:raise HTTPException(422,"El nombre de la vista es demasiado largo")
    order=connection.execute("SELECT COALESCE(max(sort_order),-1)+1 FROM custom_views").fetchone()[0]
    cursor=connection.execute("INSERT INTO custom_views(name,is_default,sort_order) VALUES(?,0,?)",(name,order))
    new_id=cursor.lastrowid
    connection.execute("""INSERT INTO custom_view_columns(view_id,category_id,title,position,width)
      SELECT ?,category_id,title,position,width FROM custom_view_columns WHERE view_id=? ORDER BY position,id""",
      (new_id,view_id));connection.commit();return serialize_custom_view(connection,new_id)


@app.delete("/api/views/{view_id}")
def delete_custom_view(view_id:int,connection=Depends(db),_=Depends(csrf_session)):
    view=custom_view_or_404(connection,view_id);connection.execute("DELETE FROM custom_views WHERE id=?",(view_id,))
    if view["is_default"]:
        replacement=connection.execute("SELECT id FROM custom_views ORDER BY sort_order,id LIMIT 1").fetchone()
        if replacement:connection.execute("UPDATE custom_views SET is_default=1 WHERE id=?",(replacement[0],))
    connection.commit();return {"deleted":view_id}


@app.post("/api/views/{view_id}/columns")
def create_custom_view_column(view_id:int,payload:CreateCustomViewColumn,connection=Depends(db),_=Depends(csrf_session)):
    custom_view_or_404(connection,view_id)
    if payload.category_id is not None:custom_category_or_404(connection,payload.category_id)
    duplicate=connection.execute(
      "SELECT 1 FROM custom_view_columns WHERE view_id=? AND category_id IS NULL",(view_id,)
    ).fetchone() if payload.category_id is None else connection.execute(
      "SELECT 1 FROM custom_view_columns WHERE view_id=? AND category_id=?",
      (view_id,payload.category_id)).fetchone()
    if duplicate:raise HTTPException(409,"Esta fuente ya tiene una columna en la vista")
    position=connection.execute("SELECT COALESCE(max(position),-1)+1 FROM custom_view_columns WHERE view_id=?",
      (view_id,)).fetchone()[0]
    connection.execute("INSERT INTO custom_view_columns(view_id,category_id,title,position) VALUES(?,?,?,?)",
      (view_id,payload.category_id,payload.title.strip(),position))
    connection.execute("UPDATE custom_views SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(view_id,))
    connection.commit();return serialize_custom_view(connection,view_id)


@app.patch("/api/views/{view_id}/columns/{column_id}")
def update_custom_view_column(view_id:int,column_id:int,payload:UpdateCustomViewColumn,connection=Depends(db),_=Depends(csrf_session)):
    custom_view_or_404(connection,view_id)
    column=connection.execute("SELECT * FROM custom_view_columns WHERE id=? AND view_id=?",(column_id,view_id)).fetchone()
    if not column:raise HTTPException(404,"Columna no encontrada")
    fields=[];values=[]
    if "category_id" in payload.model_fields_set:
        if payload.category_id is not None:custom_category_or_404(connection,payload.category_id)
        duplicate=connection.execute(
          "SELECT 1 FROM custom_view_columns WHERE view_id=? AND category_id IS NULL AND id<>?",
          (view_id,column_id)).fetchone() if payload.category_id is None else connection.execute(
          "SELECT 1 FROM custom_view_columns WHERE view_id=? AND category_id=? AND id<>?",
          (view_id,payload.category_id,column_id)).fetchone()
        if duplicate:raise HTTPException(409,"Esta fuente ya tiene una columna en la vista")
        fields.append("category_id=?");values.append(payload.category_id)
    if payload.title is not None:fields.append("title=?");values.append(payload.title.strip())
    if payload.width is not None:fields.append("width=?");values.append(payload.width)
    if fields:
        values.extend((column_id,view_id));connection.execute(
          f"UPDATE custom_view_columns SET {','.join(fields)},updated_at=CURRENT_TIMESTAMP WHERE id=? AND view_id=?",values)
        connection.execute("UPDATE custom_views SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(view_id,));connection.commit()
    return serialize_custom_view(connection,view_id)


@app.delete("/api/views/{view_id}/columns/{column_id}")
def delete_custom_view_column(view_id:int,column_id:int,connection=Depends(db),_=Depends(csrf_session)):
    custom_view_or_404(connection,view_id)
    deleted=connection.execute("DELETE FROM custom_view_columns WHERE id=? AND view_id=?",(column_id,view_id)).rowcount
    if not deleted:raise HTTPException(404,"Columna no encontrada")
    rows=connection.execute("SELECT id FROM custom_view_columns WHERE view_id=? ORDER BY position,id",(view_id,)).fetchall()
    for position,row in enumerate(rows):connection.execute("UPDATE custom_view_columns SET position=? WHERE id=?",(position,row[0]))
    connection.execute("UPDATE custom_views SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(view_id,))
    connection.commit();return serialize_custom_view(connection,view_id)


@app.put("/api/views/{view_id}/columns/order")
def reorder_custom_view_columns(view_id:int,payload:ReorderCustomViewColumns,connection=Depends(db),_=Depends(csrf_session)):
    custom_view_or_404(connection,view_id)
    existing=[row[0] for row in connection.execute("SELECT id FROM custom_view_columns WHERE view_id=?",(view_id,))]
    if len(payload.column_ids)!=len(set(payload.column_ids)) or set(payload.column_ids)!=set(existing):
        raise HTTPException(422,"El orden debe incluir exactamente las columnas de la vista")
    for position,column_id in enumerate(payload.column_ids):
        connection.execute("UPDATE custom_view_columns SET position=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND view_id=?",
          (position,column_id,view_id))
    connection.execute("UPDATE custom_views SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(view_id,))
    connection.commit();return serialize_custom_view(connection,view_id)


@app.get("/api/taxonomy")
def taxonomy(connection=Depends(db),_=Depends(session_data)):
    categories=[dict(r) for r in connection.execute("""SELECT c.*,count(DISTINCT CASE WHEN tw.bookmark_state NOT IN ('removed','locally_archived') THEN e.tweet_id END) count FROM categories c LEFT JOIN effective_category_assignments e ON e.category_id=c.id LEFT JOIN tweets tw ON tw.tweet_id=e.tweet_id GROUP BY c.id ORDER BY c.sort_order""")]
    tags=[dict(r) for r in connection.execute("""SELECT t.id,t.name,t.normalized,count(DISTINCT CASE WHEN tw.bookmark_state NOT IN ('removed','locally_archived') THEN e.tweet_id END) count FROM tags t LEFT JOIN effective_tag_assignments e ON e.tag_id=t.id LEFT JOIN tweets tw ON tw.tweet_id=e.tweet_id GROUP BY t.id ORDER BY count DESC,t.name LIMIT 300""")]
    authors=[dict(r) for r in connection.execute("SELECT author_handle handle,author_name name,count(*) count FROM tweets WHERE is_bookmark=1 AND bookmark_state NOT IN ('removed','locally_archived') AND author_handle IS NOT NULL GROUP BY author_handle,author_name ORDER BY count DESC LIMIT 300")]
    return {"categories":categories,"tags":tags,"authors":authors,"content_types":["tool","article","thread","tutorial","reference","video","image","other"]}


@app.get("/api/taxonomy/discovery")
def taxonomy_discovery_status(connection=Depends(db),_=Depends(session_data)):
    return taxonomy_status(connection)


@app.post("/api/taxonomy/discovery")
def start_taxonomy_discovery(connection=Depends(db),_=Depends(csrf_session)):
    try:return discover_taxonomy(connection)
    except ValueError as exc:raise HTTPException(409,str(exc))


@app.post("/api/taxonomy/discovery/apply")
def confirm_taxonomy_discovery(payload:ApplyTaxonomyDiscovery,connection=Depends(db),_=Depends(csrf_session)):
    try:return apply_discovery(connection,[item.model_dump() for item in payload.categories])
    except ValueError as exc:raise HTTPException(409,str(exc))


@app.get("/api/facets")
def contextual_facets(q:str="",categories:str|None=None,tags:str|None=None,authors:str|None=None,
    content_types:str|None=None,has_media:bool|None=None,has_links:bool|None=None,
    date_from:str|None=None,date_to:str|None=None,connection=Depends(db),_=Depends(session_data)):
    """Return disjunctive facet counts using only FTS5, never semantic inference."""
    selected=filters(categories=categories,tags=tags,authors=authors,content_types=content_types,
      has_media=has_media,has_links=has_links,date_from=date_from,date_to=date_to)
    engine=SearchEngine(connection)
    def scope(without):
        current={key:([] if key==without else value) for key,value in selected.items()}
        candidates=filter_candidates(connection,current)
        return {hit.tweet_id for hit in engine._fts(q,candidates)} if q.strip() else set(candidates)
    def counts(rows,allowed):
        result={}
        for tweet_id,value in rows:
            if tweet_id in allowed and value is not None:result[str(value)]=result.get(str(value),0)+1
        return result
    category_rows=connection.execute("SELECT tweet_id,category_id FROM effective_category_assignments").fetchall()
    tag_rows=connection.execute("SELECT tweet_id,tag_id FROM effective_tag_assignments").fetchall()
    author_rows=connection.execute("SELECT tweet_id,author_handle FROM tweets WHERE is_bookmark=1 AND bookmark_state NOT IN ('removed','locally_archived')").fetchall()
    type_rows=connection.execute("SELECT tweet_id,content_type FROM content_type_assignments").fetchall()
    return {"categories":counts(category_rows,scope("categories")),"tags":counts(tag_rows,scope("tags")),
      "authors":counts(author_rows,scope("authors")),"content_types":counts(type_rows,scope("content_types"))}


@app.get("/api/stats")
def stats(connection=Depends(db),_=Depends(session_data)):
    one=lambda sql:connection.execute(sql).fetchone()[0]
    report=connection.execute("SELECT * FROM source_imports ORDER BY id DESC LIMIT 1").fetchone()
    return {"bookmarks":one("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND bookmark_state NOT IN ('removed','locally_archived')"),"suspected_removed":one("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND bookmark_state='suspected_removed'"),"removed":one("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND bookmark_state='removed'"),"unavailable":one("SELECT count(*) FROM tweets WHERE is_bookmark=1 AND source_status='unavailable'"),"quotes":one("SELECT count(*) FROM bookmark_quotes"),"quotes_with_text":one("SELECT count(*) FROM bookmark_quotes b JOIN tweets t ON t.tweet_id=b.quoted_tweet_id WHERE t.full_text<>''"),"embeddings":one("SELECT count(*) FROM embeddings"),"classified":one("SELECT count(DISTINCT tweet_id) FROM category_assignments"),"last_import":dict(report) if report else None}


@app.post("/api/v1/xarchive/pairing-codes")
def new_pairing_code(connection=Depends(db),_=Depends(csrf_session)):
    try:return create_pairing_code(connection)
    except ValueError as exc:raise HTTPException(503,str(exc))


@app.get("/api/v1/xarchive/devices")
def devices(connection=Depends(db),_=Depends(session_data)):
    device_rows=[dict(row) for row in connection.execute("""SELECT id,name,account_user_id,
      created_at,last_seen_at,revoked_at,extension_version FROM sync_devices ORDER BY created_at DESC""")]
    latest=connection.execute("""SELECT r.id,r.device_id,r.started_at,r.finished_at,r.status,r.receipt_json,d.name device_name
      FROM sync_runs r LEFT JOIN sync_devices d ON d.id=r.device_id ORDER BY r.started_at DESC LIMIT 1""").fetchone()
    latest_sync=None
    if latest:
        receipt=json.loads(latest["receipt_json"])
        latest_sync={"id":latest["id"],"device_id":latest["device_id"],"device_name":latest["device_name"],
          "started_at":latest["started_at"],"finished_at":latest["finished_at"],"status":latest["status"],
          "import":receipt.get("import") or {},"lifecycle":receipt.get("lifecycle") or {},
          "enrichment":receipt.get("enrichment")}
    instance=connection.execute("SELECT value FROM schema_meta WHERE key='instance_id'").fetchone()
    return {"instance_id":instance["value"] if instance else "","devices":device_rows,
      "latest_sync":latest_sync,"enrichment":enrichment_status(connection)}


@app.get("/api/enrichment")
def enrichment(connection=Depends(db),_=Depends(session_data)):
    return enrichment_status(connection)


@app.post("/api/enrichment/retry")
def retry_enrichment(background:BackgroundTasks,connection=Depends(db),_=Depends(csrf_session)):
    run=connection.execute("""SELECT id,status FROM sync_runs
      WHERE status IN ('interrupted','embedding_failed_fts_available',
        'taxonomy_discovery_failed_search_available','failed')
      ORDER BY started_at DESC LIMIT 1""").fetchone()
    if not run:raise HTTPException(409,"No hay un enriquecimiento fallido que reintentar")
    owner=f"user:retry:{run['id']}"
    try:acquire_enrichment_lock(connection,owner)
    except EnrichmentBusy as exc:raise HTTPException(409,str(exc))
    create_enrichment_job(connection,run["id"])
    background.add_task(run_incremental_embeddings,run["id"],owner)
    return enrichment_status(connection)


@app.delete("/api/v1/xarchive/devices/{device_id}")
def revoke_device(device_id:str,connection=Depends(db),_=Depends(csrf_session)):
    changed=connection.execute("UPDATE sync_devices SET revoked_at=CURRENT_TIMESTAMP WHERE id=? AND revoked_at IS NULL",(device_id,)).rowcount
    connection.commit()
    if not changed:raise HTTPException(404,"Dispositivo no encontrado o ya revocado")
    return {"revoked":True}


@app.delete("/api/v1/xarchive/devices/{device_id}/record")
def delete_revoked_device(device_id:str,connection=Depends(db),_=Depends(csrf_session)):
    device=connection.execute("SELECT revoked_at FROM sync_devices WHERE id=?",(device_id,)).fetchone()
    if not device:raise HTTPException(404,"Dispositivo no encontrado")
    if not device["revoked_at"]:raise HTTPException(409,"Revoca el dispositivo antes de eliminarlo")
    connection.execute("DELETE FROM sync_devices WHERE id=?",(device_id,))
    connection.commit()
    return {"deleted":True}


@app.post("/api/v1/xarchive/pair")
def pair(payload:PairDevice,connection=Depends(db)):
    try:return pair_device(connection,payload.code,payload.name,payload.extension_version)
    except ValueError as exc:raise HTTPException(401,str(exc))


@app.get("/api/v1/xarchive/bootstrap")
def bootstrap(connection=Depends(db),device=Depends(device_session)):
    path=bootstrap_archive(connection)
    if not path:raise HTTPException(404,"Todavía no hay un archivo para inicializar la extensión")
    return FileResponse(path,media_type="application/json",filename="xarchive-bootstrap.json")


@app.post("/api/v1/xarchive/sync")
def synchronize(payload:SyncPayload,background:BackgroundTasks,connection=Depends(db),device=Depends(device_session)):
    existing=connection.execute("SELECT id,status,receipt_json FROM sync_runs WHERE scan_id=?",(payload.scan_id,)).fetchone()
    if existing:
        receipt=json.loads(existing["receipt_json"]);receipt["idempotent_replay"]=True
        if existing["status"] in {"interrupted","embedding_failed_fts_available",
          "taxonomy_discovery_failed_search_available","failed"}:
            lock_owner=f"{device['id']}:{payload.scan_id}"
            try:acquire_enrichment_lock(connection,lock_owner)
            except EnrichmentBusy:return receipt
            create_enrichment_job(connection,existing["id"])
            background.add_task(run_incremental_embeddings,existing["id"],lock_owner)
            receipt["enrichment"]="resuming"
        return receipt
    lock_owner=f"{device['id']}:{payload.scan_id}"
    try:acquire_enrichment_lock(connection,lock_owner)
    except EnrichmentBusy as exc:raise HTTPException(409,str(exc))
    try:
        receipt=process_sync(connection,device,payload.model_dump())
        if not receipt.get("idempotent_replay") and receipt.get("sync_id"):
            create_enrichment_job(connection,receipt["sync_id"])
    except ValueError as exc:
        release_enrichment_lock(connection,lock_owner);raise HTTPException(422,str(exc))
    except Exception:
        release_enrichment_lock(connection,lock_owner);raise
    if not receipt.get("idempotent_replay") and receipt.get("sync_id"):
        background.add_task(run_incremental_embeddings,receipt["sync_id"],lock_owner)
    else:release_enrichment_lock(connection,lock_owner)
    return receipt


@app.get("/api/v1/xarchive/sync/{sync_id}")
def sync_status(sync_id:str,connection=Depends(db),device=Depends(device_session)):
    row=connection.execute("SELECT receipt_json FROM sync_runs WHERE id=? AND device_id=?",(sync_id,device["id"])).fetchone()
    if not row:raise HTTPException(404,"Sincronización no encontrada")
    return json.loads(row["receipt_json"])


@app.get("/api/v1/xarchive/extension")
def extension_info(_=Depends(session_data)):
    if not settings.extension_zip.is_file():raise HTTPException(503,"Paquete de extensión no disponible")
    digest=__import__("hashlib").sha256(settings.extension_zip.read_bytes()).hexdigest()
    try:
        with ZipFile(settings.extension_zip) as package:
            manifest=json.loads(package.read("manifest.json"))
        version=manifest.get("version_name") or manifest["version"]
    except (BadZipFile,KeyError,TypeError,ValueError,json.JSONDecodeError):
        raise HTTPException(503,"Paquete de extensión no disponible")
    return {"version":version,"sha256":digest,"download_url":"/api/v1/xarchive/extension/download"}


@app.get("/api/v1/xarchive/extension/download")
def extension_download(_=Depends(session_data)):
    if not settings.extension_zip.is_file():raise HTTPException(404,"Paquete no encontrado")
    return FileResponse(settings.extension_zip,media_type="application/zip",filename="xarchive-connector.zip")


app.mount("/static",StaticFiles(directory=STATIC),name="static")
@app.get("/")
def index():return FileResponse(STATIC/"index.html")
