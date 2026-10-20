"""Project an owner edit and find a bounded, local placement repair."""
import copy
import uuid
from itertools import islice,product

from .planning_rules import NIGHTS,active,capacity_ok,compatible,resource_issues,validate


def project_edit(before,fid,body):
    data=copy.deepcopy(before)
    family=next(f for f in data['families'] if f['id']==fid)
    family.update({k:body[k] for k in ['label','side','reserved_eligible','couple_children','required_room_type']})
    existing={g['id'] for g in before['guests'] if g['family_id']==fid}
    supplied=[str(m['id']) for m in body['members'] if m.get('id')]
    if len(supplied)!=len(set(supplied)) or not set(supplied).issubset(existing):
        raise ValueError('A guest slot is duplicated or belongs to another family.')
    removed=sorted(existing-set(supplied))
    people=[]
    for member in body['members']:
        g={**member,'id':str(member.get('id') or uuid.uuid4()),'family_id':fid,'side':family['side'],'group_label':family['label'],'reserved_eligible':family['reserved_eligible'],'couple_children':family['couple_children'],'required_room_type':family['required_room_type']}
        people.append(g)
    data['guests']=[g for g in data['guests'] if g['family_id']!=fid]+people
    data['links']=[link for link in data['links'] if link['a'] not in removed and link['b'] not in removed]
    if len(data['guests'])>1000:raise ValueError('This event supports at most 1,000 guest slots.')
    return data,{'family':family,'guests':people,'removed_guest_ids':removed}


def changed_rows(before,after):
    a={(x['guest_id'],x['night']):x['resource_id'] for x in before}
    b={(x['guest_id'],x['night']):x['resource_id'] for x in after}
    return [{'guest_id':g,'night':n,'from':a.get((g,n)),'to':b.get((g,n))} for g,n in sorted(a.keys()|b.keys()) if a.get((g,n))!=b.get((g,n))]


def repair_placements(before,data,fid):
    gmap={g['id']:g for g in data['guests']};old=[a for a in before['assignments'] if a['guest_id'] in gmap]
    ids={g['id'] for g in data['guests'] if g['family_id']==fid}
    # Include hard must-share companions and their households in the repair unit.
    while True:
        prior=set(ids)
        for link in data['links']:
            if link['kind']=='must_share' and link['severity']=='hard' and ({link['a'],link['b']}&ids):ids.update([link['a'],link['b']])
        family_ids={gmap[g]['family_id'] for g in ids}
        ids.update(g['id'] for g in data['guests'] if g['family_id'] in family_ids)
        if ids==prior:break
    baseline=[a for a in old if a['guest_id'] not in ids]
    previous_beds={(a['guest_id'],a['night'],a['resource_id']) for a in old if a.get('separate_bed')}
    nights=[n for n in NIGHTS if any(a['guest_id'] in ids and a['night']==n for a in old)]
    def rows(rooms):
        return sorted(baseline+[{'guest_id':g['id'],'night':n,'resource_id':rid,**({'separate_bed':True} if (g['id'],n,rid) in previous_beds else {})} for n,rid in rooms.items() if rid for g in data['guests'] if g['id'] in ids and active(g,n)],key=lambda a:(a['night'],a['guest_id']))
    options={}
    for n in nights:
        people=[g for g in data['guests'] if g['id'] in ids and active(g,n)]
        previous={a['resource_id'] for a in old if a['guest_id'] in ids and a['night']==n}
        candidates=[]
        for r in data['resources']:
            occupants=[gmap[a['guest_id']] for a in baseline if a['resource_id']==r['id'] and a['night']==n]
            if any(x['severity']=='hard' for g in people for x in resource_issues(g,r,data)):continue
            if not capacity_ok(people+occupants,r) or any(not compatible(a,b,data['links']) for i,a in enumerate(people+occupants) for b in (people+occupants)[i+1:]):continue
            candidates.append((r['id'] not in previous,bool(occupants),r['floor'] or 0,r['id']))
        options[n]=[c[-1] for c in sorted(candidates)]
    # Prefer one room for the whole stay, then try a bounded set of dated choices.
    common=set.intersection(*(set(options[n]) for n in nights)) if nights else set()
    attempts=[{n:rid for n in nights} for rid in options[nights[0]] if rid in common] if nights else []
    attempts += [dict(zip(nights,p)) for p in islice(product(*(options[n][:12] for n in nights)),144)]
    attempts.append({n:None for n in nights})
    for choice in attempts:
        after=rows(choice)
        if not validate(data,after,before=before['assignments'])['errors']:
            return after,('Details require a placement correction. Review the proposed room changes before saving.' if any(choice.values()) else 'No valid local room move was found. Review saving these details and leaving the affected household unassigned; locks and mandatory rules still apply.')
    return None,'Existing locks or linked placement rules prevent a safe correction. Keep this form open; unlock or arrange the affected rooms before saving.'
