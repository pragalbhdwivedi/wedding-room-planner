"""Bounded CP-SAT proposals; only the shared validator can approve output."""
from collections import defaultdict
from itertools import combinations

from ortools.sat.python import cp_model

from .planning_rules import NIGHTS, STAFF, active, building, capacity_ok, compatible, friend_rosters, is_adult, matches, resource_issues, segment, validate


def allocate(data,time_limit=10):
    guests={g["id"]:g for g in data["guests"] if g["arrival"]}
    resources={r["id"]:r for r in data["resources"]}
    if len(guests)>300:return {"solver_status":"input_limit","assignments":None,"diagnostics":["Automatic allocation supports up to 300 resident participants in this event."]}
    parent={g:g for g in guests}
    def root(g):
        while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
        return g
    def union(a,b):parent[root(a)]=root(b)
    families=defaultdict(list);rosters=friend_rosters(data)
    for g in guests.values():
        if g["category"]=="guest" and g["family_id"] not in rosters:families[g["family_id"]].append(g["id"])
    for members in families.values():
        for member in members[1:]:union(members[0],member)
    for link in data["links"]:
        if link["kind"]=="must_share" and link["severity"]=="hard" and link["a"] in guests and link["b"] in guests:union(link["a"],link["b"])
    groups=defaultdict(list)
    for gid in guests:groups[root(gid)].append(guests[gid])
    units=list(groups.values());unit_for={g["id"]:i for i,u in enumerate(units) for g in u}
    locked={(l["resource_id"],l["night"]) for l in data["locks"]}
    old=data["assignments"]
    fixed=[a for a in old if (a["resource_id"],a["night"]) in locked]
    fixed_keys={(a["guest_id"],a["night"]):a["resource_id"] for a in fixed}
    model=cp_model.CpModel();variables={};options={};scores=[];represented=set();diagnostics={}
    for i,people in enumerate(units):
        candidate=[];reasons=[]
        for rid,r in resources.items():
            issues=[x for g in people for x in resource_issues(g,r,data)]
            hard=[x for x in issues if x["severity"]=="hard"]
            if hard:reasons.extend(x["message"] for x in hard);continue
            if any(not capacity_ok([g for g in people if active(g,n)],r) for n in NIGHTS):
                reasons.append("The complete family/group does not fit the confirmed room capacity; review a manual split.");continue
            if any(not compatible(a,b,data["links"]) for a,b in combinations(people,2)):
                reasons.append("This group has a mandatory sharing exclusion.");continue
            valid=True
            for n in NIGHTS:
                members={g["id"] for g in people if active(g,n)}
                if any((gid,n) in fixed_keys and fixed_keys[(gid,n)]!=rid for gid in members):valid=False
                if (rid,n) in locked and not members.issubset({a["guest_id"] for a in fixed if a["resource_id"]==rid and a["night"]==n}):valid=False
            if not valid:reasons.append("Existing room locks limit this group; unlock or review a manual arrangement.");continue
            variable=model.new_bool_var(f"u{i}_{rid}");variables[(i,rid)]=variable;candidate.append(rid)
            count=sum(active(g,n) for g in people for n in NIGHTS)
            preference=sum(x["severity"]=="warning" for x in issues)*25
            preference+=sum('near_restaurant' in g['tags'] for g in people)* (0 if r['near_restaurant'] else 25)
            preference-=10 if r["reserved"] and all(g["reserved_eligible"] for g in people) else 0
            # Preserve valid existing placements where this does not reduce assigned people.
            retained=sum(a["resource_id"]==rid and a["guest_id"] in {g['id'] for g in people} for a in old)
            scores.append(variable*(count*1000000-preference+retained*3))
        options[i]=candidate
        if candidate:
            selected=sum(variables[(i,r)] for r in candidate)
            anchored=any((g['id'],n) in fixed_keys for g in people for n in NIGHTS)
            model.add(selected==1 if anchored else selected<=1)
            if anchored:represented.update((g['id'],n) for g in people for n in NIGHTS)
        else:diagnostics[i]=sorted(set(reasons))[:4] or ["No compatible room is available for the complete group."]
    constants=[a for a in fixed if (a["guest_id"],a["night"]) not in represented]
    # Room/bed capacity and pair compatibility apply per night.
    side_used={};premium_usage=defaultdict(list)
    for rid,r in resources.items():
        for n in NIGHTS:
            contributors=[(i,[g for g in u if active(g,n)]) for i,u in enumerate(units) if (i,rid) in variables and any(active(g,n) for g in u)]
            constant=[guests[a["guest_id"]] for a in constants if a["resource_id"]==rid and a["night"]==n]
            total=sum(variables[(i,rid)]*len(p) for i,p in contributors)+len(constant)
            adults=sum(variables[(i,rid)]*sum(is_adult(g) for g in p) for i,p in contributors)+sum(is_adult(g) for g in constant)
            model.add(adults<=r["adult_capacity"])
            model.add(total-adults<=2)  # Larger young-child arrangements await policy confirmation.
            model.add(total<=(1 if r["hotel_id"]=="staff" else 4))
            if r["category"]=="superior":
                four=model.new_bool_var(f"four_{rid}_{n}")
                model.add(total<=3).only_enforce_if(four.Not())
                model.add(total==4).only_enforce_if(four)
                model.add(adults==2).only_enforce_if(four)
            used=model.new_bool_var(f"used_{rid}_{n}")
            model.add(total>=1).only_enforce_if(used);model.add(total==0).only_enforce_if(used.Not())
            scores.append(-100*used)
            if r["hotel_id"]=="wyndham" and r["category"]=="premium":premium_usage[rid].append(used)
            for i,p in contributors:
                if any(not compatible(a,b,data['links']) for a in p for b in constant):model.add(variables[(i,rid)]==0)
            for (i,a),(j,b) in combinations(contributors,2):
                if any(not compatible(x,y,data['links']) for x in a for y in b):model.add(variables[(i,rid)]+variables[(j,rid)]<=1)
            if r['hotel_id']!='staff':
                for side in ['bride','groom']:
                    candidates=[variables[(i,rid)] for i,p in contributors if any(g['side']==side and g['category']=='guest' for g in p)]
                    has_constant=any(g['side']==side and g['category']=='guest' for g in constant)
                    flag=model.new_bool_var(f"side_{side}_{rid}_{n}")
                    if has_constant:model.add(flag==1)
                    elif candidates:model.add_max_equality(flag,candidates)
                    else:model.add(flag==0)
                    side_used[(side,rid,n)]=flag
    if data['reserved_count']==0:
        held=[]
        for rid,flags in premium_usage.items():
            used=model.new_bool_var('premium_any_'+rid);model.add_max_equality(used,flags);held.append(used)
        model.add(sum(held)<=20)
    for link in data['links']:
        if link['severity']!='hard' or link['kind'] not in {'nearby','same_building'} or link['a'] not in unit_for or link['b'] not in unit_for:continue
        i,j=unit_for[link['a']],unit_for[link['b']]
        if i==j:continue
        if options[i] and options[j]:
            model.add(sum(variables[(i,r)] for r in options[i])==sum(variables[(j,r)] for r in options[j]))
            for a in options[i]:
                for b in options[j]:
                    allowed=building(resources[a])==building(resources[b]) if link['kind']=='same_building' else a==b or any({c['a'],c['b']}=={a,b} for c in data['connections'])
                    if not allowed:model.add(variables[(i,a)]+variables[(j,b)]<=1)
    for rule in data['rules']:
        if rule['severity']!='hard':continue
        if rule['kind']=='side_quota':
            # Quotas with tag selectors need their own occupancy flags.
            for n in NIGHTS:
                flags=[]
                for rid,r in resources.items():
                    if r['hotel_id']=='staff':continue
                    terms=[variables[(i,rid)] for i,u in enumerate(units) if (i,rid) in variables and any(matches(g,rule) and active(g,n) and g['category']=='guest' for g in u)]
                    const=any(a['resource_id']==rid and a['night']==n and matches(guests[a['guest_id']],rule) for a in constants)
                    flag=model.new_bool_var(f"quota_{rule['id']}_{rid}_{n}")
                    if const:model.add(flag==1)
                    elif terms:model.add_max_equality(flag,terms)
                    else:model.add(flag==0)
                    flags.append(flag)
                model.add(sum(flags)<=rule['parameters']['maximum'])
        elif rule['kind']=='separate_sides':
            for n in NIGHTS:
                parts=defaultdict(list)
                for rid,r in resources.items():
                    if r['hotel_id']!='staff':parts[segment(r,rule['parameters']['scope'])].append(rid)
                for part,rids in parts.items():
                    flags=[]
                    for side in ['bride','groom']:
                        terms=[variables[(i,rid)] for rid in rids for i,u in enumerate(units) if (i,rid) in variables and any(g['side']==side and matches(g,rule) and active(g,n) and g['category']=='guest' for g in u)]
                        const=any(a['resource_id'] in rids and a['night']==n and guests[a['guest_id']]['side']==side and matches(guests[a['guest_id']],rule) for a in constants)
                        flag=model.new_bool_var(f"apart_{rule['id']}_{part}_{side}_{n}")
                        if const:model.add(flag==1)
                        elif terms:model.add_max_equality(flag,terms)
                        else:model.add(flag==0)
                        flags.append(flag)
                    model.add(sum(flags)<=1)
    model.maximize(sum(scores));solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=min(15,max(1,time_limit))
    solver.parameters.num_search_workers=2;solver.parameters.random_seed=23
    status=solver.solve(model)
    label={cp_model.OPTIMAL:'optimal',cp_model.FEASIBLE:'feasible',cp_model.INFEASIBLE:'infeasible',cp_model.UNKNOWN:'timeout',cp_model.MODEL_INVALID:'invalid_model'}.get(status,'unknown')
    if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:return {'solver_status':label,'assignments':None,'diagnostics':['No feasible proposal was returned within the configured constraints/time limit. Existing assignments were not changed.']}
    after=list(constants)
    for (i,rid),var in variables.items():
        if solver.boolean_value(var):
            after.extend({'guest_id':g['id'],'night':n,'resource_id':rid} for g in units[i] for n in NIGHTS if active(g,n))
    after=sorted(after,key=lambda a:(a['night'],a['guest_id']))
    checked=validate(data,after,before=old)
    if checked['errors']:return {'solver_status':'unresolved','assignments':None,'diagnostics':[e['message'] for e in checked['errors'][:20]],'errors':checked['errors']}
    located={(a['guest_id'],a['night']) for a in after}
    unassigned=[{'guest_id':g['id'],'night':n,'reasons':diagnostics.get(unit_for[g['id']],['Available compatible rooms were insufficient while preserving mandatory rules, groups and locks.'])} for g in guests.values() for n in NIGHTS if active(g,n) and (g['id'],n) not in located]
    return {'solver_status':label,'assignments':after,'assigned_count':len(after),'unassigned':unassigned,'warnings':checked['warnings'],'diagnostics':['Families are kept together in automatic proposals; review manual splits for groups that cannot fit.','Unassigned guests remain visible; optimal means optimal within these units and constraints.']}
