#!/usr/bin/env python3
"""Repository-local bounded ABE work-loop foundation.

This supervisor does not execute arbitrary queue commands. It evaluates a bounded
number of successive READY tasks, records heartbeat evidence, and stops fail-closed
on any unsafe or externally consequential task. A repository-local lock prevents
concurrent duplicate supervisors.
"""
import json, os, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/'config/abe/task-queue.json'
PLAN=ROOT/'config/abe/build-plan.json'
OUT=ROOT/'build/abe/work-loop-state.json'
LOCK=ROOT/'build/abe/work-loop.lock'
MAX_STEPS=5

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(obj):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(LOCK,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        os.write(fd,str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        write({'schema_version':1,'status':'BLOCKED','reason':'repository-local work-loop lock already exists','production_deploy':False,'destructive_actions':False,'external_writes':False})
        raise SystemExit(2)
    try:
        q,p=load(QUEUE),load(PLAN)
        safe=(q.get('mode')=='controlled-autonomous' and p.get('mode')=='controlled-autonomous' and q.get('authoritative_department_scope')==['DO-DEP-01','DO-DEP-14'] and q.get('verified_baseline')=='DO-DEP-04' and p.get('production_deploy') is False and p.get('destructive_actions') is False and all(q.get('rules',{}).get(k) is False for k in ('external_writes','production_deploy','destructive_actions')))
        ready=[t for t in q.get('queue',[]) if t.get('status')=='READY'][:MAX_STEPS]
        blocked=next((t for t in ready if t.get('safe_autonomous') is not True),None)
        state={'schema_version':1,'status':'RUNNING' if safe and ready and not blocked else ('IDLE' if safe and not ready else 'BLOCKED'),'heartbeat_epoch':int(time.time()),'bounded_max_steps':MAX_STEPS,'ready_tasks':[{'id':t['id'],'title':t['title']} for t in ready],'next_task':({'id':ready[0]['id'],'title':ready[0]['title']} if safe and ready and not blocked else None),'reason':(f"unsafe READY task {blocked['id']}" if blocked else (None if safe else 'global safety invariants failed')),'authoritative_department_scope':['DO-DEP-01','DO-DEP-14'],'verified_baseline':'DO-DEP-04','production_deploy':False,'destructive_actions':False,'external_writes':False}
        write(state); print(json.dumps(state,sort_keys=True))
        if state['status']=='BLOCKED': raise SystemExit(2)
    finally:
        LOCK.unlink(missing_ok=True)
if __name__=='__main__': main()
