import copy
import io
import uuid
import zipfile
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import ValidationError
from sqlalchemy import select

from .models import Family, Guest, PendingChange, now
from .planning_api import ApplyInput, DB, GuestInput, Editor, Viewer, WRITE, billing_data, event_data, meal_rows, record
from .planning_rules import issue, validate
from .planning_store import hard_check, locked_state, snapshot, visible_plan

router=APIRouter(prefix="/api/planning")
HEADERS=['Guest ID','Family ID','Group','Side','Reserved eligible','Couple with children','Name','Age','Category','Phone','Arrival','Tags','Private notes','Age band','Gender','Sharing mode','Family room type']


def safe(value):
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):return "'"+value
    return value


def decorate(sheet):
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    for cell in sheet[1]:cell.fill=PatternFill('solid',fgColor='183D35');cell.font=Font(color='FFFFFF',bold=True)
    for index,column in enumerate(sheet.columns,1):
        width=min(42,max(14,max(len(str(cell.value or '')) for cell in column[:100])+2))
        sheet.column_dimensions[get_column_letter(index)].width=width


@router.get('/export.xlsx')
def export(user:Viewer,db:DB,template:bool=False):
    editor=user.role in {'owner','editor'}
    if template and not editor:raise HTTPException(403,'Only an owner or editor can import guest templates')
    data=visible_plan(db,user);workbook=Workbook();sheet=workbook.active;sheet.title='Guests'
    headers=HEADERS if editor else [h for h in HEADERS if h not in ['Private notes','Reserved eligible','Couple with children','Family room type'] and not (h=='Phone' and user.role=='family')]
    sheet.append(headers)
    families={f['id']:f for f in data['families']}
    if not template:
        for g in data['guests']:
            f=families[g['family_id']]
            row=dict(zip(HEADERS,[g['id'],g['family_id'],f['label'],g['side'],f['reserved_eligible'],f['couple_children'],g['name'],g['age'],g['category'],g.get('phone'),g['arrival'],', '.join(g['tags']),g.get('notes',''),g.get('age_band','unknown'),g.get('gender','unspecified'),g.get('sharing_mode','family'),f.get('required_room_type')]))
            sheet.append([safe(row[h]) for h in headers])
        assigned=workbook.create_sheet('Assignments');assigned.append(['Guest ID','Night','Room or bed ID','Separate bed for child'])
        for a in data['assignments']:assigned.append([a['guest_id'],a['night'],a['resource_id'],a.get('separate_bed',False)])
        rooms=workbook.create_sheet('Rooms');rooms.append(['ID','Property','Room number','Category','Floor','Reserved family'])
        for r in data['resources']:rooms.append([r['id'],r['hotel_id'],safe(r['number']),r['category'],r['floor'],r['reserved']])
        presence=workbook.create_sheet('Arrivals');presence.append(['Guest ID','Status']+(['Arrived at','Departed at'] if user.role!='family' else []))
        for row in data['presence']:presence.append([row['guest_id'],row['status']]+([row['arrived_at'],row['departed_at']] if user.role!='family' else []))
        functions=event_data(db,user);events=workbook.create_sheet('Functions');events.append(['ID','Function','Date','Side','Time (Asia/Kolkata)','Venue','Source'])
        for event in functions['events']:events.append([event['id'],safe(event['name']),event['day'],event['side'],event['start_time'],safe(event['venue']),safe(event['source_url'])])
        attended=workbook.create_sheet('Function attendance');attended.append(['Function ID','Guest ID','Planned','Actual'])
        for row in functions['rows']:attended.append([row[k] for k in ['event_id','guest_id','planned','actual']])
        meals=workbook.create_sheet('Meals');meals.append(['Guest ID','Date','Meal','Location','Planned','Actual']+(['Inclusion'] if editor else []))
        for row in meal_rows(db,{g['id'] for g in data['guests']}):meals.append([row[k] for k in ['guest_id','day','meal','location','planned','actual']]+([row['inclusion']] if editor else []))
        if editor:
            bill=billing_data(db);cost=workbook.create_sheet('Estimate');cost.append(['Day','Item','Quantity','Rate paise','Amount paise','Status'])
            for line in bill['lines']:cost.append([line.get('day'),line['kind'],line['quantity'],line['rate_paise'],line['amount_paise'],line['status']])
            cost.append(['','Known subtotal','','',bill['known_subtotal_paise'],'Estimate; unpriced items listed below'])
            for item in bill['unpriced']:cost.append([item.get('day'),safe(item['reason']),item.get('quantity'),None,None,'UNPRICED'])
    instructions=workbook.create_sheet('Read me');instructions.append(['Instructions'])
    for text in ['One row is one guest slot. Completing a name does not add a second person.','Preserve Guest ID and Family ID on re-import. Blank IDs create new records, with duplicate warnings.','New groups require Group and Side (bride or groom). Ages may be blank. Supply Age band adult/child for provisional assignment, or unknown to leave unresolved.','Arrival is 2026-11-24, 2026-11-25 or blank for a non-resident. Category: guest, driver, staff, vendor.','Family room type: superior, premium or blank. The choice requires that Wyndham room type; couples with children use Superior.','Built-in tags: ground_floor, second_hotel, near_restaurant. Additional tags use short text.','Use the owner import preview before applying. Import does not delete records or assign rooms.','Private notes and costs are omitted from viewer exports. Formula-like user text is exported as text.']:
        instructions.append([text])
    for s in workbook:decorate(s)
    output=io.BytesIO();workbook.save(output)
    return Response(output.getvalue(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="wedding-guests-template.xlsx"' if template else 'attachment; filename="wedding-plan.xlsx"'})


def boolean(value):
    if value is None or value=='':return False
    if isinstance(value,bool):return value
    if str(value).strip().lower() in {'true','yes','1'}:return True
    if str(value).strip().lower() in {'false','no','0'}:return False
    raise ValueError('Use true/false or yes/no for family flags')


def parse_import(content,current):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            files=archive.infolist()
            if len(files)>2000 or sum(f.file_size for f in files)>20*1024*1024 or any('vbaproject' in f.filename.lower() or 'externallinks/' in f.filename.lower() for f in files):raise ValueError('Workbook content is too large or contains unsupported macros/external links')
        workbook=load_workbook(io.BytesIO(content),read_only=True,data_only=False,keep_links=False)
        if 'Guests' not in workbook.sheetnames:raise ValueError('Use the Guests sheet from the downloaded template')
        sheet=workbook['Guests']
        # Worksheet dimensions are optional and may also be stale or misleading.
        # Stream actual cells with bounds, rather than trusting cached dimensions.
        sheet.reset_dimensions();cells=[]
        for cell_row in sheet.iter_rows():
            if len(cells)>=1001 or len(cell_row)>20:raise ValueError('Import supports up to 1,000 rows and the template columns')
            cells.append(cell_row)
        if not cells:raise ValueError('The Guests sheet is empty')
        headers=[str(c.value or '').strip() for c in cells[0]]
        if len(headers)!=len(set(headers)) or not set(['Group','Side','Name','Age','Category','Arrival']).issubset(headers) or any(h not in HEADERS for h in headers):raise ValueError('The Guests sheet headers do not match the template')
    except (ValueError,KeyError,zipfile.BadZipFile) as error:raise HTTPException(400,str(error))
    except Exception:raise HTTPException(400,'The file is not a readable supported .xlsx workbook')
    known_guests={g['id']:g for g in current['guests']};known_families={f['id']:f for f in current['families']}
    new_groups={};families={};guests={};errors=[];warnings=[]
    names={g['name'].strip().casefold() for g in current['guests'] if g['name']}
    for row_index,cells in enumerate(cells[1:],2):
        if all(c.value in [None,''] for c in cells):continue
        try:
            if any(c.data_type=='f' for c in cells):raise ValueError('Formulas are not allowed in import cells')
            row=dict(zip(headers,[c.value[1:] if isinstance(c.value,str) and c.value.startswith(("'=","'+","'-","'@")) else c.value for c in cells]))
            gid=str(uuid.UUID(str(row['Guest ID']).strip())) if row.get('Guest ID') else str(uuid.uuid4())
            if gid in guests:raise ValueError('Duplicate Guest ID in workbook')
            old=known_guests.get(gid)
            label=str(row.get('Group') or '').strip();side=str(row.get('Side') or '').strip().lower()
            if not label or len(label)>100 or side not in {'bride','groom'}:raise ValueError('Enter Group and bride/groom Side')
            if row.get('Family ID'):fid=str(uuid.UUID(str(row['Family ID']).strip()))
            elif old:fid=old['family_id']
            else:fid=new_groups.setdefault((label.casefold(),side),str(uuid.uuid4()))
            if old and old['family_id']!=fid:raise ValueError('Guest ID belongs to a different family')
            room_type=(str(row.get('Family room type') or '').strip().lower() or None) if 'Family room type' in headers else known_families.get(fid,{}).get('required_room_type')
            if room_type not in {None,'superior','premium'}:raise ValueError('Family room type must be Superior, Premium or blank')
            family={'id':fid,'label':label,'side':side,'reserved_eligible':boolean(row.get('Reserved eligible')),'couple_children':boolean(row.get('Couple with children')),'required_room_type':room_type}
            if family['couple_children'] and room_type=='premium':raise ValueError('Couples with children require Superior rooms')
            if fid in families and families[fid]!=family:raise ValueError('Repeated family rows have inconsistent details')
            families[fid]=family
            arrival=row.get('Arrival')
            if isinstance(arrival,(date,datetime)):arrival=arrival.date().isoformat() if isinstance(arrival,datetime) else arrival.isoformat()
            arrival=str(arrival).strip() if arrival not in [None,''] else None
            age=row.get('Age')
            if age not in [None,''] and (isinstance(age,bool) or float(age)!=int(float(age))):raise ValueError('Age must be a whole number')
            name=row.get('Name')
            # Undo only the formula-protection prefix produced by our exporter.
            if isinstance(name,str) and name.startswith(("'=","'+","'-","'@")):name=name[1:]
            tags=[t.strip() for t in str(row.get('Tags') or '').split(',') if t.strip()]
            category=str(row.get('Category') or 'guest').strip().lower()
            friend_hint=category=='friends' or bool(set(tags)&{'friends','role_friend'})
            sharing_mode=str(row.get('Sharing mode') or ('friends' if friend_hint else (old or {}).get('sharing_mode','family'))).strip().lower()
            value=GuestInput(name=name,gender=str(row.get('Gender') or (old or {}).get('gender','unspecified')).strip().lower(),sharing_mode=sharing_mode,age_band=str(row.get('Age band') or (old or {}).get('age_band','unknown')).strip().lower(),age=None if age in [None,''] else int(float(age)),category='guest' if category=='friends' else category,phone=str(row['Phone']) if row.get('Phone') is not None else None,arrival=arrival,tags=tags,notes=str(row.get('Private notes') or ''))
            if room_type and value.category!='guest':raise ValueError('Room types apply only to hotel guests')
            guest={**value.model_dump(mode='json',exclude={'id'}),'id':gid,'family_id':fid,'side':side,'reserved_eligible':family['reserved_eligible'],'couple_children':family['couple_children'],'required_room_type':room_type}
            if guest['name'] and guest['name'].casefold() in names and not old:warnings.append(issue('import_duplicate_name_'+str(row_index),'A new row has a name already present. Review duplicates before adding another slot.',severity='warning',guests=[gid]))
            if guest['name']:names.add(guest['name'].casefold())
            guests[gid]=guest
        except (ValueError,TypeError,ValidationError):errors.append({'row':row_index,'message':'Check IDs, consistent family details, integer age, category, date and text lengths. Formula cells are rejected.'})
    workbook.close()
    merged=copy.deepcopy(current);merged['families']=list({**known_families,**families}.values());merged['guests']=list({**known_guests,**guests}.values())
    fmap={f['id']:f for f in merged['families']}
    for g in merged['guests']:
        f=fmap[g['family_id']]
        for key in ['side','reserved_eligible','couple_children','required_room_type']:g[key]=f[key]
    if len(merged['guests'])>1000:errors.append({'row':None,'message':'The event supports at most 1,000 guest slots.'})
    checked=validate(merged,current['assignments']);errors.extend({'row':None,'message':i['message']} for i in checked['errors'])
    old_warnings={w['id'] for w in validate(current,current['assignments'])['warnings']}
    warnings.extend(w for w in checked['warnings'] if w['id'] not in old_warnings)
    return {'families':list(families.values()),'guests':list(guests.values())},errors,warnings


@router.post('/import/preview',dependencies=WRITE)
async def import_preview(file:UploadFile,revision:int,user:Editor,db:DB):
    if not file.filename or not file.filename.lower().endswith('.xlsx'):raise HTTPException(400,'Upload an .xlsx guest template')
    content=await file.read(5*1024*1024+1);await file.close()
    if len(content)>5*1024*1024:raise HTTPException(413,'Workbook exceeds the 5 MiB limit')
    locked_state(db,revision);payload,errors,warnings=parse_import(content,snapshot(db))
    result={'revision':revision,'errors':errors,'warnings':warnings,'token':None,'families':len(payload['families']),'guests':len(payload['guests'])}
    if errors or not payload['guests']:return result
    pending=PendingChange(owner_id=user.id,revision=revision,kind='import',payload=payload,warnings=warnings,expires_at=now()+timedelta(minutes=10))
    db.add(pending);db.commit();result['token']=str(pending.id)
    return result


@router.post('/import/apply',dependencies=WRITE)
def apply_import(body:ApplyInput,user:Editor,db:DB):
    state=locked_state(db,body.revision);pending=db.get(PendingChange,body.token)
    if not pending or pending.kind!='import' or pending.owner_id!=user.id or pending.expires_at<=now() or pending.revision!=state.revision:raise HTTPException(409,'Import preview expired or changed; upload and preview again')
    if set(body.acknowledged)!={w['id'] for w in pending.warnings}:raise HTTPException(409,'Review and acknowledge the exact import warnings')
    before=snapshot(db)
    for f in pending.payload['families']:
        row=db.get(Family,uuid.UUID(f['id']))
        if not row:row=Family(id=uuid.UUID(f['id']));db.add(row)
        for k in ['label','side','reserved_eligible','couple_children','required_room_type']:setattr(row,k,f[k])
    db.flush()
    for g in pending.payload['guests']:
        row=db.get(Guest,uuid.UUID(g['id']))
        if not row:row=Guest(id=uuid.UUID(g['id']),family_id=uuid.UUID(g['family_id']));db.add(row)
        for k in ['name','age','age_band','gender','sharing_mode','category','phone','tags','notes']:setattr(row,k,g[k])
        row.arrival=date.fromisoformat(g['arrival']) if g['arrival'] else None
    db.flush();after=snapshot(db);checked=hard_check(after,after['assignments'])
    old={w['id'] for w in validate(before,before['assignments'])['warnings']}
    if not {w['id'] for w in checked['warnings'] if w['id'] not in old}.issubset(set(body.acknowledged)):raise HTTPException(409,'Import conditions changed; preview again')
    count=len(pending.payload['guests']);db.delete(pending)
    return record(db,user,state,'import.applied',{'rows':count,'warning_ids':body.acknowledged})
