import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete, select

from .models import Assignment, Family, Guest, GuestLink, GuestPresence, PlanState, PlanningRule, Resource, Room, RoomConnection, RoomLock
from .planning_rules import summaries, validate


def locked_state(db, expected):
    state=db.scalar(select(PlanState).where(PlanState.id==1).with_for_update())
    if state.revision!=expected:raise HTTPException(409,"The plan changed in another session. Refresh before trying again.")
    return state


def assignments(db):
    return sorted([{"guest_id":str(a.guest_id),"night":a.night.isoformat(),"resource_id":a.resource_id} for a in db.scalars(select(Assignment))],key=lambda a:(a['night'],a['guest_id']))


def snapshot(db):
    families=[{"id":str(f.id),"label":f.label,"side":f.side,"reserved_eligible":f.reserved_eligible,"couple_children":f.couple_children} for f in db.scalars(select(Family).order_by(Family.label,Family.id))]
    family_map={f["id"]:f for f in families}
    guests=[]
    for g in db.scalars(select(Guest).order_by(Guest.family_id,Guest.id)):
        f=family_map[str(g.family_id)]
        guests.append({"id":str(g.id),"family_id":str(g.family_id),"name":g.name,"age":g.age,"age_band":g.age_band,"gender":g.gender,"sharing_mode":g.sharing_mode,"group_label":f["label"],"category":g.category,"phone":g.phone,"arrival":g.arrival.isoformat() if g.arrival else None,"tags":g.tags,"notes":g.notes,"side":f["side"],"reserved_eligible":f["reserved_eligible"],"couple_children":f["couple_children"]})
    rooms={r.id:r for r in db.scalars(select(Room))}
    resources=[]
    for r in db.scalars(select(Resource).order_by(Resource.id)):
        room=rooms.get(r.room_id)
        resources.append({"id":r.id,"number":room.number if room else f"Bed {r.staff_bed_id}","hotel_id":room.hotel_id if room else "staff","category":room.category if room else "dormitory","block":room.block if room else None,"floor":room.floor if room else None,"adult_capacity":room.adult_capacity if room else 1,"bed_type":room.bed_type if room else "single","reserved":r.reserved,"near_restaurant":r.near_restaurant,"x":r.x,"y":r.y})
    return {"families":families,"guests":guests,"resources":resources,"reserved_count":sum(r["reserved"] for r in resources),"assignments":assignments(db),
            "locks":[{"resource_id":l.resource_id,"night":l.night.isoformat()} for l in db.scalars(select(RoomLock))],
            "links":[{"id":str(l.id),"a":str(l.a),"b":str(l.b),"kind":l.kind,"severity":l.severity} for l in db.scalars(select(GuestLink))],
            "connections":[{"a":c.a,"b":c.b,"kind":c.kind} for c in db.scalars(select(RoomConnection))],
            "rules":[{"id":str(r.id),"name":r.name,"kind":r.kind,"severity":r.severity,"side":r.side,"tag":r.tag,"parameters":r.parameters} for r in db.scalars(select(PlanningRule))]}


def visible_plan(db,user):
    state=db.get(PlanState,1);data=snapshot(db)
    all_guests=data["guests"]
    if user.role=="family":
        data["families"]=[f for f in data["families"] if f["side"]==user.side]
        data["guests"]=[g for g in all_guests if g["side"]==user.side]
    ids={g["id"] for g in data["guests"]}
    data['presence']=[{'guest_id':str(p.guest_id),'status':'departed' if p.departed_at else 'arrived' if p.arrived_at else 'not_recorded',**({'arrived_at':p.arrived_at.isoformat() if p.arrived_at else None,'departed_at':p.departed_at.isoformat() if p.departed_at else None} if user.role!='family' else {})} for p in db.scalars(select(GuestPresence)) if str(p.guest_id) in ids]
    data["assignments"]=[a for a in data["assignments"] if a["guest_id"] in ids]
    data["summary"]=summaries(data,data["assignments"],ids)
    if user.role=="family":
        for s in data["summary"].values():
            s["free_rooms"]=None
            for property in s["properties"].values():property["empty"]=None
            s["side_rooms"]={user.side:s["side_rooms"][user.side]}
    if user.role!="owner":
        for g in data["guests"]:
            g.pop("notes",None)
            if user.role=="family":g.pop("phone",None)
        data.pop("links");data.pop("rules")
    else:
        data["conflicts"]=validate(data,data["assignments"])
        data["can_undo"]=state.cursor is not None;data["can_redo"]=bool(state.redo)
    data["reserve_pool"]=4 if data["reserved_count"]==0 else 0
    data["revision"]=state.revision
    return data


def save_assignments(db,rows):
    db.execute(delete(Assignment))
    db.add_all([Assignment(guest_id=uuid.UUID(a["guest_id"]),night=date.fromisoformat(a["night"]),resource_id=a["resource_id"]) for a in rows])
    db.flush()


def hard_check(data,rows,before=None):
    result=validate(data,rows,before=before)
    if result["errors"]:raise HTTPException(409,{"message":"The change conflicts with mandatory planning rules.","errors":result["errors"]})
    return result
