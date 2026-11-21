"""Synthetic probability/archive regressions for the isolated PostgreSQL testdb."""
import io
import os
import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select, text

from app.allocator import allocate
from app.billing import calculate
from app.db import SessionLocal
from app.main import app
from app.models import Audit, EventAttendance, Guest, GuestDocument, GuestPresence, MealAttendance, PlanChange
from app.planning_rules import NIGHTS, summaries, validate
from app.planning_store import snapshot
from test_guest_documents import upload
from test_planning import PASSWORD, apply, assign, family, headers, member, plan, preview, revision


def probability(client, auth, guest, value, rev=None):
    return client.put('/api/planning/guests/'+guest['id']+'/probability',
                      json={'revision':revision(client) if rev is None else rev,'probability':value},headers=headers(auth))


def imported(client, auth, content):
    response=client.post('/api/planning/import/preview?revision='+str(revision(client)),
                         files={'file':('synthetic.xlsx',content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},headers=headers(auth))
    assert response.status_code==200,response.text
    return response.json()


def apply_import(client, auth, pending):
    return client.post('/api/planning/import/apply',json={'revision':pending['revision'],'token':pending['token'],
                       'acknowledged':[w['id'] for w in pending['warnings']]},headers=headers(auth))


def workbook(client, transform):
    book=load_workbook(io.BytesIO(client.get('/api/planning/export.xlsx').content))
    transform(book['Guests'])
    out=io.BytesIO();book.save(out);return out.getvalue()


@pytest.mark.parametrize('invalid',[-1,101,49.5,'49',True,None])
def test_probability_rejects_invalid_values_without_mutation(client,owner,invalid):
    guest=family(client,owner)[0];before=plan(client)
    assert guest['probability']==100
    assert probability(client,owner,guest,invalid).status_code==422
    result=client.post('/api/planning/families',json={'revision':before['revision'],'label':'Synthetic Invalid',
        'side':'bride','members':[member(probability=invalid)]},headers=headers(owner))
    assert result.status_code==422 and plan(client)==before


def test_archive_boundary_releases_all_nights_retains_ids_attendance_and_history(client,owner):
    guests=family(client,owner,[member('Synthetic Archived'),member('Synthetic Boundary',probability=50)])
    guest=next(g for g in guests if g['name']=='Synthetic Archived')
    for night in NIGHTS:assign(client,owner,guests,'w-102',night)
    assert client.put('/api/planning/locks',json={'revision':revision(client),'resource_id':'w-102',
        'night':NIGHTS[0],'locked':True},headers=headers(owner)).status_code==200
    assert upload(client,owner,guest).status_code==200
    event=client.post('/api/planning/events',json={'revision':revision(client),'name':'Synthetic Function',
        'day':NIGHTS[0]},headers=headers(owner)).json()['id']
    event_row={'event_id':event,'guest_id':guest['id'],'planned':True,'actual':True}
    meal={'guest_id':guest['id'],'day':NIGHTS[0],'meal':'dinner','planned':True,'actual':True,'inclusion':'included'}
    assert client.put('/api/planning/functions/attendance',json={'revision':revision(client),'rows':[event_row]},headers=headers(owner)).status_code==200
    assert client.put('/api/planning/meals',json={'revision':revision(client),'rows':[meal]},headers=headers(owner)).status_code==200
    assert client.put('/api/planning/presence/'+guest['id'],json={'revision':revision(client),'arrived_at':'2026-11-24T14:00:00+05:30'},headers=headers(owner)).status_code==200
    before=plan(client)
    with SessionLocal() as db:history_count=db.scalar(select(func.count()).select_from(PlanChange))
    result=probability(client,owner,guest,49)
    assert result.status_code==200 and result.json()['archived'] is True
    after=plan(client)
    assert len(after['guests'])==2 and {g['id'] for g in after['guests']}=={g['id'] for g in guests}
    assert all(a['guest_id']!=guest['id'] for a in after['assignments']) and len(after['assignments'])==2
    assert after['locks']==before['locks'] and not after['presence']
    for night in NIGHTS:
        assert after['summary'][night]['residents']==1
        assert after['summary'][night]['hotel_guests']==1  # 50% counts as one whole active guest.
    assert client.get('/api/planning/meals').json()['rows']==[]
    assert client.get('/api/planning/functions').json()['rows']==[]
    assert client.get('/api/planning/guests/'+guest['id']+'/documents.pdf').status_code==200
    with SessionLocal() as db:
        gid=uuid.UUID(guest['id'])
        assert db.get(Guest,gid).probability==49
        for model in [GuestDocument,GuestPresence,MealAttendance,EventAttendance]:
            assert db.scalar(select(func.count()).select_from(model).where(model.guest_id==gid))==1
        assert db.scalar(select(func.count()).select_from(PlanChange))==history_count
        audit=db.scalar(select(Audit).where(Audit.action=='guest.probability_updated'))
        assert audit.details['before']==100 and audit.details['after']==49 and len(audit.details['released_assignments'])==2
    assert client.put('/api/planning/meals',json={'revision':revision(client),'rows':[meal]},headers=headers(owner)).status_code==409
    assert client.put('/api/planning/functions/attendance',json={'revision':revision(client),'rows':[event_row]},headers=headers(owner)).status_code==409
    assert client.put('/api/planning/presence/'+guest['id'],json={'revision':revision(client)},headers=headers(owner)).status_code==409
    assert client.put('/api/planning/assignments/'+guest['id']+'/bed',json={'revision':revision(client),'night':NIGHTS[0],'separate_bed':True},headers=headers(owner)).status_code==409
    denied=client.post('/api/planning/assignments/preview',json={'revision':revision(client),'moves':[{'guest_id':guest['id'],'night':NIGHTS[0],'resource_id':'w-104'}]},headers=headers(owner))
    assert denied.status_code==409 and 'archived' in denied.text.lower()
    choices=client.post('/api/planning/assignments/destinations',json={'revision':revision(client),'guest_ids':[guest['id']],'night':NIGHTS[0]},headers=headers(owner)).json()['choices']
    assert all(not c['allowed'] and 'archived' in c['reason'].lower() for c in choices.values())
    assert probability(client,owner,guest,50).status_code==200
    restored=plan(client)
    assert all(a['guest_id']!=guest['id'] for a in restored['assignments'])
    assert restored['summary'][NIGHTS[0]]['residents']==2 and restored['summary'][NIGHTS[0]]['unassigned']==1
    assert len(client.get('/api/planning/meals').json()['rows'])==1


def test_family_edit_legacy_omission_preserves_probability_and_explicit_archive_releases_rooms(client,owner):
    guests=family(client,owner,[member('Synthetic Low',probability=20),member('Synthetic High',probability=75)])
    high=next(g for g in guests if g['name']=='Synthetic High')
    assign(client,owner,[high],'w-102')
    d=plan(client);f=d['families'][0]
    members=[{k:g[k] for k in ['id','name','age','age_band','gender','sharing_mode','category','phone','arrival','tags','notes']} for g in d['guests']]
    body={k:f[k] for k in ['label','side','reserved_eligible','couple_children','required_room_type']}
    body.update(revision=d['revision'],members=members)
    response=client.put('/api/planning/families/'+f['id'],json=body,headers=headers(owner))
    assert response.status_code==200,response.text
    assert {g['name']:g['probability'] for g in plan(client)['guests']}=={'Synthetic Low':20,'Synthetic High':75}
    for g in members:g['probability']=49
    body['revision']=revision(client)
    response=client.put('/api/planning/families/'+f['id'],json=body,headers=headers(owner))
    assert response.status_code==200 and 'token' not in response.json(),response.text
    assert not plan(client)['assignments'] and all(g['probability']==49 for g in plan(client)['guests'])


def test_restored_family_member_stays_unassigned_during_another_members_repair(client,owner):
    guests=family(client,owner,[member('Synthetic Restore',probability=20),member('Synthetic Repair',probability=100)])
    restored=next(g for g in guests if g['name']=='Synthetic Restore')
    repair=next(g for g in guests if g['name']=='Synthetic Repair')
    assign(client,owner,[repair],'w-202')
    d=plan(client);f=d['families'][0]
    members=[{k:g[k] for k in ['id','name','age','age_band','gender','sharing_mode','probability','category','phone','arrival','tags','notes']} for g in d['guests']]
    for g in members:
        if g['id']==restored['id']:g['probability']=100
        else:g['age']=60
    body={k:f[k] for k in ['label','side','reserved_eligible','couple_children','required_room_type']}
    body.update(revision=d['revision'],members=members)
    response=client.put('/api/planning/families/'+f['id'],json=body,headers=headers(owner))
    assert response.status_code==200,response.text
    pending=response.json();assert pending['token'] and pending['family_edit']
    assert all(c['guest_id']!=restored['id'] for c in pending['changes'])
    saved=client.post('/api/planning/families/apply',json={'revision':pending['revision'],'token':pending['token'],
        'acknowledged':[w['id'] for w in pending['warnings']]},headers=headers(owner))
    assert saved.status_code==200,saved.text
    assert all(a['guest_id']!=restored['id'] for a in plan(client)['assignments'])


def test_probability_excel_roundtrip_legacy_default_and_archive_apply(client,owner):
    guests=family(client,owner,[member('Synthetic Low',probability=20),member('Synthetic High',probability=75)])
    high=next(g for g in guests if g['name']=='Synthetic High')
    assign(client,owner,[high],'w-102')
    def omit(sheet):
        column=[c.value for c in sheet[1]].index('Probability')+1
        sheet.delete_cols(column)
    pending=imported(client,owner,workbook(client,omit));assert not pending['errors'],pending
    assert apply_import(client,owner,pending).status_code==200
    assert {g['name']:g['probability'] for g in plan(client)['guests']}=={'Synthetic Low':20,'Synthetic High':75}
    assert len(plan(client)['assignments'])==1
    def archive_all(sheet):
        column=[c.value for c in sheet[1]].index('Probability')+1
        for row in range(2,sheet.max_row+1):sheet.cell(row,column,49)
    pending=imported(client,owner,workbook(client,archive_all));assert not pending['errors'],pending
    assert apply_import(client,owner,pending).status_code==200
    assert not plan(client)['assignments'] and all(g['probability']==49 for g in plan(client)['guests'])
    exported=client.get('/api/planning/export.xlsx').content
    pending=imported(client,owner,exported);assert not pending['errors'],pending
    assert apply_import(client,owner,pending).status_code==200
    assert all(g['probability']==49 for g in plan(client)['guests'])
    def fractional(sheet):sheet.cell(2,[c.value for c in sheet[1]].index('Probability')+1,49.5)
    assert imported(client,owner,workbook(client,fractional))['errors']


def test_archiving_invalidates_room_import_and_allocator_previews_and_history(client,owner):
    guest=family(client,owner)[0]
    assign(client,owner,[guest],'w-102')
    move=preview(client,owner,[guest],'w-104')
    imp=imported(client,owner,client.get('/api/planning/export.xlsx').content)
    run=client.post('/api/planning/allocation',json={'revision':revision(client)},headers=headers(owner)).json()['id']
    from app.jobs import process_one
    process_one()
    assert probability(client,owner,guest,0).status_code==200
    assert apply(client,owner,move).status_code==409
    assert apply_import(client,owner,imp).status_code==409
    assert client.post('/api/planning/allocation/'+run+'/preview',json={'revision':revision(client)},headers=headers(owner)).status_code==409
    for direction in ['undo','redo']:
        assert client.post('/api/planning/history',json={'revision':revision(client),'direction':direction},headers=headers(owner)).status_code==409
    assert not plan(client)['assignments']
    assert probability(client,owner,guest,100).status_code==200 and not plan(client)['assignments']


def test_history_cannot_reassign_guest_archived_after_being_unassigned(client,owner):
    guest=family(client,owner)[0];assign(client,owner,[guest],'w-102')
    move=preview(client,owner,[guest],None)
    assert apply(client,owner,move).status_code==200 and not plan(client)['assignments']
    assert probability(client,owner,guest,0).status_code==200
    result=client.post('/api/planning/history',json={'revision':revision(client),'direction':'undo'},headers=headers(owner))
    assert result.status_code==409 and 'archived' in result.text.lower()
    assert not plan(client)['assignments']


@pytest.mark.parametrize('role,side',[('family','bride'),('family','groom'),('reception',None),('editor',None)])
def test_probability_role_and_private_document_boundaries(client,owner,role,side):
    guest=family(client,owner,[member(probability=20)])[0]
    assert upload(client,owner,guest).status_code==200
    assert client.post('/api/users',json={'username':'synthetic.archive.viewer','display_name':'Synthetic Viewer','password':PASSWORD,'role':role,'side':side},headers=headers(owner)).status_code==201
    viewer=TestClient(app);auth=viewer.post('/api/auth/login',json={'username':'synthetic.archive.viewer','password':PASSWORD}).json()
    response=viewer.get('/api/planning')
    assert ('Synthetic Guest' in response.text)==(role!='family' or side=='bride')
    if role=='family':assert viewer.get('/api/planning/guests/'+guest['id']+'/documents').status_code==403
    else:assert viewer.get('/api/planning/guests/'+guest['id']+'/documents').status_code==200
    if role in {'family','reception'}:assert viewer.get('/api/planning/billing').status_code==403
    result=probability(viewer,auth,guest,100,rev=revision(client))
    assert result.status_code==(200 if role=='editor' else 403)


def test_additive_probability_migration_backfills_100_without_other_changes(client,owner):
    guests=family(client,owner)
    for night in NIGHTS:assign(client,owner,guests,'w-102',night)
    assert upload(client,owner,guests[0]).status_code==200
    before=plan(client)
    with SessionLocal() as db:
        original={table:list(db.scalars(text('SELECT to_jsonb(t)::text FROM '+table+' t ORDER BY 1'))) for table in ['guests','families','assignments','plan_state','users','sessions','guest_documents']}
    env={**os.environ,'PLANNER_DATABASE_USER':'planner_migrate','PLANNER_DATABASE_PASSWORD_FILE':'/run/secrets/db_migration_password'}
    for target in [('downgrade','0009_guest_documents'),('upgrade','head')]:
        result=subprocess.run(['alembic',*target],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stderr
    assert plan(client)==before and all(g['probability']==100 for g in plan(client)['guests'])
    with SessionLocal() as db:
        assert original=={table:list(db.scalars(text('SELECT to_jsonb(t)::text FROM '+table+' t ORDER BY 1'))) for table in original}


def test_archived_stale_rows_excluded_by_pure_rules_allocator_and_billing(client,owner):
    guests=family(client,owner,[member('Synthetic Active',probability=50),member('Synthetic Archived',probability=49)])
    with SessionLocal() as db:data=snapshot(db)
    active_id=next(g['id'] for g in guests if g['name']=='Synthetic Active')
    archived_id=next(g['id'] for g in guests if g['name']=='Synthetic Archived')
    # Defend calculations even if passed a stale/imported snapshot with an old archived assignment.
    rows=[{'guest_id':g['id'],'night':NIGHTS[0],'resource_id':'w-102'} for g in guests]
    assert summaries(data,rows)[NIGHTS[0]]['assigned']==1
    assert any(e['code']=='archived_guest' for e in validate(data,rows)['errors'])
    data['assignments']=rows
    result=allocate(data)
    assert result['assignments'] is not None
    assert all(a['guest_id']==active_id for a in result['assignments'])
    assert all(a['guest_id']!=archived_id for a in result['unassigned'])
    policy={'wyndham_allowance':0,'wyndham_excess_paise':500000,'staff_meal_paise':15000,'second_hotel_day_paise':1800000,'second_hotel_included':12}
    bill=calculate(data,policy,{'guest_meals':{},'second_extra_paise':None},[],[])
    assert bill['nights'][NIGHTS[0]]['wyndham_people']==1 and bill['nights'][NIGHTS[0]]['excess_paise']==500000
