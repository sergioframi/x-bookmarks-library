from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from app.config import settings
from app.db import connect,initialize_schema


def main():
    parser=argparse.ArgumentParser(description="Administración de la biblioteca")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("migrate")
    imp=sub.add_parser("import");imp.add_argument("path")
    classify=sub.add_parser("classify");classify.add_argument("--only-unclassified",action="store_true");classify.add_argument("--no-semantic",action="store_true")
    embed=sub.add_parser("embed");embed.add_argument("--all",action="store_true");embed.add_argument("--batch-size",type=int,default=32)
    sub.add_parser("rebuild-fts")
    sub.add_parser("discover-taxonomy")
    sub.add_parser("finalize-taxonomy")
    sub.add_parser("prepare-model")
    bootstrap=sub.add_parser("bootstrap");bootstrap.add_argument("path")
    backup=sub.add_parser("backup");backup.add_argument("destination")
    sub.add_parser("stats")
    password=sub.add_parser("hash-password");password.add_argument("password")
    args=parser.parse_args()
    if args.command=="hash-password":
        from app.security import hash_password
        print(hash_password(args.password));return
    if args.command=="prepare-model":
        from app.model_cache import prepare_embedding_model
        print(json.dumps(prepare_embedding_model(),ensure_ascii=False,indent=2));return
    settings.database_path.parent.mkdir(parents=True,exist_ok=True)
    connection=connect(settings.database_path);initialize_schema(connection)
    try:
        if args.command=="migrate": result={"schema":"ok"}
        elif args.command=="import":
            from app.importer import import_xarchive
            result=import_xarchive(connection,args.path)
        elif args.command=="classify":
            from app.classifier import classify
            result=classify(connection,only_unclassified=args.only_unclassified,semantic=not args.no_semantic)
        elif args.command=="embed":
            from app.embedder import generate_embeddings
            job_id=__import__("os").getenv("ENRICHMENT_JOB_ID")
            progress=None
            if job_id:
                from app.progress import add_event,update_job
                milestone={"bucket":-1}
                def progress(completed,total):
                    percent=int(completed*100/max(1,total));bucket=percent//10
                    update_job(connection,job_id,status="running",phase="embeddings",total=total,
                      completed=completed,message=f"Creando embeddings: {completed} de {total}")
                    if bucket>milestone["bucket"]:
                        milestone["bucket"]=bucket
                        add_event(connection,job_id,"embedding","info","embeddings",
                          f"Embeddings: {completed} de {total}",{"completed":completed,"total":total,"percent":percent})
                        connection.commit()
            result=generate_embeddings(connection,only_missing=not args.all,batch_size=args.batch_size,
              progress_callback=progress)
        elif args.command=="rebuild-fts":
            from app.classifier import rebuild_search_documents
            result={"indexed":rebuild_search_documents(connection)}
        elif args.command=="discover-taxonomy":
            from app.taxonomy_discovery import discover_taxonomy
            result=discover_taxonomy(connection)
        elif args.command=="finalize-taxonomy":
            from app.classifier import classify
            from app.taxonomy_discovery import discover_taxonomy,taxonomy_status
            profile=connection.execute("SELECT state FROM taxonomy_profiles WHERE id=1").fetchone()
            if profile and profile["state"]=="empty":result=discover_taxonomy(connection)
            elif profile and profile["state"]=="active":result=classify(connection,only_unclassified=True,semantic=True)
            else:result=taxonomy_status(connection)
        elif args.command=="bootstrap":
            from app.importer import import_xarchive
            from app.classifier import rebuild_search_documents
            from app.embedder import generate_embeddings
            from app.taxonomy_discovery import discover_taxonomy
            result={"import":import_xarchive(connection,args.path)}
            result["search_documents"]={"indexed":rebuild_search_documents(connection)}
            result["embeddings"]=generate_embeddings(connection)
            result["taxonomy_discovery"]=discover_taxonomy(connection)
        elif args.command=="backup":
            destination=Path(args.destination);destination.parent.mkdir(parents=True,exist_ok=True)
            target=sqlite3.connect(destination);connection.backup(target);target.close();result={"backup":str(destination)}
        else:
            one=lambda sql:connection.execute(sql).fetchone()[0]
            result={"bookmarks":one("SELECT count(*) FROM tweets WHERE is_bookmark=1"),"quotes":one("SELECT count(*) FROM bookmark_quotes"),"embeddings":one("SELECT count(*) FROM embeddings"),"classified":one("SELECT count(DISTINCT tweet_id) FROM category_assignments")}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally: connection.close()


if __name__=="__main__":main()
