"""Geometric module candidates for axis-aligned furniture meshes (Blender).

No order names, hole categories, or external membership config are used.
Contact area is triangle intersection, not bounding-box overlap. Semantic
module grouping (especially double shells, L and coffee) remains reviewable.
Input meshes and transforms are never modified by segment(). Units: mm.
"""
from itertools import combinations
from collections import defaultdict
from math import prod
from mathutils import Vector

TOL = 0.05
MIN_CONTACT_MM2 = 1.0
ATTACH_GAP = 30.0
# A 90-degree open door hinges on a PANEL face, not on the module bounding box.
# Overlay doors sit a few mm proud of the carcass front, so the flush test needs
# a real tolerance; 2.5 mm resolves every observed door with no ambiguity.
HINGE_FACE = 2.5
# A handle seated in its own door leaf overlaps it by ~17 mm; the neighbouring
# leaf is only grazed by ~3 mm. Both numbers repeat across the whole corpus.
SEAT_DEPTH = 8.0
SEAT_MARGIN = 5.0
# Plan distance from a rotated door's hinge end to the carcass panel it hangs on.
ROTATED_HINGE = 30.0


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
    free_area={}; free_normal={}
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
    # A panel rotated in plan (an L-module door swung to 45 degrees) has no 18 mm
    # bounding-box dimension. Measure its thickness along its own dominant normal
    # instead; this never feeds the contact graph, only the rotated-door rule.
    planar=None
    if not thick:
        best=None
        for vs,tk,aligned in triangles:
            n=(vs[1]-vs[0]).cross(vs[2]-vs[0]);ar=n.length/2
            if ar<1e-8: continue
            n.normalize();key=tuple(round(c,3) for c in n)
            if best is None or free_area.get(key,0)+ar>best[1]: pass
            free_area[key]=free_area.get(key,0)+ar;free_normal[key]=n
        if free_area:
            key=max(free_area,key=free_area.get);n=free_normal[key]
            if abs(n[2])<.02:
                proj=[p.dot(n) for p in points]
                span=max(proj)-min(proj)
                if abs(span-18)<.35:
                    u=n.cross(Vector((0,0,1)));u.normalize()
                    t=[p.dot(u) for p in points]
                    lo_t,hi_t=min(t),max(t)
                    ends=[]
                    for limit in (lo_t,hi_t):
                        sel=[p for p,tv in zip(points,t) if abs(tv-limit)<=1.0]
                        ends.append((sum(q[0] for q in sel)/len(sel),sum(q[1] for q in sel)/len(sel)))
                    planar=dict(thickness=span,normal=[n[0],n[1],n[2]],ends=ends,length=hi_t-lo_t)
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
    return dict(name=obj.name,lo=lo,hi=hi,dims=dims,axis=axis,thick=thick,planar=planar,surfaces=surfaces)


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


def plan_distance(point,panel):
    """Distance in the XY plane from a point to a panel's axis-aligned footprint."""
    d=[max(panel['lo'][k]-point[k],point[k]-panel['hi'][k],0.0) for k in range(2)]
    return (d[0]*d[0]+d[1]*d[1])**.5


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
    # A ninety-degree open door hinges on the outer face of one assigned vertical
    # panel: its thickness centre lies just outside that panel, its swung leaf
    # starts at that panel's front (or back) face, and it spans the panel in Z.
    # Anchoring on the panel rather than on the module bounding box is what makes
    # inner dividers and protruding worktops stop breaking the test.
    by_module={m['id']:m for m in modules}
    for p in parts:
        n=p['name'];k=p['axis']
        if n not in unresolved or not p['thick'] or k not in (0,1): continue
        d=1-k;centre=(p['lo'][k]+p['hi'][k])/2;owners=defaultdict(list)
        for panel in parts:
            pn=panel['name']
            if pn==n or pn not in assignment or not panel['thick'] or panel['axis']!=k: continue
            outside=max(panel['lo'][k]-centre,centre-panel['hi'][k])
            if not TOL<outside<=18: continue
            if not (abs(p['hi'][d]-panel['lo'][d])<=HINGE_FACE or abs(p['lo'][d]-panel['hi'][d])<=HINGE_FACE): continue
            if min(p['hi'][2],panel['hi'][2])-max(p['lo'][2],panel['lo'][2])<p['dims'][2]/2: continue
            owners[assignment[pn]['module']].append(pn)
        if len(owners)==1:
            mid=next(iter(owners))
            assignment[n]=dict(module=mid,reason='open_door_outer_hinge_corner',support_parts=owners[mid])
            by_module[mid]['parts'].append(n);del unresolved[n]
        elif owners:unresolved[n]=dict(reason='ambiguous_open_door',candidates=sorted(owners))
    # Hardware gets membership from a unique fitted panel. Bounding proximity
    # is attachment evidence only; it is not added to structural contacts.
    # A plan-rotated 18 mm panel still hinges on a carcass panel: one of its two
    # plan ends sits on that panel's footprint and it spans the panel in Z.
    for p in parts:
        n=p['name']
        if n not in unresolved or not p['planar']:continue
        owners=defaultdict(list)
        for panel in parts:
            pn=panel['name']
            if pn==n or pn not in assignment or not panel['thick'] or panel['axis'] not in (0,1):continue
            if min(p['hi'][2],panel['hi'][2])-max(p['lo'][2],panel['lo'][2])<p['dims'][2]/2:continue
            near=min(plan_distance(end,panel) for end in p['planar']['ends'])
            if near<=ROTATED_HINGE:owners[assignment[pn]['module']].append((round(near,2),pn))
        if len(owners)==1:
            mid=next(iter(owners))
            assignment[n]=dict(module=mid,reason='rotated_open_door_plan_hinge',support_parts=[q[1] for q in sorted(owners[mid])])
            next(m for m in modules if m['id']==mid)['parts'].append(n);del unresolved[n]
        elif owners:unresolved[n]=dict(reason='ambiguous_rotated_door',candidates=sorted(owners))
    panels=[p for p in parts if p['thick'] and p['name'] in assignment]
    for p in parts:
        n=p['name']
        if n not in unresolved or p['thick']:continue
        # Depth of interpenetration, not a clamped gap: a handle seated in its own
        # door overlaps it by ~17 mm while merely grazing the neighbouring leaf by
        # ~3 mm. max(...,0) collapsed both to zero and lost every seam handle.
        best={}
        for panel in panels:
            k=panel['axis'];other=[a for a in range(3) if a!=k]
            if not all(panel['lo'][a]-1<=p['lo'][a] and p['hi'][a]<=panel['hi'][a]+1 for a in other):continue
            if p['dims'][k]>2*18:continue
            depth=min(panel['hi'][k],p['hi'][k])-max(panel['lo'][k],p['lo'][k])
            if depth<-1:continue
            mid=assignment[panel['name']]['module']
            if mid not in best or depth>best[mid][0]:best[mid]=(depth,panel['name'])
        if len(best)==1:
            mid=next(iter(best));assignment[n]=dict(module=mid,reason='unique_panel_attachment',support_parts=[best[mid][1]],seat_depth_mm=round(best[mid][0],2))
            next(m for m in modules if m['id']==mid)['parts'].append(n);del unresolved[n]
        elif best:
            ranked=sorted(best.items(),key=lambda kv:-kv[1][0])
            if ranked[0][1][0]>=SEAT_DEPTH and ranked[0][1][0]-ranked[1][1][0]>=SEAT_MARGIN:
                mid=ranked[0][0]
                assignment[n]=dict(module=mid,reason='deepest_panel_seat',support_parts=[ranked[0][1][1]],
                                   seat_depth_mm=round(ranked[0][1][0],2),runner_up_mm=round(ranked[1][1][0],2))
                next(m for m in modules if m['id']==mid)['parts'].append(n);del unresolved[n]
            else:unresolved[n]=dict(reason='ambiguous_panel_attachment',candidates=sorted(best),
                                    depths_mm={k:round(v[0],2) for k,v in best.items()})
    boundaries=[]
    for c in contacts:
        if c['kind']!='broad-broad': continue
        a=assignment.get(c['a'],{}).get('module');b=assignment.get(c['b'],{}).get('module')
        if a and b and a!=b: boundaries.append(dict(**c,modules=[a,b],semantic_status='physical_shell_boundary_requires_review'))
    twins=twin_candidates(modules,by_name,boundaries)
    flag_boundary_hinges(assignment,boundaries)
    leaf_evidence=leaf_width_evidence(modules,assignment,by_name)
    return dict(version='0.4',scope='axis_aligned_physical_shell_candidates',parameters=dict(distance_mm=TOL,min_contact_mm2=MIN_CONTACT_MM2,panel_attachment_gap_mm=ATTACH_GAP,hinge_face_mm=HINGE_FACE,seat_depth_mm=SEAT_DEPTH,seat_margin_mm=SEAT_MARGIN,rotated_hinge_mm=ROTATED_HINGE),modules=modules,assignment=assignment,unresolved=unresolved,contacts=contacts,boundaries=boundaries,twin_candidates=twins,leaf_width_evidence=leaf_evidence,part_count=len(parts),warnings=['Physical shells are not guaranteed semantic order modules.','twin_candidates are side-by-side identical carcasses; whether they are ONE order module is a product-definition question, not a geometric one.','L arms, rotated panels and unsupported attachments require review.','Input duplicates should be removed by the existing preparation stage.'])


def flag_boundary_hinges(assignment,boundaries):
    """A leaf hinged on a panel that is itself a module boundary is contested.

    In the reference renders the neighbouring module is painted as the owner in
    every observed case (9441, 9462, 9467, 9484) while the leaf-width arithmetic
    supports this module. The assignment is left alone and the doubt is recorded.
    """
    partner={}
    for b in boundaries:
        for name,other in ((b['a'],b['modules'][1]),(b['b'],b['modules'][0])):
            partner.setdefault(name,set()).add(other)
    for name,a in assignment.items():
        if a['reason'] not in ('open_door_outer_hinge_corner','rotated_open_door_plan_hinge','unique_panel_attachment','deepest_panel_seat'): continue
        rival=set()
        for support in a.get('support_parts',()):
            rival|=partner.get(support,set())
        rival.discard(a['module'])
        if rival:
            a['hinge_on_shell_boundary']=sorted(rival)
            a['semantic_status']='contested_leaf_reference_renders_paint_the_neighbour'


def leaf_width_evidence(modules,assignment,by_name):
    """Sum of open-leaf widths against the module's outer width, per tier.

    Two leaves closing a 600 mm carcass measure 297 mm each. A module with an
    upper and a lower bank of doors has two tiers; summing them together would
    report a meaningless 2.0. Leaves are therefore grouped by Z overlap first.
    This is positive evidence for the contested leaves above, never a rule."""
    out={}
    for m in modules:
        leaves=[]
        for name in m['parts']:
            a=assignment.get(name);p=by_name.get(name)
            if not a or not p or a['reason']!='open_door_outer_hinge_corner' or p['axis'] not in (0,1): continue
            leaves.append(p)
        if not leaves: continue
        leaves.sort(key=lambda p:p['lo'][2])
        tiers=[]
        for p in leaves:
            for tier in tiers:
                if min(p['hi'][2],tier['hi'])-max(p['lo'][2],tier['lo'])>p['dims'][2]/2:
                    tier['parts'].append(p);tier['lo']=min(tier['lo'],p['lo'][2]);tier['hi']=max(tier['hi'],p['hi'][2]);break
            else: tiers.append(dict(lo=p['lo'][2],hi=p['hi'][2],parts=[p]))
        rows=[]
        for tier in tiers:
            k=tier['parts'][0]['axis']
            total=sum(q['dims'][1-q['axis']] for q in tier['parts'])
            width=m['hi'][k]-m['lo'][k]
            rows.append(dict(z_mm=[round(tier['lo'],1),round(tier['hi'],1)],
                             leaves=sorted(q['name'] for q in tier['parts']),
                             leaf_width_sum_mm=round(total,1),module_width_mm=round(width,1),
                             ratio=round(total/width,4) if width else None))
        out[m['id']]=rows
    return out


def layout_signature(module,by_name,names):
    """Part bounding boxes relative to the module origin; order independent."""
    lo=module['lo']
    return sorted(tuple(round(by_name[n][side][k]-lo[k],1) for side in ('lo','hi') for k in range(3))
                  for n in names if n in by_name)


def twin_candidates(modules,by_name,boundaries):
    """Side-by-side carcasses with identical outer size AND identical structural
    layout. In the reference set every such pair is drawn as ONE order module
    (9449-2, 9475) while every non-identical side-by-side pair is drawn as two
    (9440, 9441, 9462, 9467, 9484, 9488-1). The geometry alone cannot prove the
    product rule, so the pair is reported and never merged."""
    index={m['id']:m for m in modules}
    out=[]
    for b in boundaries:
        if b['axis']!=0: continue
        a,c=[index[i] for i in b['modules']]
        if [round(a['hi'][k]-a['lo'][k],1) for k in range(3)]!=[round(c['hi'][k]-c['lo'][k],1) for k in range(3)]: continue
        if layout_signature(a,by_name,a['core_parts'])!=layout_signature(c,by_name,c['core_parts']): continue
        out.append(dict(modules=b['modules'],axis=b['axis'],area_mm2=b['area_mm2'],
                        dims_mm=[round(a['hi'][k]-a['lo'][k],1) for k in range(3)],
                        evidence='identical outer size and identical structural layout',
                        semantic_status='one_order_module_in_reference_renders_requires_product_rule'))
    return out
