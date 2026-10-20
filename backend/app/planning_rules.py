"""One pure validation authority for moves, imports, history and solver output."""
from collections import defaultdict
from itertools import combinations

NIGHTS = ("2026-11-24", "2026-11-25")
DAYS = (*NIGHTS, "2026-11-26")
STAFF = {"driver", "staff", "vendor"}


def age_band(guest):
    age=guest.get("age")
    return ("adult" if age>10 else "child") if age is not None else guest.get("age_band","unknown")


def is_adult(guest):return age_band(guest)=="adult"


def is_friend(guest):
    return guest.get('sharing_mode')=='friends' and guest['category']=='guest' and is_adult(guest) and not guest.get('couple_children',False)


def friend_rosters(data):
    return {f['id'] for f in data['families'] if (people:=[g for g in data['guests'] if g['family_id']==f['id'] and g['category']=='guest']) and all(is_friend(g) for g in people)}


def friend_pair(a,b):
    return a.get('gender','unspecified') in {'male','female'} and a.get('gender')==b.get('gender') and a['side']==b['side']


def active(guest, night):
    return guest.get("arrival") in NIGHTS and guest["arrival"] <= night <= NIGHTS[-1]


def matches(guest, rule):
    return (not rule.get("side") or guest["side"] == rule["side"]) and (not rule.get("tag") or rule["tag"] in guest["tags"])


def issue(code, message, *, severity="hard", guests=(), resources=(), night=None):
    # IDs bind acknowledgement to a concrete warning, not a generic override.
    key = ":".join([code, str(night or ""), ",".join(sorted(guests)), ",".join(sorted(resources))])
    return {"id": key, "code": code, "message": message, "severity": severity,
            "guest_ids": sorted(guests), "resource_ids": sorted(resources), "night": night}


def resource_issues(guest, resource, snapshot):
    result = []
    def fail(code, message):result.append(issue(code, message, guests=[guest["id"]], resources=[resource["id"]]))
    if (guest["category"] in STAFF) != (resource["hotel_id"] == "staff"):
        fail("staff_separation", "Guests use hotel rooms; drivers, staff and vendors use dormitory beds only.")
    if age_band(guest)=="unknown":
        fail("age_unknown", "Enter the guest's age before assignment; unknown age is unresolved.")
    elif guest["age"] is None:
        result.append(issue("age_unconfirmed", "Draft uses the supplied adult/child count. Confirm exact age and any age-50+ ground-floor requirement.", severity="notice", guests=[guest["id"]],resources=[resource["id"]]))
    if (guest["age"] is not None and guest["age"] >= 50 or "ground_floor" in guest["tags"]) and resource["floor"] != 0:
        fail("ground_floor", "Age 50+ or a ground-floor tag requires a known ground-floor room.")
    if resource["hotel_id"] == "second" and "second_hotel" not in guest["tags"]:
        fail("second_hotel", "This guest needs the second-hotel eligibility tag.")
    if "second_hotel_only" in guest["tags"] and resource["hotel_id"]!="second":
        fail("accommodation_choice", "This guest is marked for the separate hotel.")
    if "main_hotel" in guest["tags"] and resource["hotel_id"]!="wyndham":
        fail("accommodation_choice", "This guest is marked for Wyndham.")
    if resource["reserved"] and not guest["reserved_eligible"]:
        fail("reserved_family", "This room is reserved for eligible family guests.")
    if resource["hotel_id"] == "wyndham" and resource["category"] == "premium":
        if guest["couple_children"]:
            fail("couple_children", "A couple with children uses a Superior room with extra bedding at Wyndham.")
    for rule in snapshot.get("rules", []):
        if rule["kind"] == "allowed_resources" and matches(guest, rule) and resource["id"] not in rule["parameters"]["resource_ids"]:
            result.append(issue("rule_"+rule["id"], rule["name"], severity=rule["severity"], guests=[guest["id"]], resources=[resource["id"]]))
    return result


def capacity_ok(people, resource):
    if any(age_band(p)=="unknown" for p in people):return False
    adults = sum(is_adult(p) for p in people)
    if len(people)-adults>2:return False  # Larger young-child arrangements are unconfirmed.
    if adults > resource["adult_capacity"]:return False
    if resource["hotel_id"] == "staff":return len(people) <= 1
    if resource["category"] == "superior":
        return len(people) <= 3 or (len(people) == 4 and adults == 2)
    return len(people) <= 4


def compatible(a, b, links):
    pair = {a["id"], b["id"]}
    relevant = [l for l in links if {l["a"],l["b"]} == pair]
    if any(l["kind"] == "cannot_share" and l["severity"] == "hard" for l in relevant):return False
    if is_friend(a) and is_friend(b):return friend_pair(a,b)
    return a["family_id"] == b["family_id"] or any(l["kind"] in {"may_share", "must_share"} for l in relevant)


def building(resource):return (resource["hotel_id"], resource["block"])


def segment(resource, scope):
    if scope == "room":return resource["id"]
    if scope == "block":return str(building(resource))
    return str((*building(resource),resource["floor"]))


def validate(snapshot, assignments, *, before=None):
    guests = {g["id"]:g for g in snapshot["guests"]}
    resources = {r["id"]:r for r in snapshot["resources"]}
    links = snapshot.get("links", [])
    result, cells, by_guest, seen = [], defaultdict(list), {}, set()
    for a in assignments:
        gid, rid, night = a["guest_id"], a["resource_id"], a["night"]
        if (gid,night) in seen:
            result.append(issue("overlap", "One guest cannot occupy two rooms on the same night.", guests=[gid], night=night));continue
        seen.add((gid,night))
        if gid not in guests or rid not in resources or night not in NIGHTS:
            result.append(issue("invalid_reference", "The plan references a missing guest, room or night."));continue
        g,r = guests[gid], resources[rid]
        if not active(g,night):result.append(issue("stay", "The guest is not resident on this night.", guests=[gid], night=night))
        for item in resource_issues(g,r,snapshot):
            item["night"]=night;item["id"] += ":"+night;result.append(item)
        cells[(rid,night)].append(g);by_guest[(gid,night)]=rid
        if "near_restaurant" in g["tags"] and not r["near_restaurant"]:
            result.append(issue("restaurant", "Restaurant proximity is requested but not confirmed for this room.", severity="warning", guests=[gid], resources=[rid], night=night))
    for (rid,night), people in cells.items():
        r=resources[rid];gids=[g["id"] for g in people]
        if not capacity_ok(people,r):result.append(issue("capacity", "Adult capacity or the confirmed child-sharing arrangement is exceeded/unresolved.", guests=gids, resources=[rid],night=night))
        for a,b in combinations(people,2):
            if not compatible(a,b,links):result.append(issue("compatibility", "Friends share only with the same specified gender and side. Other unrelated guests need explicit sharing compatibility; mandatory exclusions remain enforced.", guests=[a["id"],b["id"]], resources=[rid],night=night))
    if snapshot["reserved_count"]==0:
        premium={a['resource_id'] for a in assignments if a['resource_id'] in resources and resources[a['resource_id']]['hotel_id']=='wyndham' and resources[a['resource_id']]['category']=='premium'}
        premium_count=sum(r['hotel_id']=='wyndham' and r['category']=='premium' for r in resources.values())
        if len(premium)>premium_count-4:result.append(issue('reserve_pool','Four Premium rooms must stay unused across both nights until named family rooms are chosen.',resources=premium))
    rosters=friend_rosters(snapshot)
    for night in NIGHTS:
        for family in snapshot["families"]:
            if family["id"] in rosters:continue
            people=[g for g in guests.values() if g["family_id"]==family["id"] and g["category"]=="guest" and active(g,night)]
            places={by_guest.get((g["id"],night)) for g in people}
            if len(places)>1 and places!={None}:
                result.append(issue("family_split", "Family members are split or partly unassigned. Confirm this arrangement explicitly.",severity="warning",guests=[g["id"] for g in people],resources=[p for p in places if p],night=night))
        for link in links:
            a,b=by_guest.get((link["a"],night)),by_guest.get((link["b"],night))
            if not (a or b):continue
            ga,gb=guests.get(link["a"]),guests.get(link["b"])
            if not ga or not gb or not active(ga,night) or not active(gb,night):continue
            valid=True
            if link["kind"]=="must_share":valid=a is not None and a==b
            elif link["kind"]=="cannot_share":valid=not a or a!=b
            elif link["kind"]=="same_building":valid=a is not None and b is not None and building(resources[a])==building(resources[b])
            elif link["kind"]=="nearby":valid=a is not None and b is not None and (a==b or any({c["a"],c["b"]}=={a,b} for c in snapshot.get("connections",[])))
            if not valid:result.append(issue("link_"+link["id"], "A "+link["kind"].replace('_',' ')+" relationship is not satisfied; room proximity needs verified connections.",severity=link["severity"],guests=[link["a"],link["b"]],resources=[p for p in [a,b] if p],night=night))
        for rule in snapshot.get("rules",[]):
            chosen=[g for g in guests.values() if matches(g,rule) and g["category"]=="guest" and (g["id"],night) in by_guest]
            if rule["kind"]=="side_quota":
                places={by_guest[(g["id"],night)] for g in chosen}
                if len(places)>rule["parameters"]["maximum"]:result.append(issue("rule_"+rule["id"],rule["name"],severity=rule["severity"],guests=[g["id"] for g in chosen],resources=places,night=night))
            elif rule["kind"]=="separate_sides":
                parts=defaultdict(list)
                for g in chosen:parts[segment(resources[by_guest[(g["id"],night)]],rule["parameters"]["scope"])].append(g)
                for people in parts.values():
                    if len({g["side"] for g in people})>1:result.append(issue("rule_"+rule["id"],rule["name"],severity=rule["severity"],guests=[g["id"] for g in people],resources={by_guest[(g["id"],night)] for g in people},night=night))
    if before is not None:
        def occupants(values,rid,night):return {a["guest_id"] for a in values if a["resource_id"]==rid and a["night"]==night}
        for lock in snapshot.get("locks",[]):
            rid,night=lock["resource_id"],lock["night"]
            if occupants(before,rid,night)!=occupants(assignments,rid,night):result.append(issue("locked", "Unlock this room/bed before changing its occupants.",resources=[rid],night=night))
    unique={i["id"]:i for i in result}
    return {"errors":[i for i in unique.values() if i["severity"]=="hard"],"warnings":[i for i in unique.values() if i["severity"]=="warning"],"notices":[i for i in unique.values() if i["severity"]=="notice"]}


def summaries(snapshot, assignments, guest_ids=None):
    selected=[g for g in snapshot["guests"] if guest_ids is None or g["id"] in guest_ids]
    resources={r["id"]:r for r in snapshot["resources"]}
    out={}
    for night in NIGHTS:
        residents=[g for g in selected if active(g,night)]
        rows=[a for a in assignments if a["night"]==night and a["guest_id"] in {g["id"] for g in residents}]
        used={a["resource_id"] for a in rows}
        regular={r for r in used if resources[r]["hotel_id"]!="staff"}
        sides={side:len({a["resource_id"] for a in rows if any(g["id"]==a["guest_id"] and g["side"]==side for g in residents) and resources[a["resource_id"]]["hotel_id"]!="staff"}) for side in ["bride","groom"]}
        bedding=0;mixed=0
        for rid in regular:
            people=[g for g in residents if any(a["guest_id"]==g["id"] and a["resource_id"]==rid for a in rows)]
            extra=max(0,sum(is_adult(g) for g in people)-2)
            if any(g["couple_children"] and age_band(g)=="child" for g in people):extra=max(1,extra)
            bedding+=extra;mixed+=len({g["side"] for g in people})>1
        out[night]={"residents":len(residents),"assigned":len(rows),"unassigned":len(residents)-len(rows),"used_rooms":len(regular),"free_rooms":50-len(regular),"reserved":snapshot["reserved_count"],"side_rooms":sides,"mixed_rooms":mixed,"staff_beds_used":sum(resources[r]["hotel_id"]=="staff" for r in used),"extra_bedding":bedding}
        out[night]["properties"]={hotel:{"used":sum(resources[r]["hotel_id"]==hotel for r in regular),"empty":capacity-sum(resources[r]["hotel_id"]==hotel for r in regular)} for hotel,capacity in [("wyndham",44),("second",6)]}
        out[night]["unconfirmed_ages"]=sum(g["age"] is None for g in residents)
        out[night]["reserve_pool"]=4 if snapshot["reserved_count"]==0 else 0
    return out
