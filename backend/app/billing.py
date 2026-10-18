"""Exact-pa​ise estimates with explicit missing-price and coverage boundaries."""
from .planning_rules import DAYS, NIGHTS, STAFF, active


def calculate(snapshot, policy, settings, meals, charge_days, *, basis="planned"):
    guests={g["id"]:g for g in snapshot["guests"]}
    resources={r["id"]:r for r in snapshot["resources"]}
    rows=snapshot["assignments"]
    lines=[];unpriced=[];night_totals={}
    for night in NIGHTS:
        located={a["guest_id"]:resources[a["resource_id"]] for a in rows if a["night"]==night}
        wyndham=[guests[g] for g,r in located.items() if r["hotel_id"]=="wyndham"]
        adults=sum(g["age"] is not None and g["age"]>10 for g in wyndham)
        unknown=sum(g["age"] is None for g in wyndham)
        excess=max(0,adults-policy["wyndham_allowance"])
        amount=excess*policy["wyndham_excess_paise"]
        lines.append({"day":night,"kind":"wyndham_excess","quantity":excess,"rate_paise":policy["wyndham_excess_paise"],"amount_paise":amount,"status":"planning_assumption"})
        second=sum(r["hotel_id"]=="second" for r in located.values())
        extra=max(0,second-policy["second_hotel_included"])
        if extra:
            if settings["second_extra_paise"] is None:unpriced.append({"day":night,"kind":"second_extra","quantity":extra,"reason":"Second-hotel extra-person rate is not supplied."})
            else:lines.append({"day":night,"kind":"second_extra","quantity":extra,"rate_paise":settings["second_extra_paise"],"amount_paise":extra*settings["second_extra_paise"],"status":"owner_entered_estimate"})
        if second and night not in charge_days:unpriced.append({"day":night,"kind":"second_day","quantity":second,"reason":"Confirm the second-hotel billable-day mapping; daily rate is provisional."})
        unassigned=sum(active(g,night) and g["id"] not in located for g in guests.values())
        if unassigned:unpriced.append({"day":night,"kind":"unassigned","quantity":unassigned,"reason":"Residents are unassigned; hotel-specific costs cannot yet be finalised."})
        if unknown:unpriced.append({"day":night,"kind":"age_unknown","quantity":unknown,"reason":"Chargeable ages are unresolved."})
        night_totals[night]={"wyndham_heads":len(wyndham),"chargeable":adults,"unknown_ages":unknown,"excess":excess,"excess_paise":amount,"second_heads":second,"unassigned":unassigned}
    for day in sorted(charge_days):
        lines.append({"day":day,"kind":"second_hotel_property","quantity":1,"rate_paise":policy["second_hotel_day_paise"],"amount_paise":policy["second_hotel_day_paise"],"status":"provisional"})
    for attendance in meals:
        g=guests.get(attendance["guest_id"])
        if not g:continue
        present=attendance["planned"] if basis=="planned" else attendance["actual"]
        if present is None:
            if attendance["planned"]:unpriced.append({"day":attendance["day"],"kind":"attendance_unknown","quantity":1,"reason":"Actual attendance has not been recorded."})
            continue
        if not present:continue
        base={"day":attendance["day"],"meal":attendance["meal"],"guest_id":g["id"],"quantity":1}
        if attendance["inclusion"]=="included":continue
        if attendance["inclusion"]=="unconfirmed":
            unpriced.append({**base,"kind":"coverage_unknown","reason":"Confirm package inclusion before charging this meal."});continue
        if attendance["location"]=="wyndham" and g["category"] in STAFF:
            rate=policy["staff_meal_paise"];kind="staff_meal"
        elif attendance["location"]=="wyndham" and g["age"] is not None:
            rate=settings["guest_meals"].get(attendance["meal"]+('_adult' if g["age"]>10 else '_child'));kind="guest_meal"
        else:rate=None;kind="meal_unpriced"
        if rate is None:unpriced.append({**base,"kind":kind,"reason":"The applicable meal rate is not supplied."})
        else:lines.append({**base,"kind":kind,"rate_paise":rate,"amount_paise":rate,"status":"confirmed_rate" if kind=="staff_meal" else "owner_entered_estimate"})
    unknown_ages=sum(g["age"] is None for g in guests.values())
    if unknown_ages:unpriced.append({"kind":"guest_ages_unknown","quantity":unknown_ages,"reason":"Complete unknown guest ages before final reconciliation."})
    return {"basis":basis,"currency":"INR","lines":lines,"known_subtotal_paise":sum(l["amount_paise"] for l in lines),"unpriced":unpriced,"complete":not unpriced,"provisional":True,"nights":night_totals,"policy":policy,"settings":settings,"charge_days":sorted(charge_days),"assumptions":["No Wyndham allowance carryover between nights.","Second-hotel daily price and billable days remain subject to confirmation.","Included bedding is not charged again.","Meal inclusion is explicit; unconfirmed coverage is not billed as a separate meal."]}
