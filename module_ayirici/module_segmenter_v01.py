"""Geometric module candidates for axis-aligned furniture meshes (Blender).

No order names, hole categories, or external membership config are used.
Contact area is triangle intersection, not bounding-box overlap. Semantic
module grouping (especially double shells, L and coffee) remains reviewable.
Input meshes and transforms are never modified by segment(). Units: mm.
"""
from itertools import combinations
from collections import defaultdict
from math import prod

TOL = 0.05
MIN_CONTACT_MM2 = 1.0
ATTACH_GAP = 30.0


def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))*.5 if len(poly)>2 else 0.0


def triangle_overlap(subject,clip):
    """Convex clipping; inputs are nondegenerate counterclockwise triangles."""
    poly=list(subject)
    for a,b in zip(clip,clip[1:]+clip[:1]):
        if not poly: return 0.0
        output=[]
        prev=poly[-1]; dp=cross(a,b,prev)
        for cur in poly:
            dc=cross(a,b,cur)
            if (dc>=0)!=(dp>=0):
                t=dp/(dp-dc)
                output.append((prev[0]+t*(cur[0]-prev[0]),prev[1]+t*(cur[1]-prev[1])))
            if dc>=0: output.append(cur)
            prev,dp=cur,dc
        poly=output
    return area(poly)


def measure(obj):
    points=[obj.matrix_world@v.co*1000 for v in obj.data.vertices]
    if not points: return None
    lo=[min(p[k] for p in points) for k in range(3)]
    hi=[max(p[k] for p in points) for k in range(3)]
    dims=[hi[k]-lo[k] for k in range(3)]
    obj.data.calc_loop_triangles()
    triangles=[]; normal_area=defaultdict(float)
    for tri in obj.data.loop_triangles:
        vs=[points[i] for i in tri.vertices]
        n=(vs[1]-vs[0]).cross(vs[2]-vs[0]); ar=n.length/2
        if ar<1e-8: continue
        n.normalize(); k=max(range(3),key=lambda i:abs(n[i]))
        aligned=abs(n[k])>.99999
        if aligned: normal_area[k]+=ar
        triangles.append((vs,k,aligned))
    axis=max(normal_area,key=normal_area.get) if normal_area else None
    # Only supported axis-aligned nominal panels become structural nodes.
    thick=axis is not None and abs(dims[axis]-18)<.15
    surfaces={}
    for k in range(3):
        other=[i for i in range(3) if i!=k]
        for side,plane in ((0,lo[k]),(1,hi[k])):
            projected=[]
            for vs,tk,aligned in triangles:
                if not aligned or tk!=k or max(abs(v[k]-plane) for v in vs)>TOL: continue
                t=[(v[other[0]],v[other[1]]) for v in vs]
                if cross(*t)<0: t.reverse()
                projected.append((t,(min(v[0] for v in t),max(v[0] for v in t),min(v[1] for v in t),max(v[1] for v in t))))
            surfaces[k,side]=projected
    return dict(name=obj.name,lo=lo,hi=hi,dims=dims,axis=axis,thick=thick,surfaces=surfaces)


def contact(a,b):
    overlap=[min(a['hi'][k],b['hi'][k])-max(a['lo'][k],b['lo'][k]) for k in range(3)]
    if min(overlap)<-TOL: return None
    for axis in range(3):
        other=[k for k in range(3) if k!=axis]
        if min(overlap[k] for k in other)<=TOL: continue
        if abs(b['lo'][axis]-a['hi'][axis])<=TOL: lower,upper=a,b
        elif abs(a['lo'][axis]-b['hi'][axis])<=TOL: lower,upper=b,a
        else: continue
        actual=0.0
        for ta,ba in lower['surfaces'][axis,1]:
            for tb,bb in upper['surfaces'][axis,0]:
                if ba[1]<=bb[0] or bb[1]<=ba[0] or ba[3]<=bb[2] or bb[3]<=ba[2]: continue
                actual+=triangle_overlap(ta,tb)
        if actual<MIN_CONTACT_MM2: continue
        types=['broad' if p['axis']==axis else 'edge' for p in (a,b)]
        return dict(a=a['name'],b=b['name'],axis=axis,kind='-'.join(sorted(types)),
                    area_mm2=actual,coverage=[actual/prod(p['dims'][k] for k in other) for p in (a,b)],
                    plane_mm=(lower['hi'][axis]+upper['lo'][axis])/2,
                    lo_mm=[max(a['lo'][k],b['lo'][k]) for k in other],
                    hi_mm=[min(a['hi'][k],b['hi'][k]) for k in other])
    return None


def bounds(parts):
    return dict(lo=[min(p['lo'][k] for p in parts) for k in range(3)],hi=[max(p['hi'][k] for p in parts) for k in range(3)])


def contains(outer,inner,pad=TOL):
    return all(outer['lo'][k]-pad<=inner['lo'][k] and inner['hi'][k]<=outer['hi'][k]+pad for k in range(3))


def shell(parts):
    # Opposing vertical sides + at least one horizontal structural connection.
    # A missing bottom/top is allowed for washing-machine cabinets.
    if not any(p['axis']==2 for p in parts): return False
    for a,b in combinations(parts,2):
        k=a['axis']
        if k not in (0,1) or b['axis']!=k: continue
        if abs((a['lo'][k]+a['hi'][k]-b['lo'][k]-b['hi'][k])/2)<2*18: continue
        z_overlap=min(a['hi'][2],b['hi'][2])-max(a['lo'][2],b['lo'][2])
        if z_overlap>18: return True
    return False


def segment(objects):
    parts=[p for o in objects if o.type=='MESH' for p in [measure(o)] if p]
    by_name={p['name']:p for p in parts}
    thick=[p for p in parts if p['thick']]
    adjacency={p['name']:set() for p in thick};contacts=[]
    for a,b in combinations(thick,2):
        c=contact(a,b)
        if not c: continue
        contacts.append(c)
        if c['kind']=='broad-edge':
            adjacency[a['name']].add(b['name']);adjacency[b['name']].add(a['name'])
    unseen=set(adjacency);components=[]
    while unseen:
        first=min(unseen);unseen.remove(first);todo=[first];names=[]
        while todo:
            n=todo.pop();names.append(n)
            for m in sorted(adjacency[n]&unseen): unseen.remove(m);todo.append(m)
        ps=[by_name[n] for n in names]
        components.append(dict(parts=sorted(names),**bounds(ps),shell=shell(ps)))
    shells=[g for g in components if g['shell']]
    cores=[g for g in shells if not any(h is not g and contains(h,g) and prod(h['hi'][k]-h['lo'][k] for k in range(3))>prod(g['hi'][k]-g['lo'][k] for k in range(3))+1 for h in shells)]
    cores.sort(key=lambda g:tuple(round(v,3) for v in g['lo']))
    modules=[];assignment={}
    for i,g in enumerate(cores,1):
        mid=f'M{i:02d}';modules.append(dict(id=mid,core_parts=g['parts'][:],parts=g['parts'][:],lo=g['lo'],hi=g['hi']))
        for n in g['parts']: assignment[n]=dict(module=mid,reason='structural_edge_contact')
    # Nested structural subassemblies (drawers) cannot create extra top-level modules.
    for g in components:
        if any(n in assignment for n in g['parts']): continue
        candidates=[m for m in modules if contains(m,g,1.0)]
        if len(candidates)==1:
            m=candidates[0]
            for n in g['parts']: assignment[n]=dict(module=m['id'],reason='contained_subassembly');m['parts'].append(n)
    unresolved={}
    for p in parts:
        n=p['name']
        if n in assignment: continue
        candidates=[m for m in modules if contains(m,p,1.0)]
        reason='unique_containment'
        if not candidates and p['axis'] is not None and min(p['dims'])<=18.15:
            # A panel must fit the complete opening in both in-plane axes.
            # A shared back spanning two modules is deliberately unresolved.
            k=p['axis'];other=[a for a in range(3) if a!=k]
            candidates=[m for m in modules if all(m['lo'][a]-1<=p['lo'][a] and p['hi'][a]<=m['hi'][a]+1 for a in other) and max(m['lo'][k]-p['hi'][k],p['lo'][k]-m['hi'][k],0)<=ATTACH_GAP]
            reason='panel_fits_single_shell_projection'
        if len(candidates)==1:
            m=candidates[0];assignment[n]=dict(module=m['id'],reason=reason);m['parts'].append(n)
        else: unresolved[n]=dict(reason='multiple_candidates' if candidates else 'no_supported_geometric_attachment',candidates=[m['id'] for m in candidates])
    # Ninety-degree open doors end at a front/back corner. The centre must
    # lie OUTSIDE the appropriate side, distinguishing adjacent hinge leaves.
    for p in parts:
        n=p['name'];k=p['axis']
        if n not in unresolved or not p['thick'] or k not in (0,1): continue
        d=1-k;centre=(p['lo'][k]+p['hi'][k])/2;candidates=[]
        for m in modules:
            outside=max(m['lo'][k]-centre,centre-m['hi'][k])
            corner=(abs(p['hi'][d]-m['lo'][d])<=1 or abs(p['lo'][d]-m['hi'][d])<=1)
            height=m['lo'][2]-1<=p['lo'][2] and p['hi'][2]<=m['hi'][2]+1
            width=p['dims'][d]<=m['hi'][k]-m['lo'][k]+1
            if TOL<outside<=18 and corner and height and width:candidates.append(m)
        if len(candidates)==1:
            m=candidates[0];assignment[n]=dict(module=m['id'],reason='open_door_outer_hinge_corner');m['parts'].append(n);del unresolved[n]
        elif candidates:unresolved[n]=dict(reason='ambiguous_open_door',candidates=[m['id'] for m in candidates])
    # Hardware gets membership from a unique fitted panel. Bounding proximity
    # is attachment evidence only; it is not added to structural contacts.
    panels=[p for p in parts if p['thick'] and p['name'] in assignment]
    for p in parts:
        n=p['name']
        if n not in unresolved or p['thick']:continue
        owners=defaultdict(list)
        for panel in panels:
            k=panel['axis'];other=[a for a in range(3) if a!=k]
            fits=all(panel['lo'][a]-1<=p['lo'][a] and p['hi'][a]<=panel['hi'][a]+1 for a in other)
            gap=max(panel['lo'][k]-p['hi'][k],p['lo'][k]-panel['hi'][k],0)
            # Avoid linking large thin panels to any overlapping small panel.
            if fits and gap<=1 and p['dims'][k]<=2*18:
                owners[assignment[panel['name']]['module']].append(panel['name'])
        if len(owners)==1:
            mid=next(iter(owners));assignment[n]=dict(module=mid,reason='unique_panel_attachment',support_parts=owners[mid])
            next(m for m in modules if m['id']==mid)['parts'].append(n);del unresolved[n]
        elif owners:unresolved[n]=dict(reason='ambiguous_panel_attachment',candidates=sorted(owners))
    boundaries=[]
    for c in contacts:
        if c['kind']!='broad-broad': continue
        a=assignment.get(c['a'],{}).get('module');b=assignment.get(c['b'],{}).get('module')
        if a and b and a!=b: boundaries.append(dict(**c,modules=[a,b],semantic_status='physical_shell_boundary_requires_review'))
    return dict(version='0.1',scope='axis_aligned_physical_shell_candidates',parameters=dict(distance_mm=TOL,min_contact_mm2=MIN_CONTACT_MM2,panel_attachment_gap_mm=ATTACH_GAP),modules=modules,assignment=assignment,unresolved=unresolved,contacts=contacts,boundaries=boundaries,part_count=len(parts),warnings=['Physical shells are not guaranteed semantic order modules.','L, coffee, rotated/open panels and unsupported attachments require review.','Input duplicates should be removed by the existing preparation stage.'])
