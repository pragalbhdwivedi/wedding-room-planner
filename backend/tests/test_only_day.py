"""Synthetic regressions for an explicit 24 November only attendance limit."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.allocator import allocate
from app.billing import calculate
from app.db import SessionLocal
from app.models import Assignment, Audit, EventAttendance, GuestPresence, MealAttendance, PlanChange
from app.planning_rules import DAYS, NIGHTS, active, present_on_day, summaries, validate
from app.planning_store import save_assignments, snapshot
from test_guest_probability import apply_import, imported, workbook
from test_planning import apply, assign, family, headers, member, plan, preview, revision


def edit_tags(client,owner,guest,tags):
    data=plan(client);f=next(f for f in data['families'] if f['id']==guest['family_id'])
    body={k:f[k] for k in ['label','side','reserved_eligible','couple_children','required_room_type']}
    body['members']=[{k:g[k] for k in ['id','name','age','age_band','gender','sharing_mode','probability','category','phone','arrival','tags','notes']}
                     for g in data['guests'] if g['family_id']==f['id']]
    next(g for g in body['members'] if g['id']==guest['id'])['tags']=tags
    body['revision']=data['revision']
    return client.put('/api/planning/families/'+f['id'],json=body,headers=headers(owner))


def event(client,owner,day):
    response=client.post('/api/planning/events',json={'revision':revision(client),'name':'Synthetic Function '+day,'day':day},headers=headers(owner))
    assert response.status_code==201,response.text
    return response.json()['id']


def test_explicit_day_limit_is_independent_from_arrival_and_archive():
    ordinary={'arrival':NIGHTS[1],'tags':[]}
    assert all(present_on_day(ordinary,d) for d in DAYS)
    assert not active(ordinary,NIGHTS[0]) and active(ordinary,NIGHTS[1])
    limited={**ordinary,'arrival':NIGHTS[0],'tags':['only_24_nov'],'probability':50}
    assert [present_on_day(limited,d) for d in DAYS]==[True,False,False]
    assert [active(limited,n) for n in NIGHTS]==[True,False]
    assert not present_on_day({**limited,'probability':49},DAYS[0])
    assert not present_on_day(limited,'2026-11-23')
    assert present_on_day({**limited,'arrival':None},DAYS[0])
    assert not active({**limited,'arrival':None},NIGHTS[0])


def test_family_limit_releases_only_excluded_night_keeps_locks_identity_and_history(client,owner):
    guest=family(client,owner,[member(None,None,age_band='unknown',probability=75,tags=['synthetic_source'])])[0]
    for night in NIGHTS:
        assign(client,owner,[guest],'w-102',night)
        assert client.put('/api/planning/locks',json={'revision':revision(client),'resource_id':'w-102','night':night,'locked':True},headers=headers(owner)).status_code==200
    before=plan(client)
    with SessionLocal() as db:changes=db.scalar(select(func.count()).select_from(PlanChange))
    result=edit_tags(client,owner,guest,['synthetic_source','only_24_nov'])
    assert result.status_code==200 and 'token' not in result.json(),result.text
    after=plan(client);saved=next(g for g in after['guests'] if g['id']==guest['id'])
    assert saved['name'] is None and saved['age'] is None and saved['age_band']=='unknown' and saved['probability']==75
    assert len(after['guests'])==1 and after['locks']==before['locks']
    assert after['assignments']==[a for a in before['assignments'] if a['night']==NIGHTS[0]]
    assert after['summary'][NIGHTS[0]]['residents']==1 and after['summary'][NIGHTS[0]]['unconfirmed_ages']==1
    assert after['summary'][NIGHTS[1]]['residents']==after['summary'][NIGHTS[1]]['assigned']==0
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(PlanChange))==changes
        audit=db.scalar(select(Audit).where(Audit.action=='family.updated'))
        assert audit.details['day_scope_released_assignments']==[a for a in before['assignments'] if a['night']==NIGHTS[1]]
        assert not audit.details['probability_changes']
    assert edit_tags(client,owner,guest,['synthetic_source']).status_code==200
    assert plan(client)['assignments']==after['assignments']  # Removing the tag never restores a placement.


def test_limit_filters_existing_function_and_meal_history_without_creating_attendance(client,owner):
    guest=family(client,owner)[0];gid=uuid.UUID(guest['id']);events=[]
    for day in DAYS:
        eid=event(client,owner,day);events.append(eid)
        assert client.put('/api/planning/functions/attendance',json={'revision':revision(client),'rows':[{'event_id':eid,'guest_id':guest['id'],'planned':True,'actual':True}]},headers=headers(owner)).status_code==200
        assert client.put('/api/planning/meals',json={'revision':revision(client),'rows':[{'guest_id':guest['id'],'day':day,'meal':'dinner','planned':True,'actual':True,'inclusion':'chargeable'}]},headers=headers(owner)).status_code==200
    times={'arrived_at':'2026-11-24T14:00:00+05:30','departed_at':'2026-11-25T09:00:00+05:30'}
    assert client.put('/api/planning/presence/'+guest['id'],json={'revision':revision(client),**times},headers=headers(owner)).status_code==200
    before=plan(client)['presence']
    assert edit_tags(client,owner,guest,['only_24_nov']).status_code==200
    assert plan(client)['presence']==before and not plan(client)['assignments']
    assert [m['day'] for m in client.get('/api/planning/meals').json()['rows']]==[DAYS[0]]
    assert [r['event_id'] for r in client.get('/api/planning/functions').json()['rows']]==[events[0]]
    for day,eid in zip(DAYS[1:],events[1:]):
        assert client.put('/api/planning/meals',json={'revision':revision(client),'rows':[{'guest_id':guest['id'],'day':day,'meal':'lunch'}]},headers=headers(owner)).status_code==409
        assert client.put('/api/planning/functions/attendance',json={'revision':revision(client),'rows':[{'event_id':eid,'guest_id':guest['id']}]},headers=headers(owner)).status_code==409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EventAttendance).where(EventAttendance.guest_id==gid))==3
        assert db.scalar(select(func.count()).select_from(MealAttendance).where(MealAttendance.guest_id==gid))==3
        assert db.get(GuestPresence,gid).departed_at is not None
    assert edit_tags(client,owner,guest,[]).status_code==200
    assert len(client.get('/api/planning/meals').json()['rows'])==3
    assert len(client.get('/api/planning/functions').json()['rows'])==3


def test_manual_destinations_beds_and_history_cannot_override_explicit_day_limit(client,owner):
    guest=family(client,owner,[member(age=8,age_band='child')])[0]
    assign(client,owner,[guest],'w-102',NIGHTS[1])
    assert apply(client,owner,preview(client,owner,[guest],None,NIGHTS[1])).status_code==200
    assert edit_tags(client,owner,guest,['only_24_nov']).status_code==200
    # No placement was released by the edit, so this exercises the history guard itself.
    undo=client.post('/api/planning/history',json={'revision':revision(client),'direction':'undo'},headers=headers(owner))
    assert undo.status_code==409 and 'excluded' in undo.text
    move={'revision':revision(client),'moves':[{'guest_id':guest['id'],'night':NIGHTS[1],'resource_id':'w-102'}]}
    assert client.post('/api/planning/assignments/preview',json=move,headers=headers(owner)).status_code==409
    choices=client.post('/api/planning/assignments/destinations',json={'revision':revision(client),'guest_ids':[guest['id']],'night':NIGHTS[1]},headers=headers(owner)).json()['choices']
    assert all(not c['allowed'] for c in choices.values())
    assert client.put('/api/planning/assignments/'+guest['id']+'/bed',json={'revision':revision(client),'night':NIGHTS[1],'separate_bed':True},headers=headers(owner)).status_code==409
    assign(client,owner,[guest],'w-102',NIGHTS[0])
    assert client.put('/api/planning/assignments/'+guest['id']+'/bed',json={'revision':revision(client),'night':NIGHTS[0],'separate_bed':True},headers=headers(owner)).status_code==200
    assert plan(client)['summary'][NIGHTS[0]]['hotel_guests']==1


def test_excel_existing_tag_column_roundtrips_and_releases_only_other_night(client,owner):
    guest=family(client,owner,[member(probability=75,tags=['synthetic_source'])])[0]
    for night in NIGHTS:assign(client,owner,[guest],'w-102',night)
    def limit(sheet):
        column=[c.value for c in sheet[1]].index('Tags')+1
        sheet.cell(2,column,'synthetic_source, only_24_nov')
    pending=imported(client,owner,workbook(client,limit))
    assert not pending['errors'] and len(pending['day_scope_released_assignments'])==1,pending
    assert pending['day_scope_released_assignments'][0]['night']==NIGHTS[1]
    assert apply_import(client,owner,pending).status_code==200
    data=plan(client)
    assert data['guests'][0]['probability']==75 and data['guests'][0]['id']==guest['id']
    assert [a['night'] for a in data['assignments']]==[NIGHTS[0]]
    again=imported(client,owner,client.get('/api/planning/export.xlsx').content)
    assert not again['errors'] and not again['day_scope_released_assignments']
    assert apply_import(client,owner,again).status_code==200
    assert 'only_24_nov' in plan(client)['guests'][0]['tags']
    with SessionLocal() as db:
        audits=list(db.scalars(select(Audit).where(Audit.action=='import.applied')))
        assert sum(len(a.details['day_scope_released_assignments']) for a in audits)==1


def test_stale_out_of_day_rows_do_not_count_bill_or_anchor_allocator(client,owner):
    guest=family(client,owner,[member(tags=['only_24_nov'])])[0]
    with SessionLocal() as db:data=snapshot(db)
    stale=[{'guest_id':guest['id'],'night':n,'resource_id':'w-102'} for n in NIGHTS]
    data['assignments']=stale
    data['locks']=[{'resource_id':'w-102','night':NIGHTS[1]}]
    assert summaries(data,stale)[NIGHTS[1]]['assigned']==0
    assert any(e['code']=='unavailable_day' for e in validate(data,stale)['errors'])
    result=allocate(data)
    assert result['assignments'] is not None,result
    assert [a['night'] for a in result['assignments']]==[NIGHTS[0]]
    assert not result['unassigned']
    policy={'wyndham_allowance':0,'wyndham_excess_paise':500000,'staff_meal_paise':15000,'second_hotel_day_paise':1800000,'second_hotel_included':12}
    meals=[{'guest_id':guest['id'],'day':day,'meal':'dinner','location':'wyndham','planned':True,'actual':True,'inclusion':'chargeable'} for day in DAYS]
    for basis in ['planned','actual']:
        bill=calculate(data,policy,{'guest_meals':{'dinner_adult':10000},'second_extra_paise':None},meals,[],basis=basis)
        assert bill['nights'][NIGHTS[1]]['wyndham_people']==bill['nights'][NIGHTS[1]]['chargeable']==0
        assert bill['known_subtotal_paise']==510000
        assert len([l for l in bill['lines'] if l['kind']=='guest_meal'])==1
        assert all(l['day']==DAYS[0] for l in bill['lines'] if l['kind']=='guest_meal')
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as rejected:save_assignments(db,stale)
        assert rejected.value.status_code==409
        # A legacy/directly stored row is excluded from the current API/export snapshot too.
        from datetime import date
        db.add_all([Assignment(guest_id=uuid.UUID(a['guest_id']),night=date.fromisoformat(a['night']),resource_id=a['resource_id']) for a in stale])
        db.commit()
        assert [a['night'] for a in snapshot(db)['assignments']]==[NIGHTS[0]]
    assert [a['night'] for a in plan(client)['assignments']]==[NIGHTS[0]]


@pytest.mark.parametrize('tags',[[],['only_24_nov']])
def test_solver_keeps_normal_manual_prearrival_lock_in_validation_baseline(client,owner,tags):
    guest=family(client,owner,[member(arrival=NIGHTS[1],tags=tags)])[0]
    with SessionLocal() as db:data=snapshot(db)
    data['assignments']=[{'guest_id':guest['id'],'night':NIGHTS[0],'resource_id':'w-102'}]
    data['locks']=[{'resource_id':'w-102','night':NIGHTS[0]}]
    result=allocate(data)
    assert result['assignments'] is None and result['solver_status']=='unresolved',result
    assert any(e['code']=='locked' for e in result['errors'])


@pytest.mark.parametrize('kind',['nearby','same_building','must_share','cannot_share'])
def test_relationships_do_not_constrain_guests_without_a_shared_night(client,owner,kind):
    if kind=='cannot_share':
        people=family(client,owner,[member('Synthetic First',tags=['only_24_nov']),member('Synthetic Second',arrival=NIGHTS[1])])
        first=next(g for g in people if g['name']=='Synthetic First');second=next(g for g in people if g['name']=='Synthetic Second')
    else:
        first=family(client,owner,[member(tags=['only_24_nov','main_hotel'])],label='Synthetic First Day')[0]
        second=family(client,owner,[member(arrival=NIGHTS[1],tags=['second_hotel','second_hotel_only'])],label='Synthetic Second Day')[0]
    with SessionLocal() as db:data=snapshot(db)
    data['links']=[{'id':'synthetic-link','a':first['id'],'b':second['id'],'kind':kind,'severity':'hard'}]
    result=allocate(data)
    assert result['assignments'] is not None and not result['unassigned'],result
    assert {(a['guest_id'],a['night']) for a in result['assignments']}=={(first['id'],NIGHTS[0]),(second['id'],NIGHTS[1])}
