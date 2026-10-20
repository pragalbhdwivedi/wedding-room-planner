import asyncio
import copy
import json
import uuid
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, select

from .billing import calculate
from .family_edits import changed_rows, project_edit, repair_placements
from .db import SessionLocal, database
from .models import (AllocationRun, Assignment, Audit, BillSnapshot, BillingSettings, EventAttendance, EventPolicy, Family, FunctionEvent, Guest, GuestLink, GuestPresence,
                     HotelChargeDay, LoginSession, MealAttendance, PendingChange, PlanChange, PlanState,
                     PlanningRule, Resource, Room, RoomConnection, RoomLock, User, WeddingDetails, now)
from .planning_rules import DAYS, NIGHTS, issue, validate
from .planning_store import assignments, hard_check, locked_state, save_assignments, snapshot, visible_plan
from .security import COOKIE, current_user, digest, require_csrf, require_editor

router=APIRouter(prefix="/api/planning")
DB=Annotated[object,Depends(database)]
Editor=Annotated[User,Depends(require_editor)]
Viewer=Annotated[User,Depends(current_user)]
WRITE=[Depends(require_csrf)]


class Input(BaseModel):
    model_config=ConfigDict(extra="forbid")


class Revision(Input):
    revision:int=Field(ge=1)


class ApplyInput(Revision):
    token:uuid.UUID
    acknowledged:list[str]=Field(default_factory=list,max_length=2000)


class GuestInput(Input):
    id:uuid.UUID|None=None
    name:str|None=Field(default=None,max_length=100)
    age:int|None=Field(default=None,ge=0,le=120)
    age_band:Literal["adult","child","unknown"]="unknown"
    gender:Literal["unspecified","male","female"]="unspecified"
    sharing_mode:Literal["family","friends"]="family"
    category:Literal["guest","driver","staff","vendor"]="guest"
    phone:str|None=Field(default=None,max_length=40)
    arrival:Literal["2026-11-24","2026-11-25"]|None="2026-11-24"
    tags:list[str]=Field(default_factory=list,max_length=30)
    notes:str=Field(default="",max_length=2000)

    @model_validator(mode="after")
    def consistent_age_band(self):
        if self.age is not None and self.age_band not in ["unknown", "child" if self.age<=10 else "adult"]:raise ValueError("Age and adult/child count disagree")
        return self

    @field_validator("name","phone")
    @classmethod
    def clean_optional(cls,value):return value.strip() or None if value is not None else None

    @field_validator("tags")
    @classmethod
    def valid_tags(cls,values):
        cleaned=sorted(set(v.strip().lower() for v in values if v.strip()))
        if any(len(v)>40 or not all(c.isalnum() or c in "_- " for c in v) for v in cleaned):raise ValueError("Use short text tags")
        return cleaned


class FamilyInput(Revision):
    label:str=Field(min_length=1,max_length=100)
    side:Literal["bride","groom"]
    reserved_eligible:bool=False
    couple_children:bool=False
    required_room_type:Literal["superior","premium"]|None=None
    members:list[GuestInput]=Field(min_length=1,max_length=80)

    @field_validator("label")
    @classmethod
    def label_text(cls,value):
        if not value.strip():raise ValueError("Enter a family/group name")
        return value.strip()

    @model_validator(mode="after")
    def compatible_room_type(self):
        if self.couple_children and self.required_room_type=="premium":
            raise ValueError("Couples with children must use Superior rooms at Wyndham")
        if self.required_room_type and any(m.category!="guest" for m in self.members):
            raise ValueError("Superior/Premium room types apply to hotel guests, not staff or drivers")
        return self


def record(db,user,state,action,details=None):
    state.revision+=1
    db.add(Audit(actor_id=user.id,action=action,entity_id=str(state.revision),details=details or {}))
    db.commit()
    return {"revision":state.revision}


def verify_edit(db,before):
    after=snapshot(db)
    result=hard_check(after,after["assignments"])
    old={i["id"] for i in validate(before,before["assignments"])["warnings"]}
    new=[w for w in result["warnings"] if w["id"] not in old]
    if new:raise HTTPException(409,{"message":"This edit introduces placement warnings. Unassign affected guests, then review their new placement.","errors":new})


@router.get("")
def get_plan(user:Viewer,db:DB):return visible_plan(db,user)


@router.post("/families",dependencies=WRITE,status_code=201)
def create_family(body:FamilyInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    if len(snapshot(db)["guests"])+len(body.members)>1000:raise HTTPException(400,"The current event supports up to 1,000 guest slots.")
    family=Family(label=body.label,side=body.side,reserved_eligible=body.reserved_eligible,couple_children=body.couple_children,required_room_type=body.required_room_type)
    db.add(family);db.flush()
    _members(db,family,body.members,creating=True)
    return {**record(db,user,state,"family.created",{"family_id":str(family.id),"slots":len(body.members)}),"family_id":str(family.id)}


def _members(db,family,members,creating=False):
    existing={str(g.id):g for g in db.scalars(select(Guest).where(Guest.family_id==family.id))}
    supplied=[str(m.id) for m in members if m.id]
    if len(supplied)!=len(set(supplied)) or not set(existing).issubset(supplied):raise HTTPException(400,"Keep each existing guest slot exactly once. Names complete slots; they do not create duplicate people.")
    for member in members:
        if member.id:
            guest=existing.get(str(member.id))
            if not guest:raise HTTPException(400,"An existing guest ID belongs to a different group or no longer exists.")
        else:
            guest=Guest(family_id=family.id);db.add(guest)
        for key,value in member.model_dump(exclude={"id","arrival"}).items():setattr(guest,key,value)
        guest.arrival=date.fromisoformat(member.arrival) if member.arrival else None
    db.flush()


@router.put("/families/{family_id}",dependencies=WRITE)
def update_family(family_id:uuid.UUID,body:FamilyInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);before=snapshot(db)
    if not db.get(Family,family_id):raise HTTPException(404,"Family/group not found")
    draft=body.model_dump(mode='json');existing={g['id']:g for g in before['guests']}
    if 'required_room_type' not in body.model_fields_set:
        draft['required_room_type']=next(f['required_room_type'] for f in before['families'] if f['id']==str(family_id))
    for source,member in zip(body.members,draft['members']):
        old=existing.get(str(source.id))
        if old:
            for key in ['gender','sharing_mode']:
                if key not in source.model_fields_set:member[key]=old[key]
    try:data,payload=project_edit(before,str(family_id),draft)
    except ValueError as error:raise HTTPException(400,str(error))
    removed=set(payload['removed_guest_ids'])
    base=[a for a in before['assignments'] if a['guest_id'] not in removed]
    checked=validate(data,base,before=before['assignments'])
    old={w['id'] for w in validate(before,before['assignments'])['warnings']}
    added={g['id'] for g in payload['guests']}-{g['id'] for g in before['guests']}
    placed_family=bool(added and all(g['age_band']!='unknown' for g in payload['guests'] if g['id'] in added) and any(a['guest_id'] in {g['id'] for g in before['guests'] if g['family_id']==str(family_id)} for a in before['assignments']))
    if not removed and not placed_family and not checked['errors'] and not [w for w in checked['warnings'] if w['id'] not in old]:
        persist_family_edit(db,payload)
        return record(db,user,state,'family.updated',{'family_id':str(family_id),'slots':len(body.members)})
    after,reason=(repair_placements(before,data,str(family_id)) if checked['errors'] or placed_family else (base,'Review the guest changes and any placement warnings before saving.'))
    if after is None and not checked['errors']:
        after,reason=base,'No safe room placement is available for the added guest. Review saving them unassigned.'
    if not checked['errors'] and after is not None and len(after)<len(base):
        after,reason=base,'The new member cannot be placed with the existing family safely. Review saving them unassigned.'
    if placed_family and not checked['errors'] and after!=base and after is not None:
        reason='Review the proposed room placement for the added member before saving.'
    if after is None:raise HTTPException(409,{'message':reason,'errors':checked['errors']})
    if checked['errors']:reason=' '.join(dict.fromkeys(e['message'] for e in checked['errors']))+' '+reason
    result=validate(data,after,before=before['assignments'])
    warnings=[w for w in result['warnings'] if w['id'] not in old]
    pending=PendingChange(owner_id=user.id,revision=body.revision,kind='family_edit',payload={**payload,'after':after},warnings=warnings,expires_at=now()+timedelta(minutes=5))
    db.add(pending);db.commit()
    from .planning_rules import summaries
    return {'family_edit':True,'token':str(pending.id),'revision':body.revision,'errors':[],'warnings':warnings,'summary':summaries(data,after),'changes':changed_rows(before['assignments'],after),'reason':reason,'removed_guest_ids':payload['removed_guest_ids'],'edited_guests':[{'id':g['id'],'name':g['name'],'age':g['age'],'group_label':g['group_label'],'age_band':g['age_band'],'tags':g['tags']} for g in payload['guests']]}


def persist_family_edit(db,payload):
    f=payload['family'];family=db.get(Family,uuid.UUID(f['id']))
    for key in ['label','side','reserved_eligible','couple_children','required_room_type']:setattr(family,key,f[key])
    for guest_id in payload.get('removed_guest_ids',[]):
        gid=uuid.UUID(guest_id)
        db.execute(delete(Assignment).where(Assignment.guest_id==gid))
        db.execute(delete(GuestLink).where((GuestLink.a==gid)|(GuestLink.b==gid)))
        db.execute(delete(GuestPresence).where(GuestPresence.guest_id==gid))
        db.execute(delete(MealAttendance).where(MealAttendance.guest_id==gid))
        db.execute(delete(EventAttendance).where(EventAttendance.guest_id==gid))
        db.delete(db.get(Guest,gid))
    for g in payload['guests']:
        row=db.get(Guest,uuid.UUID(g['id']))
        if not row:row=Guest(id=uuid.UUID(g['id']),family_id=family.id);db.add(row)
        for key in ['name','age','age_band','gender','sharing_mode','category','phone','tags','notes']:setattr(row,key,g[key])
        row.arrival=date.fromisoformat(g['arrival']) if g['arrival'] else None
    db.flush()


@router.post('/families/apply',dependencies=WRITE)
def apply_family_edit(body:ApplyInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);pending=db.get(PendingChange,body.token)
    if not pending or pending.kind!='family_edit' or pending.owner_id!=user.id or pending.revision!=state.revision or pending.expires_at<=now():raise HTTPException(409,'This guest-edit preview changed or expired. Review the edit again.')
    before=snapshot(db);old={w['id'] for w in validate(before,before['assignments'])['warnings']}
    persist_family_edit(db,pending.payload);data=snapshot(db);after=pending.payload['after']
    result=hard_check(data,after,before['assignments'])
    expected={w['id'] for w in result['warnings'] if w['id'] not in old}
    if expected!={w['id'] for w in pending.warnings} or set(body.acknowledged)!=expected:raise HTTPException(409,'Acknowledge exactly the warnings in this guest-edit preview.')
    if after!=before['assignments']:
        if pending.payload.get('removed_guest_ids'):
            # A deleted identity cannot safely reappear through assignment undo/redo.
            state.cursor=None;state.redo=[]
        else:
            change=PlanChange(parent=state.cursor,actor_id=user.id,before=before['assignments'],after=after);db.add(change);db.flush();state.cursor=change.id;state.redo=[]
        save_assignments(db,after)
    elif pending.payload.get('removed_guest_ids'):
        state.cursor=None;state.redo=[]
    fid=pending.payload['family']['id'];db.delete(pending)
    return record(db,user,state,'family.updated_with_placement',{'family_id':fid,'warning_ids':sorted(expected),'placement_changes':len(changed_rows(before['assignments'],after)),'deleted_guest_ids':pending.payload.get('removed_guest_ids',[])})



class Reservations(Revision):room_ids:list[str]=Field(max_length=4)


@router.put("/reservations",dependencies=WRITE)
def reservations(body:Reservations,user:Editor,db:DB):
    state=locked_state(db,body.revision);before=snapshot(db)
    eligible={r["id"] for r in before["resources"] if r["hotel_id"]=="wyndham" and r["category"]=="premium"}
    if len(body.room_ids) not in [0,4] or len(set(body.room_ids))!=len(body.room_ids) or not set(body.room_ids).issubset(eligible):raise HTTPException(400,"Choose four distinct Premium rooms, or keep the unnamed four-room reserve pool.")
    for resource in db.scalars(select(Resource)):resource.reserved=resource.id in body.room_ids
    db.flush();verify_edit(db,before)
    return record(db,user,state,"reservations.updated",{"room_ids":sorted(body.room_ids)})


class LockInput(Revision):
    resource_id:str
    night:Literal["2026-11-24","2026-11-25"]
    locked:bool


@router.put("/locks",dependencies=WRITE)
def lock(body:LockInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    if not db.get(Resource,body.resource_id):raise HTTPException(404,"Room/bed not found")
    key=(body.resource_id,date.fromisoformat(body.night));row=db.get(RoomLock,key)
    if body.locked and not row:db.add(RoomLock(resource_id=key[0],night=key[1]))
    if not body.locked and row:db.delete(row)
    return record(db,user,state,"lock.updated",{"resource_id":body.resource_id,"night":body.night,"locked":body.locked})


class Position(Input):
    resource_id:str
    x:float=Field(ge=0,le=20000,allow_inf_nan=False)
    y:float=Field(ge=0,le=20000,allow_inf_nan=False)


class LayoutInput(Revision):positions:list[Position]=Field(max_length=62)


@router.put("/layout",dependencies=WRITE)
def layout(body:LayoutInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    for position in body.positions:
        resource=db.get(Resource,position.resource_id)
        if not resource:raise HTTPException(404,"Room/bed not found")
        resource.x,resource.y=position.x,position.y
    return record(db,user,state,"layout.updated",{"resource_ids":[p.resource_id for p in body.positions]})


class RoomInput(Revision):
    number:str|None=Field(default=None,max_length=16)
    near_restaurant:bool=False


@router.put("/rooms/{resource_id}",dependencies=WRITE)
def room_settings(resource_id:str,body:RoomInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);before=snapshot(db)
    resource=db.get(Resource,resource_id)
    if not resource:raise HTTPException(404,"Room/bed not found")
    resource.near_restaurant=body.near_restaurant
    if resource.room_id and "number" in body.model_fields_set:
        room=db.get(Room,resource.room_id)
        if room.hotel_id=="wyndham":raise HTTPException(409,"Wyndham room numbers are fixed by the hotel layout. Move guests to another numbered room instead.")
        if room.hotel_id=="second":
            number=body.number.strip() if body.number else None
            if number and db.scalar(select(Room.id).where(Room.hotel_id=="second",Room.number==number,Room.id!=room.id)):raise HTTPException(409,"That second-hotel room number is already used.")
            room.number=number
    db.flush();verify_edit(db,before)
    return record(db,user,state,"room.settings_updated",{"resource_id":resource_id})


class RoomNumberInput(Revision):
    number:str|None=Field(default=None,max_length=16)


@router.put("/rooms/{resource_id}/number",dependencies=WRITE)
def room_number(resource_id:str,body:RoomNumberInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    resource=db.get(Resource,resource_id)
    room=db.get(Room,resource.room_id) if resource and resource.room_id else None
    if not room:raise HTTPException(400,"Only hotel rooms have room numbers.")
    if room.hotel_id=="wyndham":raise HTTPException(409,"Wyndham room numbers are fixed by the hotel layout. Move guests to another numbered room instead.")
    number=body.number.strip() if body.number else None
    if room.number==number:raise HTTPException(400,"This room already has that number.")
    if number and db.scalar(select(Room.id).where(Room.hotel_id==room.hotel_id,Room.number==number,Room.id!=room.id)):
        raise HTTPException(409,"That room number is already used at this hotel.")
    previous=room.number
    room.number=number
    return record(db,user,state,"room.number_updated",{"resource_id":resource_id,"from":previous,"to":number})


class RoomCategoryInput(Revision):
    category:Literal["superior","premium"]


@router.put("/rooms/{resource_id}/category",dependencies=WRITE)
def room_category(resource_id:str,body:RoomCategoryInput,user:Editor,db:DB):
    locked_state(db,body.revision)
    resource=db.get(Resource,resource_id)
    room=db.get(Room,resource.room_id) if resource and resource.room_id else None
    if not room or room.hotel_id!="wyndham":raise HTTPException(400,"Only Wyndham rooms have a fixed Superior/Premium type.")
    raise HTTPException(409,"This room's Superior/Premium type is fixed by the hotel layout. Move guests to a numbered room of the requested type instead.")


class LinkInput(Revision):
    a:uuid.UUID
    b:uuid.UUID
    kind:Literal["may_share","must_share","cannot_share","nearby","same_building"]
    severity:Literal["hard","warning"]="hard"


@router.post("/links",dependencies=WRITE)
def add_link(body:LinkInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);before=snapshot(db)
    a,b=sorted([body.a,body.b],key=str)
    if a==b or not db.get(Guest,a) or not db.get(Guest,b):raise HTTPException(400,"Choose two different existing guests.")
    link=db.scalar(select(GuestLink).where(GuestLink.a==a,GuestLink.b==b,GuestLink.kind==body.kind))
    if not link:link=GuestLink(a=a,b=b,kind=body.kind);db.add(link)
    link.severity="hard" if body.kind=="may_share" else body.severity
    db.flush();verify_edit(db,before)
    return record(db,user,state,"relationship.saved",{"link_id":str(link.id)})


@router.delete("/links/{link_id}",dependencies=WRITE)
def delete_link(link_id:uuid.UUID,revision:int,user:Editor,db:DB):
    state=locked_state(db,revision);before=snapshot(db);link=db.get(GuestLink,link_id)
    if not link:raise HTTPException(404,"Relationship not found")
    db.delete(link);db.flush();verify_edit(db,before)
    return record(db,user,state,"relationship.removed",{"link_id":str(link_id)})


class ConnectionInput(Revision):
    a:str
    b:str
    kind:Literal["neighbour","opposite"]
    confirmed:Literal[True]


@router.post("/connections",dependencies=WRITE)
def connection(body:ConnectionInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);a,b=sorted([body.a,body.b])
    if a==b or not db.get(Resource,a) or not db.get(Resource,b):raise HTTPException(400,"Choose two different rooms/beds.")
    row=db.get(RoomConnection,(a,b))
    if not row:row=RoomConnection(a=a,b=b,kind=body.kind);db.add(row)
    row.kind=body.kind
    return record(db,user,state,"connection.confirmed",{"a":a,"b":b,"kind":body.kind})


@router.delete("/connections",dependencies=WRITE)
def delete_connection(a:str,b:str,revision:int,user:Editor,db:DB):
    state=locked_state(db,revision);before=snapshot(db);row=db.get(RoomConnection,tuple(sorted([a,b])))
    if row:db.delete(row)
    db.flush();verify_edit(db,before)
    return record(db,user,state,"connection.removed",{"a":a,"b":b})


class RuleInput(Revision):
    name:str=Field(min_length=1,max_length=100)
    kind:Literal["allowed_resources","side_quota","separate_sides"]
    severity:Literal["hard","warning"]="hard"
    side:Literal["bride","groom"]|None=None
    tag:str|None=Field(default=None,max_length=40)
    resource_ids:list[str]=Field(default_factory=list,max_length=62)
    maximum:int|None=Field(default=None,ge=0,le=50)
    scope:Literal["room","block","floor"]="room"


@router.post("/rules",dependencies=WRITE)
def add_rule(body:RuleInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);before=snapshot(db)
    if body.kind=="allowed_resources":
        if not body.resource_ids or not set(body.resource_ids).issubset({r["id"] for r in before["resources"]}):raise HTTPException(400,"Select known allowed rooms/beds.")
        parameters={"resource_ids":sorted(set(body.resource_ids))}
    elif body.kind=="side_quota":
        if not body.side or body.maximum is None:raise HTTPException(400,"Choose a side and room maximum.")
        parameters={"maximum":body.maximum}
    else:
        if body.side:raise HTTPException(400,"Side separation applies to both sides.")
        parameters={"scope":body.scope}
    row=PlanningRule(name=body.name.strip(),kind=body.kind,severity=body.severity,side=body.side,tag=body.tag.strip().lower() if body.tag else None,parameters=parameters)
    if not row.name:raise HTTPException(400,"Enter a rule name")
    db.add(row);db.flush();verify_edit(db,before)
    return record(db,user,state,"rule.created",{"rule_id":str(row.id)})


@router.delete("/rules/{rule_id}",dependencies=WRITE)
def delete_rule(rule_id:uuid.UUID,revision:int,user:Editor,db:DB):
    state=locked_state(db,revision);before=snapshot(db);row=db.get(PlanningRule,rule_id)
    if not row:raise HTTPException(404,"Rule not found")
    db.delete(row);db.flush();verify_edit(db,before)
    return record(db,user,state,"rule.removed",{"rule_id":str(rule_id)})


class Move(Input):
    guest_id:uuid.UUID
    night:Literal["2026-11-24","2026-11-25"]
    resource_id:str|None


class SeparateBedInput(Revision):
    night:Literal["2026-11-24","2026-11-25"]
    separate_bed:bool


@router.put("/assignments/{guest_id}/bed",dependencies=WRITE)
def separate_bed(guest_id:uuid.UUID,body:SeparateBedInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    guest=db.get(Guest,guest_id)
    row=db.get(Assignment,(guest_id,date.fromisoformat(body.night)))
    if not guest or not row:raise HTTPException(404,"Assign this child to a hotel room on this night first.")
    resource=db.get(Resource,row.resource_id)
    if guest.category!="guest" or (guest.age is not None and guest.age>10) or (guest.age is None and guest.age_band!="child") or not resource.room_id:
        raise HTTPException(400,"Separate-bed counting is available only for a hotel guest aged 10 or under.")
    if row.separate_bed==body.separate_bed:raise HTTPException(400,"This bed choice is already saved.")
    row.separate_bed=body.separate_bed
    state.cursor=None;state.redo=[]
    return record(db,user,state,"assignment.separate_bed_updated",{"guest_id":str(guest_id),"night":body.night,"separate_bed":body.separate_bed})


class Moves(Revision):
    moves:list[Move]=Field(min_length=1,max_length=2000)
    confirm_sharing:bool=False


class Destinations(Revision):
    guest_ids:list[uuid.UUID]=Field(min_length=1,max_length=1000)
    night:Literal["2026-11-24","2026-11-25"]


@router.post("/assignments/destinations",dependencies=WRITE)
def destinations(body:Destinations,user:Editor,db:DB):
    locked_state(db,body.revision);data=snapshot(db);ids={str(g) for g in body.guest_ids}
    if not ids.issubset({g['id'] for g in data['guests']}):raise HTTPException(404,"Guest no longer exists")
    base=[a for a in data['assignments'] if not (a['guest_id'] in ids and a['night']==body.night)]
    choices={}
    for room in data['resources']:
        rows=base+[{'guest_id':g,'night':body.night,'resource_id':room['id']} for g in ids]
        result=validate(data,rows,before=data['assignments'])
        choices[room['id']]={'allowed':not result['errors'],'warnings':len(result['warnings']),'reason':result['errors'][0]['message'] if result['errors'] else ''}
    return {'revision':body.revision,'choices':choices}


def sharing_warning(a,b):
    return issue("sharing_confirmation", "Confirm these two people may share a room. Their compatibility link remains saved if you later undo this room move.", severity="warning", guests=[a,b])


def with_sharing(data,pairs):
    amended={**data,"links":[*data["links"],*({"a":a,"b":b,"kind":"may_share","severity":"hard"} for a,b in pairs)]}
    return amended


def sharing_candidates(data,after,moved_ids):
    errors=validate(data,after,before=data["assignments"])["errors"]
    pairs=sorted({tuple(sorted(e["guest_ids"])) for e in errors if e["code"]=="compatibility" and len(e["guest_ids"])==2 and set(e["guest_ids"]) & moved_ids})
    if not pairs:return []
    # Explicit consent cannot bypass a hard exclusion, Friends rule, capacity or any other mandatory rule.
    return pairs if not validate(with_sharing(data,pairs),after,before=data["assignments"])["errors"] else []


def preview_plan(db,user,revision,after,kind="assignment",sharing_pairs=()):
    locked_state(db,revision);before=snapshot(db);result=validate(with_sharing(before,sharing_pairs),after,before=before["assignments"])
    if result["errors"]:return {"errors":result["errors"],"warnings":result["warnings"],"token":None,"revision":revision}
    old={w['id'] for w in validate(before,before['assignments'])['warnings']}
    warnings=[w for w in result['warnings'] if w['id'] not in old]+[sharing_warning(a,b) for a,b in sharing_pairs]
    pending=PendingChange(owner_id=user.id,revision=revision,kind=kind,payload={"after":after,"sharing_pairs":list(sharing_pairs)},warnings=warnings,expires_at=now()+timedelta(minutes=5))
    db.add(pending);db.commit()
    old_rows={(a['guest_id'],a['night']):a['resource_id'] for a in before['assignments']}
    new_rows={(a['guest_id'],a['night']):a['resource_id'] for a in after}
    changes=[{'guest_id':gid,'night':night,'from':old_rows.get((gid,night)),'to':new_rows.get((gid,night))} for gid,night in sorted(old_rows.keys()|new_rows.keys()) if old_rows.get((gid,night))!=new_rows.get((gid,night))]
    cost=billing_data(db,rows=after)
    return {"token":str(pending.id),"revision":revision,"errors":[],"warnings":warnings,"summary":summaries_for(db,after),"changes":changes,"estimate":{"known_subtotal_paise":cost['known_subtotal_paise'],"unpriced":len(cost['unpriced'])}}


def summaries_for(db,rows):
    from .planning_rules import summaries
    return summaries(snapshot(db),rows)


@router.post("/assignments/preview",dependencies=WRITE)
def preview_moves(body:Moves,user:Editor,db:DB):
    locked_state(db,body.revision);current={(a["guest_id"],a["night"]):a for a in assignments(db)};seen=set()
    for move in body.moves:
        key=(str(move.guest_id),move.night)
        if key in seen:raise HTTPException(400,"Duplicate guest/night in the same move")
        seen.add(key)
        if not db.get(Guest,move.guest_id):raise HTTPException(404,"Guest no longer exists")
        if move.resource_id:
            if key not in current or current[key]["resource_id"]!=move.resource_id:
                current[key]={"guest_id":key[0],"night":key[1],"resource_id":move.resource_id}
        else:current.pop(key,None)
    after=sorted(current.values(),key=lambda a:(a["night"],a["guest_id"]))
    data=snapshot(db)
    pairs=sharing_candidates(data,after,{str(move.guest_id) for move in body.moves})
    result=preview_plan(db,user,body.revision,after,sharing_pairs=pairs if body.confirm_sharing else ())
    result["can_confirm_sharing"]=bool(pairs) and not body.confirm_sharing
    result["request_moves"]=[move.model_dump(mode="json") for move in body.moves]
    return result




@router.post("/assignments/apply",dependencies=WRITE)
def apply_assignment(body:ApplyInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);pending=db.get(PendingChange,body.token)
    if not pending or pending.kind!="assignment" or pending.owner_id!=user.id or pending.expires_at<=now():raise HTTPException(409,"This preview expired or was already applied. Preview the move again.")
    if pending.revision!=state.revision:raise HTTPException(409,"The plan changed after preview. Preview again.")
    data=snapshot(db);before=data["assignments"];after=pending.payload["after"]
    pairs=[tuple(pair) for pair in pending.payload.get("sharing_pairs",[])]
    if pairs and pairs!=sharing_candidates(data,after,{g for pair in pairs for g in pair}):raise HTTPException(409,"Sharing consent changed. Preview the move again.")
    result=hard_check(with_sharing(data,pairs),after,before)
    old={w['id'] for w in validate(data,before)['warnings']}
    expected={w["id"] for w in result["warnings"] if w['id'] not in old}|{sharing_warning(a,b)["id"] for a,b in pairs}
    if expected!={w["id"] for w in pending.warnings} or set(body.acknowledged)!=expected:raise HTTPException(409,"Explicitly acknowledge exactly the warnings in this preview.")
    direction=pending.payload.get('history_direction')
    if direction:
        change=db.get(PlanChange,uuid.UUID(pending.payload['history_change']))
        if not change:raise HTTPException(409,"History step is unavailable")
        if direction=='undo':
            if state.cursor!=change.id or before!=change.after or after!=change.before:raise HTTPException(409,"History changed after preview")
            state.redo=[*state.redo,str(change.id)];state.cursor=change.parent
        elif direction=='redo':
            if not state.redo or state.redo[-1]!=str(change.id) or state.cursor!=change.parent or before!=change.before or after!=change.after:raise HTTPException(409,"History changed after preview")
            state.redo=state.redo[:-1];state.cursor=change.id
        else:raise HTTPException(409,"History direction is invalid")
    else:
        change=PlanChange(parent=state.cursor,actor_id=user.id,before=before,after=after);db.add(change);db.flush()
        state.cursor=change.id;state.redo=[]
    if pending.payload.get('allocation_run'):
        run=db.get(AllocationRun,uuid.UUID(pending.payload['allocation_run']))
        if not run or run.owner_id!=user.id or run.status!='completed' or run.revision!=state.revision:raise HTTPException(409,"Allocation proposal changed; run again")
        run.status='applied'
    for a,b in pairs:
        db.add(GuestLink(a=uuid.UUID(a),b=uuid.UUID(b),kind="may_share",severity="hard"))
    save_assignments(db,after);db.delete(pending)
    return record(db,user,state,"assignment."+(direction or 'applied'),{"change_id":str(change.id),"warning_ids":sorted(expected),"sharing_pairs":pairs})


class HistoryInput(Revision):direction:Literal["undo","redo"]


@router.post("/history",dependencies=WRITE)
def history(body:HistoryInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);data=snapshot(db)
    if body.direction=="undo":
        change=db.get(PlanChange,state.cursor) if state.cursor else None
        if not change:raise HTTPException(409,"Nothing to undo")
        expected,after=change.after,change.before
    else:
        change=db.get(PlanChange,uuid.UUID(state.redo[-1])) if state.redo else None
        if not change or change.parent!=state.cursor:raise HTTPException(409,"Nothing to redo")
        expected,after=change.before,change.after
    if assignments(db)!=expected:raise HTTPException(409,"The current plan no longer matches this history step.")
    result=hard_check(data,after,data["assignments"])
    old={w["id"] for w in validate(data,data["assignments"])["warnings"]}
    new=[w for w in result["warnings"] if w["id"] not in old]
    if new:
        result=preview_plan(db,user,body.revision,after)
        pending=db.get(PendingChange,uuid.UUID(result['token']))
        pending.payload={**pending.payload,'history_direction':body.direction,'history_change':str(change.id)}
        db.commit();return result
    save_assignments(db,after)
    if body.direction=="undo":state.redo=[*state.redo,str(change.id)];state.cursor=change.parent
    else:state.redo=state.redo[:-1];state.cursor=change.id
    return record(db,user,state,"assignment."+body.direction,{"change_id":str(change.id)})


@router.get("/history")
def list_history(user:Editor,db:DB):
    return {"items":[{"id":str(a.id),"action":a.action,"created_at":a.created_at.isoformat(),"revision":a.entity_id} for a in db.scalars(select(Audit).where(~Audit.action.like('session.%')).order_by(Audit.created_at.desc()).limit(100))]}


@router.post("/allocation",dependencies=WRITE,status_code=202)
def queue_allocation(body:Revision,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    if db.scalar(select(AllocationRun.id).where(AllocationRun.status.in_(["queued","running"]))):raise HTTPException(409,"An allocation job is already running.")
    data=snapshot(db)
    # Solver input excludes contacts and private notes.
    for g in data["guests"]:g.pop("phone",None);g.pop("notes",None)
    run=AllocationRun(owner_id=user.id,revision=state.revision,snapshot=data,status="queued")
    db.add(run);db.commit()
    return {"id":str(run.id),"revision":run.revision,"status":run.status}


def run_view(run,state):
    return {"id":str(run.id),"revision":run.revision,"status":"stale" if run.revision!=state.revision and run.status=="completed" else run.status,"result":run.result,"created_at":run.created_at.isoformat()}


@router.get("/allocation")
def list_runs(user:Editor,db:DB):
    state=db.get(PlanState,1)
    return {"runs":[run_view(r,state) for r in db.scalars(select(AllocationRun).order_by(AllocationRun.created_at.desc()).limit(10))]}


@router.post("/allocation/{run_id}/preview",dependencies=WRITE)
def allocation_preview(run_id:uuid.UUID,body:Revision,user:Editor,db:DB):
    locked_state(db,body.revision);run=db.get(AllocationRun,run_id)
    if not run or run.status!="completed" or run.revision!=body.revision or not run.result or run.result.get("assignments") is None:raise HTTPException(409,"This proposal is unavailable or stale. Run allocation again.")
    result=preview_plan(db,user,body.revision,run.result["assignments"])
    if result.get('token'):
        pending=db.get(PendingChange,uuid.UUID(result['token']));pending.payload={**pending.payload,'allocation_run':str(run.id)};db.commit()
    return result


class MealInput(Input):
    guest_id:uuid.UUID
    day:Literal["2026-11-24","2026-11-25","2026-11-26"]
    meal:Literal["breakfast","lunch","dinner"]
    location:Literal["wyndham","second","external"]="wyndham"
    planned:bool=True
    actual:bool|None=None
    inclusion:Literal["included","chargeable","unconfirmed"]="unconfirmed"


class Meals(Revision):rows:list[MealInput]=Field(max_length=1000)


def meal_rows(db,ids=None):
    return [{"guest_id":str(m.guest_id),"day":m.day.isoformat(),"meal":m.meal,"location":m.location,"planned":m.planned,"actual":m.actual,"inclusion":m.inclusion} for m in db.scalars(select(MealAttendance)) if ids is None or str(m.guest_id) in ids]


@router.get("/meals")
def meals(user:Viewer,db:DB):
    data=visible_plan(db,user);rows=meal_rows(db,{g["id"] for g in data["guests"]})
    if user.role not in {"owner","editor"}:
        for row in rows:row.pop("inclusion")
    return {"revision":data["revision"],"rows":rows}


@router.put("/meals",dependencies=WRITE)
def save_meals(body:Meals,user:Editor,db:DB):
    state=locked_state(db,body.revision);seen=set()
    for item in body.rows:
        key=(item.guest_id,date.fromisoformat(item.day),item.meal,item.location)
        if key in seen:raise HTTPException(400,"Duplicate person/meal/location")
        seen.add(key)
        if not db.get(Guest,item.guest_id):raise HTTPException(404,"Guest not found")
        row=db.get(MealAttendance,key)
        if not row:row=MealAttendance(guest_id=key[0],day=key[1],meal=key[2],location=key[3]);db.add(row)
        row.planned,row.actual,row.inclusion=item.planned,item.actual,item.inclusion
    db.flush()
    counts={}
    for row in db.scalars(select(MealAttendance)):
        for basis in ['planned','actual']:
            if getattr(row,basis) is True:
                key=(row.guest_id,row.day,row.meal,basis);counts[key]=counts.get(key,0)+1
    if any(count>1 for count in counts.values()):raise HTTPException(409,"The same person cannot be counted for the same meal at two locations. Clear the other location for that attendance basis first.")
    return record(db,user,state,"attendance.saved",{"rows":len(body.rows)})


class PresenceInput(Revision):
    arrived_at:AwareDatetime|None=None
    departed_at:AwareDatetime|None=None


@router.put('/presence/{guest_id}',dependencies=WRITE)
def presence(guest_id:uuid.UUID,body:PresenceInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    if not db.get(Guest,guest_id):raise HTTPException(404,'Guest not found')
    if body.arrived_at and body.departed_at and body.departed_at<body.arrived_at:raise HTTPException(400,'Departure cannot precede actual arrival')
    row=db.get(GuestPresence,guest_id)
    if not row:row=GuestPresence(guest_id=guest_id);db.add(row)
    row.arrived_at,row.departed_at=body.arrived_at,body.departed_at
    return record(db,user,state,'presence.updated',{'guest_id':str(guest_id)})


class EventInput(Revision):
    name:str=Field(min_length=1,max_length=100)
    day:Literal['2026-11-24','2026-11-25','2026-11-26']
    side:Literal['bride','groom']|None=None
    start_time:str|None=Field(default=None,pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    venue:str=Field(default="",max_length=150)
    source_url:str=Field(default="",max_length=250)

    @field_validator('source_url')
    @classmethod
    def source_https(cls,value):
        if value and not value.startswith('https://'):raise ValueError('Use an https source link')
        return value


@router.post('/events',dependencies=WRITE,status_code=201)
def add_event(body:EventInput,user:Editor,db:DB):
    state=locked_state(db,body.revision)
    if not body.name.strip():raise HTTPException(400,'Enter a function/event name')
    if db.scalar(select(FunctionEvent.id).where(FunctionEvent.name==body.name.strip(),FunctionEvent.day==date.fromisoformat(body.day),FunctionEvent.side==body.side)):raise HTTPException(409,'This function already exists for that date and side.')
    event=FunctionEvent(**body.model_dump(exclude={'revision','day'}),day=date.fromisoformat(body.day));event.name=event.name.strip();db.add(event);db.flush()
    return {**record(db,user,state,'event.created',{'event_id':str(event.id)}),'id':str(event.id)}


def event_data(db,user):
    data=visible_plan(db,user);ids={g['id'] for g in data['guests']}
    events=[{'id':str(e.id),'name':e.name,'day':e.day.isoformat(),'side':e.side,'start_time':e.start_time,'venue':e.venue,'source_url':e.source_url} for e in db.scalars(select(FunctionEvent).order_by(FunctionEvent.day,FunctionEvent.start_time.asc().nullslast(),FunctionEvent.name)) if user.role!='family' or e.side is None or e.side==user.side]
    event_ids={e['id'] for e in events}
    rows=[{'event_id':str(a.event_id),'guest_id':str(a.guest_id),'planned':a.planned,'actual':a.actual} for a in db.scalars(select(EventAttendance)) if str(a.guest_id) in ids and str(a.event_id) in event_ids]
    return {'revision':data['revision'],'events':events,'rows':rows}


@router.get('/functions')
def get_events(user:Viewer,db:DB):return event_data(db,user)


class EventRow(Input):
    event_id:uuid.UUID
    guest_id:uuid.UUID
    planned:bool=True
    actual:bool|None=None


class EventRows(Revision):rows:list[EventRow]=Field(max_length=1000)


@router.put('/functions/attendance',dependencies=WRITE)
def event_attendance(body:EventRows,user:Editor,db:DB):
    state=locked_state(db,body.revision);seen=set()
    for item in body.rows:
        key=(item.event_id,item.guest_id)
        if key in seen:raise HTTPException(400,'Duplicate person/event')
        seen.add(key);event=db.get(FunctionEvent,item.event_id);guest=db.get(Guest,item.guest_id)
        if not event or not guest:raise HTTPException(404,'Function or guest not found')
        if event.side and db.get(Family,guest.family_id).side!=event.side:raise HTTPException(400,'This side-specific event does not include that guest side')
        row=db.get(EventAttendance,key)
        if not row:row=EventAttendance(event_id=item.event_id,guest_id=item.guest_id);db.add(row)
        row.planned,row.actual=item.planned,item.actual
    return record(db,user,state,'event.attendance_saved',{'rows':len(body.rows)})


def billing_data(db,basis="planned",rows=None):
    policy=db.get(EventPolicy,1);settings=db.get(BillingSettings,1)
    p={key:getattr(policy,key) for key in ["wyndham_allowance","wyndham_excess_paise","staff_meal_paise","second_hotel_day_paise","second_hotel_included"]}
    data=snapshot(db)
    if rows is not None:data['assignments']=rows
    result=calculate(data,p,{"guest_meals":settings.guest_meals,"second_extra_paise":settings.second_extra_paise},meal_rows(db),[r.day.isoformat() for r in db.scalars(select(HotelChargeDay))],basis=basis)
    result["revision"]=db.get(PlanState,1).revision
    return result


@router.get("/billing")
def billing(user:Editor,db:DB,basis:Literal["planned","actual"]="planned"):return billing_data(db,basis)


class Rates(Revision):
    wyndham_allowance:int=Field(ge=0,le=1000)
    wyndham_excess_paise:int=Field(ge=0,le=100000000)
    staff_meal_paise:int=Field(ge=0,le=100000000)
    second_hotel_day_paise:int=Field(ge=0,le=100000000)
    second_hotel_included:int=Field(ge=0,le=1000)
    guest_meals:dict[str,int|None]=Field(default_factory=dict)
    second_extra_paise:int|None=Field(default=None,ge=0,le=100000000)
    charge_days:list[Literal["2026-11-24","2026-11-25","2026-11-26"]]=Field(default_factory=list,max_length=3)

    @field_validator("guest_meals")
    @classmethod
    def meal_rates(cls,values):
        allowed={m+'_'+a for m in ['breakfast','lunch','dinner'] for a in ['adult','child']}
        if not set(values).issubset(allowed) or any(v is not None and (isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=100000000) for v in values.values()):raise ValueError("Enter exact non-negative meal rates or leave them unpriced")
        return values


@router.put("/billing/rates",dependencies=WRITE)
def rates(body:Rates,user:Editor,db:DB):
    state=locked_state(db,body.revision);policy=db.get(EventPolicy,1);settings=db.get(BillingSettings,1)
    before=billing_data(db)["policy"]
    for key in before:setattr(policy,key,getattr(body,key))
    settings.guest_meals,settings.second_extra_paise=body.guest_meals,body.second_extra_paise
    db.execute(delete(HotelChargeDay));db.add_all([HotelChargeDay(day=date.fromisoformat(d)) for d in sorted(set(body.charge_days))])
    return record(db,user,state,"rates.updated",{"before":before,"after":body.model_dump(exclude={"revision"})})


class SnapshotInput(Revision):basis:Literal["planned","actual"]="planned"


@router.post("/billing/snapshots",dependencies=WRITE)
def bill_snapshot(body:SnapshotInput,user:Editor,db:DB):
    locked_state(db,body.revision);data=billing_data(db,body.basis)
    saved=BillSnapshot(actor_id=user.id,revision=body.revision,data=data);db.add(saved)
    db.add(Audit(actor_id=user.id,action="estimate.saved",entity_id=str(body.revision),details={"basis":body.basis}));db.commit()
    return {"id":str(saved.id),"revision":saved.revision}


@router.get("/billing/snapshots")
def bill_snapshots(user:Editor,db:DB):return {"snapshots":[{"id":str(s.id),"revision":s.revision,"created_at":s.created_at.isoformat(),"data":s.data} for s in db.scalars(select(BillSnapshot).order_by(BillSnapshot.created_at.desc()).limit(20))]}


@router.get("/events")
async def events(request:Request,user:Viewer):
    token_hash=digest(request.cookies[COOKIE])
    async def stream():
        last=None
        while not await request.is_disconnected():
            with SessionLocal() as db:
                session=db.get(LoginSession,token_hash);current=db.get(User,user.id)
                if not session or session.expires_at<=now() or not current or not current.active:
                    yield 'event: expired\ndata: {}\n\n';return
                revision=db.get(PlanState,1).revision
            if last!=revision:
                yield 'event: revision\ndata: '+json.dumps({"revision":revision})+'\n\n';last=revision
            else:yield ': heartbeat\n\n'
            await asyncio.sleep(2)
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-store","X-Accel-Buffering":"no"})


class FamilyDetail(Input):
    side:Literal['bride','groom']
    name:str=Field(min_length=1,max_length=100)
    relationship:str=Field(min_length=1,max_length=80)

    @field_validator('name','relationship')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Enter a name and relationship')
        return value.strip()


class WeddingInput(Revision):
    bride_name:str=Field(default='',max_length=100)
    groom_name:str=Field(default='',max_length=100)
    source_url:str=Field(default='',max_length=250)
    family:list[FamilyDetail]=Field(default_factory=list,max_length=60)

    @field_validator('source_url')
    @classmethod
    def source_https(cls,value):
        if value and not value.startswith('https://'):raise ValueError('Use an https source link')
        return value

    @model_validator(mode='after')
    def unique_people(self):
        keys=[(p.side,p.name.casefold()) for p in self.family]
        if len(keys)!=len(set(keys)):raise ValueError('Each family person belongs in the directory once')
        return self


@router.get('/wedding-details')
def wedding_details(user:Viewer,db:DB):
    state=db.get(PlanState,1);row=db.get(WeddingDetails,1)
    data=copy.deepcopy(row.data) if row else {'bride_name':'','groom_name':'','source_url':'','family':[]}
    if user.role=='family':data['family']=[p for p in data['family'] if p['side']==user.side]
    return {'revision':state.revision,**data}


@router.put('/wedding-details',dependencies=WRITE)
def save_wedding_details(body:WeddingInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);row=db.get(WeddingDetails,1)
    if not row:row=WeddingDetails(id=1);db.add(row)
    row.data=body.model_dump(exclude={'revision'})
    return record(db,user,state,'wedding.details_updated',{'family_count':len(body.family)})
