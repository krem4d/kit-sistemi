"""Panel roles, door/handle ownership and module-type guess from hole signatures.

Pure Python (no bpy): works on the part dicts produced by ``module_segmenter.measure``
plus a per-part hole list produced by ``hole_scan.scan`` (family, world centre, mouth
direction). Rules follow Kerem's description of a side wall (2026-09-14):

* a side wall is vertical, at the left/right of its module, its holes face each
  other (all mouths point into the module), it carries dowel (``pim``) holes and,
  apart from a few exceptions, no cam (``linco``) holes; it may carry shelf-pin,
  adjustable-foot and hanger-flange holes;
* an open door swings past the side wall, so "outermost vertical panel" is wrong;
  doors are the panels that carry hinge-cup holes (``menteseTabani``);
* a handle is recognised by its own volume, then matched to the leaf whose pair of
  handle holes (``modulbaglanti`` x2, 192 mm apart) it sits on.

A module may stack several boxes (coffee module, L module tiers): every panel that
stands on the module's left/right edge with the wall signature is a side wall, so
``sol_yan_duvarlar`` / ``sag_yan_duvarlar`` are lists. Parts whose hole scan failed
get the role ``taranamadi`` and never feed a rule (v0.5.1, after the 2026-09-14
adversarial review).

Units: mm. Axis convention of the corpus: x = width, y = depth (front is -y),
z = height.
"""
from collections import Counter

PANEL = 18.0
PANEL_TOL = 0.3
WALL_MIN_HEIGHT_RATIO = 0.3      # a side wall spans a good part of the module height ...
WALL_MIN_HEIGHT_MM = 400.0       # ... and is never a drawer side; stacked boxes make the
                                 # ratio small (three 800 mm boxes: 0.33)
WALL_MAX_LINCO = 3               # Kerem: "birkaç istisna haricinde linco deliği olmuyor";
                                 # the L module's x-normal right wall carries exactly 3
                                 # (7/7 L modules), every other wall 0-2 (198 walls)
WALL_EDGE_TOL = 1.0              # a wall stands on the module's x edge within this
L_WALL_MIN_HEIGHT_RATIO = 0.8    # the L module's back-parallel wall is full height
DRAWER_SIDE_MAX_HEIGHT = 250.0
DRAWER_FRONT_MAX_HEIGHT = 400.0
BASE_MAX_HEIGHT = 80.0           # baza strip (60 mm in the corpus)
BRACE_MAX_HEIGHT = 160.0         # takviye strip (washing-machine carcass: 92-150 mm)
FIXED_MIN_Z_FROM_BOTTOM = 120.0  # a taban sits within this of the module bottom
TOP_MAX_Z_FROM_TOP = 40.0        # a tavan reaches within this of the module top
OPEN_BOTTOM_MM = 300.0           # alt_acik: no horizontal panel in this bottom band
WORKTOP_PROTRUSION = 15.0        # tezgah protrudes past the wall front by more than this
HANDLE_DIMS = (10.0, 35.0, 202.0)  # sorted bbox of the corpus handle
HANDLE_DIM_TOL = (4.0, 8.0, 15.0)
ROD_MIN_LENGTH = 250.0
ROD_MAX_SECTION = 40.0
FLANGE_DIMS = (25.0, 50.0, 50.0)
HANDLE_PAIR_MM = 192.0           # kulp hole spacing (parca_sayim.KULP_DELIK_MESAFE)
HANDLE_PAIR_TOL = 12.0
# Calibrated on the 25 single-module reference orders (2026-09-14): a handle's
# centre sits 9.5 mm from the midpoint of its own hole pair (27/27 handles, spread
# 0.0) and 26.5 mm on an overlay drawer front (9488-1/-2); the nearest foreign pair
# is >= 613 mm away, or 23.5 mm for the parallel leaf across a twin seam. Hinge cups
# sit 21.9-22.9 mm from the plan footprint of the wall they hang on (43/43 doors)
# and 42.3 mm for the 45 degree L leaves (9453).
HANDLE_SEAT_MAX = 30.0
HANDLE_SEAT_MARGIN = 8.0
HINGE_EDGE_MAX = 60.0
HINGE_EDGE_MARGIN = 10.0
CUP_Z_TOL = 20.0                 # hinge-plate screw holes on the wall line up with the cups

WALL_ROLES = ('sol_yan_duvar', 'sag_yan_duvar', 'L_yan_duvar', 'dikey_bolme', 'dikey_bolme_asili')


def _axis(n):
    k = max(range(3), key=lambda i: abs(n[i]))
    return k, (1 if n[k] > 0 else -1)


def _fam(holes):
    return Counter(h.get('family') or 'unknown' for h in holes)


def _mouths(holes):
    c = Counter()
    for h in holes:
        m = h.get('mouth_world')
        if m:
            k, s = _axis(m)
            c[('+' if s > 0 else '-') + 'xyz'[k]] += 1
    return c


def _near(v, target, tol):
    return abs(v - target) <= tol


def _is_panel(p):
    return p['thick'] or bool(p['planar'] and abs(p['planar']['thickness'] - PANEL) <= PANEL_TOL)


def classify_hardware(p, volume_mm3=None):
    d = sorted(p['dims'])
    if all(_near(d[i], HANDLE_DIMS[i], HANDLE_DIM_TOL[i]) for i in range(3)):
        return 'kulp'
    if d[2] >= ROD_MIN_LENGTH and d[1] <= ROD_MAX_SECTION and d[0] <= ROD_MAX_SECTION:
        return 'askilik_borusu'
    if all(_near(d[i], FLANGE_DIMS[i], 3.0) for i in range(3)):
        return 'askilik_flansi'
    return 'donanim'


def _is_door(holes, height):
    cups = _fam(holes).get('menteseTabani', 0)
    return cups >= 2 or (cups == 1 and height > DRAWER_FRONT_MAX_HEIGHT)


def classify_module(module, parts, holes, volumes=None, statuses=None):
    """Assign a role to every part of one module. Returns (roles, summary)."""
    lo, hi = module['lo'], module['hi']
    W, D, H = (hi[k] - lo[k] for k in range(3))
    P = [parts[n] for n in module['parts'] if n in parts]
    roles = {}
    # 0. parts whose hole scan failed cannot feed any hole rule
    for p in P:
        if statuses and statuses.get(p['name']) == 'scan_error':
            roles[p['name']] = 'taranamadi'
    thick = [p for p in P if p['name'] not in roles and _is_panel(p)]
    flat = [p for p in thick if p['thick']]           # axis-aligned 18 mm boards
    # 1. doors: hinge cups (axis-aligned or rotated in plan)
    for p in thick:
        if _is_door(holes.get(p['name'], []), p['dims'][2]):
            if p['planar'] and not p['thick']:
                roles[p['name']] = 'kapak_dondurulmus'
            else:
                roles[p['name']] = 'kapak_acik' if p['axis'] == 0 else 'kapak_kapali'
    # 2. side walls: vertical, dowel holes, mouths all one way, tall, on the module edge
    # absolute floor for tall modules (stacked boxes), relative floor for short ones
    # (a 300 mm top module has 300 mm walls): never demand more than 60 % of H
    min_h = max(min(WALL_MIN_HEIGHT_MM, 0.6 * H), WALL_MIN_HEIGHT_RATIO * H)
    cands = []
    for p in flat:
        if p['name'] in roles or p['axis'] not in (0, 1):
            continue
        hs = holes.get(p['name'], []); f = _fam(hs); mo = _mouths(hs)
        if f.get('pim', 0) >= 2 and f.get('linco', 0) <= WALL_MAX_LINCO and f.get('menteseTabani', 0) == 0 \
                and len(mo) == 1 and p['dims'][2] >= min_h:
            cands.append((p, next(iter(mo))))
    xw = [(p, m) for p, m in cands if p['axis'] == 0]
    lefts = [p for p, m in xw if m == '+x']
    rights = [p for p, m in xw if m == '-x']
    left_edge = min((p['lo'][0] for p in lefts), default=None)
    right_edge = max((p['hi'][0] for p in rights), default=None)
    lefts = [p for p in lefts if left_edge is not None and abs(p['lo'][0] - left_edge) <= WALL_EDGE_TOL]
    rights = [p for p in rights if right_edge is not None and abs(p['hi'][0] - right_edge) <= WALL_EDGE_TOL]
    for p in lefts: roles[p['name']] = 'sol_yan_duvar'
    for p in rights: roles[p['name']] = 'sag_yan_duvar'
    # The L module's second wall is parallel to the back (y-normal), full height,
    # dowel-holed like any side wall. It exists whether or not an x-normal right
    # wall was also found (9453: the upper L tier has both).
    l_walls = [p for p, m in cands if p['axis'] == 1 and p['name'] not in roles and p['dims'][2] >= L_WALL_MIN_HEIGHT_RATIO * H]
    for p in l_walls: roles[p['name']] = 'L_yan_duvar'
    l_wall = l_walls[0] if l_walls else None
    walls = lefts + rights
    front_y = min([w['lo'][1] for w in walls] or [lo[1]])
    # 3. remaining x-normal panels: side base strip, drawer sides, dividers
    for p in flat:
        if p['name'] in roles or p['axis'] != 0:
            continue
        f = _fam(holes.get(p['name'], [])); h = p['dims'][2]; zrel = p['lo'][2] - lo[2]
        if h <= BASE_MAX_HEIGHT and zrel < 5:
            roles[p['name']] = 'baza'
        elif h <= DRAWER_SIDE_MAX_HEIGHT and (f.get('pim', 0) or f.get('linco', 0) or f.get('ray', 0)):
            roles[p['name']] = 'cekmece_yani'
        elif h <= DRAWER_SIDE_MAX_HEIGHT:
            roles[p['name']] = 'kisa_dikey_panel'
        else:
            roles[p['name']] = 'dikey_bolme_asili' if p['lo'][2] > lo[2] + 150 else 'dikey_bolme'
    # 4. horizontal panels (axis-aligned only; a rotated panel is never a shelf)
    zp = sorted([p for p in flat if p['name'] not in roles and p['axis'] == 2], key=lambda p: p['lo'][2])
    def fixed(p):
        f = _fam(holes.get(p['name'], [])); return bool(f.get('linco', 0) or f.get('tipa', 0))
    inner_w = W - 2 * PANEL
    lowest_fixed_z = min((p['lo'][2] for p in zp if fixed(p)), default=None)
    for p in zp:
        f = _fam(holes.get(p['name'], [])); hs = holes.get(p['name'], [])
        partial = '_kismi' if p['dims'][0] < 0.8 * inner_w else ''
        is_bottom = fixed(p) and p['lo'][2] < lo[2] + FIXED_MIN_Z_FROM_BOTTOM
        is_top = fixed(p) and p['hi'][2] > hi[2] - TOP_MAX_Z_FROM_TOP
        protrude = (p['lo'][1] < front_y - WORKTOP_PROTRUSION and p['dims'][0] >= 0.9 * W and not l_wall
                    and fixed(p) and not is_bottom and lowest_fixed_z is not None and p['lo'][2] > lowest_fixed_z)
        if protrude:
            roles[p['name']] = 'tezgah'
        elif is_bottom:
            roles[p['name']] = 'taban' + ('_ayarli_ayakli' if f.get('tipa', 0) else '')
        elif is_top:
            roles[p['name']] = 'tavan'
        elif fixed(p):
            roles[p['name']] = 'ara_bolme' + partial
        elif not hs or all((h.get('family') or 'unknown') == 'unknown' for h in hs):
            roles[p['name']] = 'hareketli_raf' + partial
        else:
            roles[p['name']] = 'yatay_panel'
    # 5. y-normal panels: base strip, brace, drawer front/back
    for p in flat:
        if p['name'] in roles or p['axis'] != 1:
            continue
        f = _fam(holes.get(p['name'], [])); h = p['dims'][2]; zrel = p['lo'][2] - lo[2]
        if h <= BASE_MAX_HEIGHT and zrel < 5:
            roles[p['name']] = 'baza'
        elif h <= DRAWER_FRONT_MAX_HEIGHT and f.get('modulbaglanti', 0) >= 2:
            roles[p['name']] = 'cekmece_onu'
        elif h <= DRAWER_SIDE_MAX_HEIGHT and (f.get('linco', 0) or f.get('pim', 0)) and zrel > 5 and p['dims'][0] < 0.97 * inner_w:
            roles[p['name']] = 'cekmece_on_arka'
        elif h <= BRACE_MAX_HEIGHT:
            roles[p['name']] = 'takviye_' + ('alt' if zrel < 5 else ('ust' if p['hi'][2] > hi[2] - 200 else 'ara'))
        else:
            roles[p['name']] = 'y_panel'
    # 6. rotated non-door panels, thin panels, hardware, the rest
    for p in P:
        if p['name'] in roles:
            continue
        if p['planar'] and not p['thick']:
            roles[p['name']] = 'panel_egik'
        elif p['axis'] is not None and min(p['dims']) <= 8.15 and p['dims'][p['axis']] <= 8.15:
            roles[p['name']] = 'arkalik' if abs(p['dims'][p['axis']] - 5) < 0.5 else 'ince_panel'
        elif not _is_panel(p):
            roles[p['name']] = classify_hardware(p, (volumes or {}).get(p['name']))
        elif _fam(holes.get(p['name'], [])).get('ray', 0):
            roles[p['name']] = 'cekmece_yani'
        else:
            roles[p['name']] = 'panel'
    rc = Counter(roles.values())
    bottom_band_panels = [p for p in zp if p['lo'][2] < lo[2] + OPEN_BOTTOM_MM]
    summary = dict(
        genislik=round(W), derinlik=round(D), yukseklik=round(H), yerden=round(lo[2]),
        sol_yan_duvar=lefts[0]['name'] if lefts else None, sag_yan_duvar=rights[0]['name'] if rights else None,
        sol_yan_duvarlar=[p['name'] for p in lefts], sag_yan_duvarlar=[p['name'] for p in rights],
        L_yan_duvar=l_wall['name'] if l_wall else None, L_yan_duvarlar=[p['name'] for p in l_walls],
        taban=any(v.startswith('taban') for v in roles.values()), taban_sayisi=sum(1 for v in roles.values() if v.startswith('taban')),
        ayarli_ayak=any('ayarli' in v for v in roles.values()),
        tavan=rc.get('tavan', 0) > 0, tavan_sayisi=rc.get('tavan', 0),
        ara_bolme=rc.get('ara_bolme', 0) + rc.get('ara_bolme_kismi', 0),
        hareketli_raf=rc.get('hareketli_raf', 0) + rc.get('hareketli_raf_kismi', 0),
        dikey_bolme=rc.get('dikey_bolme', 0) + rc.get('dikey_bolme_asili', 0), dikey_bolme_asili=rc.get('dikey_bolme_asili', 0),
        baza=rc.get('baza', 0), arkalik=rc.get('arkalik', 0),
        kapak_acik=rc.get('kapak_acik', 0), kapak_kapali=rc.get('kapak_kapali', 0), kapak_dondurulmus=rc.get('kapak_dondurulmus', 0),
        kulp=rc.get('kulp', 0), askilik_borusu=rc.get('askilik_borusu', 0), askilik_flansi=rc.get('askilik_flansi', 0),
        cekmece=rc.get('cekmece_yani', 0) // 2, cekmece_onu=rc.get('cekmece_onu', 0), tezgah=rc.get('tezgah', 0),
        takviye=rc.get('takviye_alt', 0) + rc.get('takviye_ara', 0) + rc.get('takviye_ust', 0),
        kismi_raf=rc.get('ara_bolme_kismi', 0) + rc.get('hareketli_raf_kismi', 0),
        egik_panel=rc.get('panel_egik', 0), taranamayan=rc.get('taranamadi', 0),
    )
    # open bottom (washing-machine carcass): no bottom board, braces instead, and
    # nothing horizontal in the bottom band. A tall base strip alone is not enough.
    summary['alt_acik'] = (not summary['taban']) and summary['takviye'] >= 2 and not bottom_band_panels
    summary['guvenilir'] = summary['taranamayan'] == 0
    summary['tur_tahmini'] = guess_type(summary)
    return roles, summary


def guess_type(s):
    """Kerem-style type name from the role summary. A proposal, not a verdict."""
    doors = s['kapak_acik'] + s['kapak_kapali'] + s['kapak_dondurulmus']
    if s['L_yan_duvar']:
        return 'L modülü' + (' (kapaklı)' if doors else '')
    if s['alt_acik']:
        return 'çamaşır makinesi modülü' + (' (çekmeceli)' if s['cekmece'] else '')
    if s['tezgah']:
        return 'kahve modülü'
    if s['dikey_bolme_asili'] and s['kismi_raf']:
        return 'ütü modülü'
    words = ['askılıklı' if s['askilik_borusu'] or s['askilik_flansi'] else 'askılıksız',
             'ara bölmeli' if s['ara_bolme'] else 'ara bölmesiz']
    if s['cekmece']: words.append('çekmeceli')
    if s['dikey_bolme']: words.append('dikey bölmeli')
    words.append(f'{doors} kapaklı' if doors else 'kapaksız')
    return ' '.join(words) + ' raf modülü' + (' — üst modül' if s['yerden'] > 100 else '')


def handle_pairs(holes):
    """Midpoints of modulbaglanti hole pairs that are HANDLE_PAIR_MM apart."""
    pts = [h['centre_world_mm'] for h in holes if h.get('family') == 'modulbaglanti']
    out = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = sum((pts[i][k] - pts[j][k]) ** 2 for k in range(3)) ** .5
            if abs(d - HANDLE_PAIR_MM) <= HANDLE_PAIR_TOL:
                out.append([(pts[i][k] + pts[j][k]) / 2 for k in range(3)])
    return out


def resolve_handles(parts, holes, roles_by_name, assignment):
    """Handle -> leaf whose handle-hole pair it sits on. Returns {handle: verdict}."""
    out = {}
    leaves = {n: handle_pairs(hs) for n, hs in holes.items() if handle_pairs(hs)}
    for n, role in roles_by_name.items():
        if role != 'kulp':
            continue
        p = parts[n]; c = [(p['lo'][k] + p['hi'][k]) / 2 for k in range(3)]
        ranked = sorted((sum((c[k] - mid[k]) ** 2 for k in range(3)) ** .5, leaf) for leaf, pairs in leaves.items() for mid in pairs)
        if not ranked or ranked[0][0] > HANDLE_SEAT_MAX:
            out[n] = dict(status='no_handle_holes_within_reach', nearest_mm=round(ranked[0][0], 1) if ranked else None)
            continue
        d0, leaf = ranked[0]
        rival = next((r for r in ranked[1:] if r[1] != leaf), None)
        if rival and rival[0] - d0 < HANDLE_SEAT_MARGIN:
            out[n] = dict(status='ambiguous', candidates=sorted({leaf, rival[1]}), distances_mm=[round(d0, 1), round(rival[0], 1)])
        else:
            out[n] = dict(status='seated', leaf=leaf, module=assignment.get(leaf, {}).get('module'), distance_mm=round(d0, 1),
                          runner_up_mm=round(rival[0], 1) if rival else None)
    return out


def _plan_distance(point, panel):
    """Distance in the XY plane from a point to a panel's axis-aligned footprint."""
    d = [max(panel['lo'][k] - point[k], point[k] - panel['hi'][k], 0.0) for k in range(2)]
    return (d[0] * d[0] + d[1] * d[1]) ** .5


def _plate_screws(wall_holes, cups):
    """Wood-screw holes on the wall at the cups' heights: the hinge base plates."""
    return sum(1 for h in wall_holes if (h.get('family') or '').startswith('agacvidasi')
               and any(abs(h['centre_world_mm'][2] - c[2]) <= CUP_Z_TOL for c in cups))


def resolve_leaves(parts, holes, roles_by_name, assignment):
    """Door -> wall (or divider) its hinge cups sit against.

    Two back-to-back walls (at a module seam, or two boxes inside one module) are
    equidistant from a leaf hung on either of them, so the cups' mouth direction
    decides: a cup opens towards the carcass it belongs to. The tie is broken per
    WALL, whatever module the rivals belong to."""
    walls = [n for n, r in roles_by_name.items() if r in WALL_ROLES]
    out = {}
    for n, role in roles_by_name.items():
        if not role.startswith('kapak'):
            continue
        cup_holes = [h for h in holes.get(n, []) if h.get('family') == 'menteseTabani']
        cups = [h['centre_world_mm'] for h in cup_holes]
        if not cups:
            out[n] = dict(status='no_hinge_cups'); continue
        p = parts[n]
        mouths = [h['mouth_world'] for h in cup_holes if h.get('mouth_world')]
        mouth = [sum(m[k] for m in mouths) / len(mouths) for k in range(3)] if mouths else None
        centre = [(p['lo'][k] + p['hi'][k]) / 2 for k in range(3)]
        def on_mouth_side(w):
            wp = parts[w]; wc = [(wp['lo'][k] + wp['hi'][k]) / 2 for k in range(3)]
            return sum((wc[k] - centre[k]) * mouth[k] for k in range(2)) > 0
        ranked = []
        for w in walls:
            wp = parts[w]
            if min(p['hi'][2], wp['hi'][2]) - max(p['lo'][2], wp['lo'][2]) < p['dims'][2] / 2:
                continue
            ranked.append((sum(_plan_distance(c, wp) for c in cups) / len(cups), w))
        ranked.sort()
        if not ranked or ranked[0][0] > HINGE_EDGE_MAX:
            out[n] = dict(status='no_wall_within_reach', nearest_mm=round(ranked[0][0], 1) if ranked else None); continue
        d0, w = ranked[0]
        rival = ranked[1] if len(ranked) > 1 else None
        mouth_used = False
        if rival and rival[0] - d0 < HINGE_EDGE_MARGIN:
            sides = [c for c in (w, rival[1]) if mouth and on_mouth_side(c)]
            if len(sides) == 1:
                w = sides[0]; d0 = next(d for d, c in ranked if c == w); mouth_used = True
            else:
                out[n] = dict(status='ambiguous', candidates=[w, rival[1]], distances_mm=[round(d0, 1), round(rival[0], 1)]); continue
        out[n] = dict(status='hinged', wall=w, module=assignment.get(w, {}).get('module'), distance_mm=round(d0, 1),
                      runner_up_mm=round(rival[0], 1) if rival else None, cups=len(cups),
                      plate_screws_on_wall=_plate_screws(holes.get(w, []), cups), mouth_used=mouth_used)
    return out


def analyse(result, parts, holes, volumes=None, statuses=None):
    """Roles for every module of a segmenter result plus door/handle ownership."""
    roles = {}; summaries = {}
    for m in result['modules']:
        r, s = classify_module(m, parts, holes, volumes, statuses)
        roles.update(r); summaries[m['id']] = s
    leaves = resolve_leaves(parts, holes, roles, result['assignment'])
    handles = resolve_handles(parts, holes, roles, result['assignment'])
    conflicts = []
    for n, v in list(leaves.items()) + list(handles.items()):
        if v.get('module') and result['assignment'].get(n, {}).get('module') not in (None, v['module']):
            conflicts.append(dict(part=n, contact_module=result['assignment'][n]['module'], hole_module=v['module'], evidence=v))
    return dict(roles=roles, module_summary=summaries, leaf_ownership=leaves, handle_ownership=handles,
                conflicts_with_contact_assignment=conflicts,
                unscanned_parts=sorted(n for n, r in roles.items() if r == 'taranamadi'))
