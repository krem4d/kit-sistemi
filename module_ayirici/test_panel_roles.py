"""Pure-Python tests for panel_roles (no Blender needed): python3 test_panel_roles.py"""
import sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import panel_roles as pr


def box(name, lo, hi, axis=None, thick=None, planar=None):
    dims = [b - a for a, b in zip(lo, hi)]
    if axis is None:
        axis = min(range(3), key=lambda k: dims[k])
    if thick is None:
        thick = planar is None and abs(dims[axis] - 18) < .15
    return dict(name=name, lo=list(lo), hi=list(hi), dims=dims, axis=axis, thick=thick, planar=planar)


def hole(family, centre, mouth=None):
    return dict(family=family, volume_mm3=0.0, centre_world_mm=list(centre), mouth_world=mouth)


def carcass(x=0, w=600, d=300, h=600, prefix='', z=0):
    """Two side walls (pim holes, mouths inward), bottom, top, base strip; hole lists."""
    parts = {}; holes = {}
    L = box(prefix + 'left', (x, 0, z), (x + 18, d, z + h)); R = box(prefix + 'right', (x + w - 18, 0, z), (x + w, d, z + h))
    parts[L['name']] = L; parts[R['name']] = R
    holes[L['name']] = [hole('pim', (x + 18, 50 + 100 * i, z + 30), (1, 0, 0)) for i in range(3)] + [hole('rafpimi', (x + 18, 60, z + 300), (1, 0, 0))]
    holes[R['name']] = [hole('pim', (x + w - 18, 50 + 100 * i, z + 30), (-1, 0, 0)) for i in range(3)]
    B = box(prefix + 'bottom', (x + 18, 0, z + 60), (x + w - 18, d, z + 78)); T = box(prefix + 'top', (x + 18, 0, z + h - 18), (x + w - 18, d, z + h))
    parts[B['name']] = B; parts[T['name']] = T
    holes[B['name']] = [hole('linco', (x + 40, 50, z + 69), (0, 0, -1)) for _ in range(4)] + [hole('tipa', (x + 60, 40, z + 60))]
    holes[T['name']] = [hole('linco', (x + 40, 50, z + h - 9), (0, 0, -1)) for _ in range(4)]
    S = box(prefix + 'base', (x + 18, 0, z), (x + w - 18, 18, z + 60)); parts[S['name']] = S; holes[S['name']] = [hole('linco', (x + 40, 9, z + 30), (0, 1, 0))]
    return parts, holes


def module(parts, mid='M01', core=None):
    """Module dict like segment(): the box comes from the CORE parts only (doors and
    handles are members but never enlarge the box), matching module_segmenter."""
    names = list(parts)
    core = core or [n for n in names if not n.startswith(('door', 'handle'))]
    lo = [min(parts[n]['lo'][k] for n in core) for k in range(3)]; hi = [max(parts[n]['hi'][k] for n in core) for k in range(3)]
    return dict(id=mid, parts=names, core_parts=core, lo=lo, hi=hi)


def result(*mods):
    assignment = {n: dict(module=m['id'], reason='test') for m in mods for n in m['parts']}
    return dict(modules=list(mods), assignment=assignment)


def door_holes(x, mouth, z0=2, h=596, cups=2):
    zs = [z0 + 98, z0 + h - 98] if cups == 2 else [z0 + 98, z0 + h / 2, z0 + h - 98]
    return [hole('menteseTabani', (x, -22, z), mouth) for z in zs] + [hole('modulbaglanti', (x, -250, z0 + 198)), hole('modulbaglanti', (x, -250, z0 + 390))]


class RoleTests(unittest.TestCase):
    def test_side_walls_by_hole_signature_not_by_extreme(self):
        parts, holes = carcass()
        door = box('door', (-16, -297, 2), (2, 0, 598)); parts['door'] = door   # swung past the left wall
        holes['door'] = door_holes(-7, (1, 0, 0))
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(roles['left'], 'sol_yan_duvar'); self.assertEqual(roles['right'], 'sag_yan_duvar')
        self.assertEqual(roles['door'], 'kapak_acik'); self.assertEqual(s['sol_yan_duvar'], 'left')

    def test_wall_rule_each_condition_alone_disqualifies(self):
        """One violated condition at a time; every mutation must lose the right wall."""
        base_parts, base_holes = carcass()
        def run(mutate):
            parts = {k: dict(v) for k, v in base_parts.items()}; holes = {k: list(v) for k, v in base_holes.items()}
            mutate(parts, holes)
            return pr.classify_module(module(parts), parts, holes)[1]['sag_yan_duvar']
        self.assertEqual(run(lambda p, h: None), 'right')
        self.assertIsNone(run(lambda p, h: h.__setitem__('right', [hole('pim', (582, 50, 30), (-1, 0, 0))])), 'one dowel hole is not a wall')
        self.assertIsNone(run(lambda p, h: h['right'].extend([hole('linco', (582, 50, 100 + i), (-1, 0, 0)) for i in range(4)])), '4 cam holes is not a wall')
        self.assertIsNone(run(lambda p, h: h['right'].extend([hole('menteseTabani', (582, 30, 100)), hole('menteseTabani', (582, 30, 500))])), 'hinge cups make a door')
        self.assertIsNone(run(lambda p, h: h['right'].append(hole('pim', (582, 50, 400), (0, 0, 1)))), 'mouths in two directions')
        def short(p, h):
            p['right'] = box('right', (582, 0, 0), (600, 300, 170)); p['right']['dims'] = [18, 300, 170]
        self.assertIsNone(run(short), 'shorter than the wall minimum')

    def test_three_cam_holes_still_a_wall_but_four_not(self):
        parts, holes = carcass()
        holes['right'] += [hole('linco', (582, 50, 100 + i), (-1, 0, 0)) for i in range(3)]
        self.assertEqual(pr.classify_module(module(parts), parts, holes)[1]['sag_yan_duvar'], 'right')

    def test_stacked_boxes_keep_every_tier_wall(self):
        """A coffee-style module: two boxes on top of each other, four side walls."""
        pa, ha = carcass(h=800, prefix='a'); pb, hb = carcass(h=800, z=800, prefix='b')
        parts = {**pa, **pb}; holes = {**ha, **hb}
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(sorted(s['sol_yan_duvarlar']), ['aleft', 'bleft']); self.assertEqual(sorted(s['sag_yan_duvarlar']), ['aright', 'bright'])
        self.assertEqual(s['dikey_bolme'], 0)
        self.assertEqual(s['taban_sayisi'], 1); self.assertEqual(roles['bbottom'], 'ara_bolme'); self.assertEqual(roles['btop'], 'tavan')

    def test_three_tier_column_walls_pass_the_height_rule(self):
        parts = {}; holes = {}
        for i in range(3):
            p, h = carcass(h=800, z=800 * i, prefix=f't{i}'); parts.update(p); holes.update(h)
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(len(s['sol_yan_duvarlar']), 3); self.assertEqual(len(s['sag_yan_duvarlar']), 3)

    def test_bottom_top_fixed_and_movable_shelves(self):
        parts, holes = carcass()
        fixed = box('mid', (18, 0, 300), (582, 300, 318)); parts['mid'] = fixed; holes['mid'] = [hole('linco', (40, 50, 309), (0, 0, -1))] * 4
        loose = box('shelf', (18, 10, 450), (582, 300, 468)); parts['shelf'] = loose; holes['shelf'] = []
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(roles['bottom'], 'taban_ayarli_ayakli'); self.assertEqual(roles['top'], 'tavan')
        self.assertEqual(roles['mid'], 'ara_bolme'); self.assertEqual(roles['shelf'], 'hareketli_raf'); self.assertEqual(roles['base'], 'baza')
        self.assertEqual(s['tur_tahmini'], 'askılıksız ara bölmeli kapaksız raf modülü')

    def test_l_module_second_bottom_and_side_base_strip(self):
        parts, holes = carcass()
        lw = box('lwall', (400, -500, 0), (800, -482, 600)); parts['lwall'] = lw
        holes['lwall'] = [hole('pim', (500 + 50 * i, -482, 30), (0, 1, 0)) for i in range(3)]
        wb = box('wingbottom', (600, -482, 60), (782, 0, 78)); parts['wingbottom'] = wb; holes['wingbottom'] = [hole('linco', (700, -200, 69), (0, 0, -1))] * 4
        sb = box('sidebase', (600, -482, 0), (618, 0, 60)); parts['sidebase'] = sb; holes['sidebase'] = [hole('linco', (609, -200, 30), (1, 0, 0))] * 2
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(roles['lwall'], 'L_yan_duvar'); self.assertEqual(s['tur_tahmini'], 'L modülü')
        self.assertEqual(roles['wingbottom'], 'taban'); self.assertEqual(s['taban_sayisi'], 2)
        self.assertEqual(roles['sidebase'], 'baza'); self.assertEqual(s['cekmece'], 0)

    def test_washing_machine_carcass(self):
        parts, holes = carcass(h=1700)
        del parts['bottom']; del holes['bottom']; del parts['base']; del holes['base']
        for i, z in enumerate((0, 700, 1500)):
            b = box(f'brace{i}', (18, 0, z), (582, 18, z + 150)); parts[b['name']] = b; holes[b['name']] = [hole('linco', (40, 9, z + 75), (0, 1, 0))] * 4
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertTrue(s['alt_acik']); self.assertEqual(s['tur_tahmini'], 'çamaşır makinesi modülü')
        self.assertEqual({roles['brace0'], roles['brace1'], roles['brace2']}, {'takviye_alt', 'takviye_ara', 'takviye_ust'})

    def test_tall_base_strip_does_not_make_a_washing_machine(self):
        parts, holes = carcass()
        parts['base'] = box('base', (18, 0, 0), (582, 18, 150)); holes['base'] = [hole('linco', (40, 9, 75), (0, 1, 0))] * 4
        parts['brace'] = box('brace', (18, 282, 450), (582, 300, 550)); holes['brace'] = [hole('linco', (40, 291, 500), (0, -1, 0))] * 4
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertFalse(s['alt_acik']); self.assertNotIn('çamaşır', s['tur_tahmini'])

    def test_drawer_sides_and_handle_hardware(self):
        parts, holes = carcass()
        for i, x in enumerate((40, 542)):
            d = box(f'dside{i}', (x, 20, 100), (x + 18, 280, 268)); parts[d['name']] = d; holes[d['name']] = [hole('pim', (x, 50, 150)), hole('linco', (x, 100, 150))]
        k = box('handle', (200, -30, 300), (402, -20, 335)); parts['handle'] = k
        rod = box('rod', (18, 150, 500), (582, 175, 525)); parts['rod'] = rod
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(s['cekmece'], 1); self.assertEqual(roles['handle'], 'kulp'); self.assertEqual(roles['rod'], 'askilik_borusu')
        self.assertIn('çekmeceli', s['tur_tahmini']); self.assertTrue(s['tur_tahmini'].startswith('askılıklı'))

    def test_closed_door_rotated_door_and_drawer_front(self):
        parts, holes = carcass()
        cd = box('door_closed', (18, -20, 62), (300, -2, 598)); parts['door_closed'] = cd
        holes['door_closed'] = [hole('menteseTabani', (40, -11, 160), (0, 1, 0)), hole('menteseTabani', (40, -11, 500), (0, 1, 0))]
        rd = box('door_rot', (300, -320, 62), (620, 0, 598), axis=2, thick=False, planar=dict(thickness=18.0, normal=[0.707, -0.707, 0]))
        parts['door_rot'] = rd; holes['door_rot'] = [hole('menteseTabani', (598, -22, 160), (-0.707, 0.707, 0)), hole('menteseTabani', (598, -22, 500), (-0.707, 0.707, 0))]
        df = box('front', (18, -20, 100), (582, -2, 300)); parts['front'] = df
        holes['front'] = [hole('modulbaglanti', (204, -11, 200)), hole('modulbaglanti', (396, -11, 200))]
        odd = box('filler', (300, -320, 62), (620, 0, 598), axis=2, thick=False, planar=dict(thickness=18.0, normal=[0.707, -0.707, 0])); parts['filler'] = odd; holes['filler'] = []
        roles, s = pr.classify_module(module(parts), parts, holes)
        self.assertEqual(roles['door_closed'], 'kapak_kapali'); self.assertEqual(roles['door_rot'], 'kapak_dondurulmus')
        self.assertEqual(roles['front'], 'cekmece_onu'); self.assertEqual(roles['filler'], 'panel_egik')
        self.assertEqual(s['kapak_kapali'], 1); self.assertEqual(s['kapak_dondurulmus'], 1); self.assertEqual(s['hareketli_raf'], 0)

    def test_scan_error_part_is_quarantined(self):
        parts, holes = carcass()
        holes['bottom'] = []
        roles, s = pr.classify_module(module(parts), parts, holes, statuses={'bottom': 'scan_error'})
        self.assertEqual(roles['bottom'], 'taranamadi'); self.assertFalse(s['guvenilir']); self.assertEqual(s['taranamayan'], 1)
        self.assertNotIn('çamaşır', s['tur_tahmini'])


class OwnershipTests(unittest.TestCase):
    def two_carcasses_with_seam_doors(self):
        pa, ha = carcass(prefix='a'); pb, hb = carcass(x=600, prefix='b')
        parts = {**pa, **pb}; holes = {**ha, **hb}
        # a's right leaf swung open past the seam (hung on aright), b's left leaf likewise (bleft);
        # cups open towards the carcass the leaf belongs to (-x for a's leaf, +x for b's)
        parts['door_a'] = box('door_a', (598, -297, 2), (616, 0, 598)); holes['door_a'] = door_holes(607, (-1, 0, 0))
        parts['door_b'] = box('door_b', (584, -297, 2), (602, 0, 598)); holes['door_b'] = door_holes(593, (1, 0, 0))
        holes['aright'] += [hole('agacvidasi', (582, 37, z)) for z in (100, 500)]
        holes['bleft'] += [hole('agacvidasi', (618, 37, z)) for z in (100, 500)]
        ma = module({n: parts[n] for n in list(pa) + ['door_a']}, 'M01'); mb = module({n: parts[n] for n in list(pb) + ['door_b']}, 'M02')
        return parts, holes, result(ma, mb)

    def test_seam_doors_hinge_on_their_own_wall(self):
        parts, holes, r = self.two_carcasses_with_seam_doors()
        a = pr.analyse(r, parts, holes)
        self.assertEqual(a['leaf_ownership']['door_a']['wall'], 'aright'); self.assertEqual(a['leaf_ownership']['door_a']['module'], 'M01')
        self.assertEqual(a['leaf_ownership']['door_b']['wall'], 'bleft'); self.assertEqual(a['leaf_ownership']['door_b']['module'], 'M02')
        self.assertTrue(a['leaf_ownership']['door_a']['mouth_used']); self.assertEqual(a['leaf_ownership']['door_a']['plate_screws_on_wall'], 2)
        self.assertEqual(a['conflicts_with_contact_assignment'], [])

    def test_seam_without_mouth_information_is_ambiguous(self):
        parts, holes, r = self.two_carcasses_with_seam_doors()
        for n in ('door_a', 'door_b'):
            for h in holes[n]: h['mouth_world'] = None
        a = pr.analyse(r, parts, holes)
        self.assertEqual(a['leaf_ownership']['door_a']['status'], 'ambiguous')

    def test_back_to_back_walls_inside_one_module_also_use_the_mouth(self):
        """Coffee module: two lower boxes in ONE module; the seam leaf must still go to its own box wall."""
        pa, ha = carcass(prefix='a'); pb, hb = carcass(x=600, prefix='b')
        parts = {**pa, **pb}; holes = {**ha, **hb}
        parts['door_a'] = box('door_a', (598, -297, 2), (616, 0, 598)); holes['door_a'] = door_holes(607, (-1, 0, 0))
        m = module(parts, 'M01'); a = pr.analyse(result(m), parts, holes)
        self.assertEqual(a['leaf_ownership']['door_a']['wall'], 'aright'); self.assertTrue(a['leaf_ownership']['door_a']['mouth_used'])

    def test_rotated_leaf_hinges_within_the_widened_reach(self):
        parts, holes = carcass()
        rd = box('door_rot', (-320, -320, 2), (18, 0, 598), axis=2, thick=False, planar=dict(thickness=18.0, normal=[0.707, -0.707, 0]))
        parts['door_rot'] = rd
        holes['door_rot'] = [hole('menteseTabani', (-5, -42, 160), (0.707, -0.707, 0)), hole('menteseTabani', (-5, -42, 500), (0.707, -0.707, 0))]  # 42.3 mm from the left wall footprint
        a = pr.analyse(result(module(parts)), parts, holes)
        v = a['leaf_ownership']['door_rot']; self.assertEqual(v['status'], 'hinged'); self.assertEqual(v['wall'], 'left'); self.assertAlmostEqual(v['distance_mm'], 42.3, places=1)
        holes['door_rot'] = [hole('menteseTabani', (-5, -61, 160)), hole('menteseTabani', (-5, -61, 500))]  # 61.2 mm: out of reach
        self.assertEqual(pr.analyse(result(module(parts)), parts, holes)['leaf_ownership']['door_rot']['status'], 'no_wall_within_reach')

    def test_handle_goes_to_the_leaf_whose_hole_pair_it_sits_on(self):
        parts, holes, r = self.two_carcasses_with_seam_doors()
        # corpus handle: 35 mm along the door normal, seated 17 mm into its own leaf,
        # so its centre is 9.5 mm from the hole-pair midpoint (593,-250,296)
        parts['handle'] = box('handle', (566, -255, 195), (601, -245, 397)); r['modules'][1]['parts'].append('handle')
        a = pr.analyse(r, parts, holes)
        v = a['handle_ownership']['handle']
        self.assertEqual(v['status'], 'seated'); self.assertEqual(v['leaf'], 'door_b'); self.assertEqual(v['module'], 'M02')
        self.assertAlmostEqual(v['distance_mm'], 9.5, places=1); self.assertAlmostEqual(v['runner_up_mm'], 23.5, places=1)

    def test_handle_seat_boundaries_match_the_calibration(self):
        parts, holes = carcass()
        parts['front'] = box('front', (18, -20, 100), (582, -2, 300)); holes['front'] = [hole('modulbaglanti', (204, -11, 200)), hole('modulbaglanti', (396, -11, 200))]
        for off, status in ((26.5, 'seated'), (31.0, 'no_handle_holes_within_reach')):
            parts['handle'] = box('handle', (199, -11 - off - 5, 182.5), (401, -11 - off + 5, 217.5))
            a = pr.analyse(result(module(parts)), parts, holes)
            self.assertEqual(a['handle_ownership']['handle']['status'], status, off)

    def test_handle_between_two_hole_pairs_is_ambiguous(self):
        parts, holes, r = self.two_carcasses_with_seam_doors()
        parts['handle'] = box('handle', (582.5, -255, 195), (617.5, -245, 397)); r['modules'][1]['parts'].append('handle')
        a = pr.analyse(r, parts, holes)
        self.assertEqual(a['handle_ownership']['handle']['status'], 'ambiguous')

    def test_conflict_with_contact_assignment_is_reported(self):
        parts, holes, r = self.two_carcasses_with_seam_doors()
        r['assignment']['door_a']['module'] = 'M02'   # pretend the contact stage gave it to the neighbour
        a = pr.analyse(r, parts, holes)
        self.assertEqual([c['part'] for c in a['conflicts_with_contact_assignment']], ['door_a'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
