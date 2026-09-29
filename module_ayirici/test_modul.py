import sys, unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import bpy

class SegmentationTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
    def box(self,name,lo,hi):
        bpy.ops.mesh.primitive_cube_add(size=1, location=[(a+b)/2000 for a,b in zip(lo,hi)])
        o=bpy.context.object;o.name=name;o.dimensions=[(b-a)/1000 for a,b in zip(lo,hi)]
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        return o
    def shell(self,x=0,z=0,p='a'):
        return [self.box(p+'left',(x,0,z),(x+18,300,z+600)),self.box(p+'right',(x+582,0,z),(x+600,300,z+600)),self.box(p+'bottom',(x+18,0,z),(x+582,300,z+18)),self.box(p+'top',(x+18,0,z+582),(x+582,300,z+600))]
    def runseg(self,objects):
        import module_segmenter
        return module_segmenter.segment(objects)
    def test_engine_exists(self):
        self.assertTrue((Path(__file__).parent/'module_segmenter.py').exists(),'Modül ayırıcı henüz yok')
    def test_single_shell(self):
        r=self.runseg(self.shell());self.assertEqual(len(r['modules']),1);self.assertEqual(len(r['unresolved']),0)
    def test_touching_shells_not_joined_by_thin_back(self):
        parts=self.shell()+self.shell(600,p='b')
        parts.append(self.box('shared_back',(0,300,0),(1200,305,600)))
        r=self.runseg(parts);self.assertEqual(len(r['modules']),2);self.assertIn('shared_back',r['unresolved'])
    def test_stacked_shells(self):
        r=self.runseg(self.shell()+self.shell(z=600,p='b'));self.assertEqual(len(r['modules']),2)
    def test_nested_drawer_not_new_module(self):
        parts=self.shell();parts += [self.box('drawer_left',(40,20,50),(58,250,200)),self.box('drawer_right',(540,20,50),(558,250,200)),self.box('drawer_bottom',(58,20,50),(540,250,68))]
        r=self.runseg(parts);self.assertEqual(len(r['modules']),1);self.assertEqual(len(r['unresolved']),0)
    def test_near_but_not_touching(self):
        a=self.box('a',(0,0,0),(18,300,600));b=self.box('b',(18.2,0,0),(600,300,18))
        r=self.runseg([a,b]);self.assertEqual(len(r['contacts']),0)
    def test_input_order_invariance(self):
        parts=self.shell()+self.shell(600,p='b');a=self.runseg(parts);b=self.runseg(list(reversed(parts)))
        self.assertEqual(sorted(sorted(m['parts']) for m in a['modules']),sorted(sorted(m['parts']) for m in b['modules']))

    def test_open_doors_use_outer_hinge_side(self):
        parts=self.shell()+self.shell(600,p='b')
        parts += [self.box('left_module_right_door',(598,-297,2),(616,0,598)),self.box('right_module_left_door',(584,-297,2),(602,0,598))]
        r=self.runseg(parts)
        self.assertIn('left_module_right_door',r['assignment'])
        self.assertIn('right_module_left_door',r['assignment'])
        self.assertEqual(r['assignment']['left_module_right_door']['module'],r['assignment']['aright']['module'])
        self.assertEqual(r['assignment']['right_module_left_door']['module'],r['assignment']['bleft']['module'])
    def test_handle_follows_open_door(self):
        parts=self.shell();parts += [self.box('door',(-16,-297,2),(2,0,598)),self.box('handle',(-34,-250,200),(1,-240,402))]
        r=self.runseg(parts);self.assertEqual(len(r['unresolved']),0)
    def test_bbox_contact_in_hole_is_not_real_contact(self):
        bars=[self.box('bar1',(0,0,0),(18,50,600)),self.box('bar2',(0,250,0),(18,300,600)),self.box('bar3',(0,50,0),(18,250,50)),self.box('bar4',(0,50,550),(18,250,600))]
        bpy.ops.object.select_all(action='DESELECT')
        for o in bars:o.select_set(True)
        bpy.context.view_layer.objects.active=bars[0];bpy.ops.object.join();frame=bpy.context.object
        other=self.box('other',(18,100,200),(600,200,218))
        r=self.runseg([frame,other]);self.assertEqual(r['contacts'],[])

    def test_translation_and_renaming_preserve_membership(self):
        from mathutils import Vector
        parts=self.shell()+self.shell(600,p='b');a=self.runseg(parts)
        original={o.name:o for o in parts}
        for i,o in enumerate(parts):o.name='random_%03d'%(100-i);o.location+=Vector((12,-7,3))
        bpy.context.view_layer.update();b=self.runseg(list(reversed(parts)))
        before={frozenset(original[n].name for n in m['parts']) for m in a['modules']}
        self.assertEqual(before,{frozenset(m['parts']) for m in b['modules']})
    def test_triangle_intersection_area(self):
        from module_segmenter import triangle_overlap
        self.assertAlmostEqual(triangle_overlap([(0,0),(2,0),(0,2)],[(0,0),(2,0),(0,2)]),2)
        self.assertEqual(triangle_overlap([(0,0),(1,0),(0,1)],[(2,2),(3,2),(2,3)]),0)
    def test_seam_handle_follows_the_leaf_it_is_seated_in(self):
        """Dikişteki kulp 17 mm oturduğu kanada gider, 3 mm sıyırdığına değil.

        v0.1 bunu belirsiz bırakıyordu: donanım turu max(...,0) ile kelepçelenmiş
        boşluk ölçüyor, iç içe geçme derinliğini görmüyordu."""
        parts=self.shell()+self.shell(600,p='b')
        parts += [self.box('door_a',(598,-297,2),(616,0,598)),self.box('door_b',(584,-297,2),(602,0,598)),self.box('handle',(566,-250,200),(601,-240,402))]
        r=self.runseg(parts)
        self.assertIn('handle',r['assignment'])
        self.assertEqual(r['assignment']['handle']['module'],r['assignment']['door_b']['module'])
        self.assertEqual(r['assignment']['handle']['reason'],'deepest_panel_seat')
        self.assertAlmostEqual(r['assignment']['handle']['seat_depth_mm'],17.0,places=1)
        self.assertAlmostEqual(r['assignment']['handle']['runner_up_mm'],3.0,places=1)

    def test_symmetric_handle_stays_ambiguous(self):
        """İki kanada eşit oturan kulp belirsiz kalır; keyfi tarafa atılmaz."""
        parts=self.shell()+self.shell(600,p='b')
        parts += [self.box('door_a',(598,-297,2),(616,0,598)),self.box('door_b',(584,-297,2),(602,0,598)),
                  self.box('handle',(589,-250,200),(611,-240,402))]
        r=self.runseg(parts)
        self.assertIn('handle',r['unresolved'])
        self.assertEqual(r['unresolved']['handle']['reason'],'ambiguous_panel_attachment')

    def test_rotated_open_door_gets_the_carcass_it_hangs_on(self):
        """Plan düzleminde 45 derece döndürülmüş kapak, AABB'de 18 mm boyut taşımaz.

        Kalınlık kendi normali boyunca ölçülür; üyelik menteşe ucunun oturduğu
        gövde panelinden gelir (9453 L modülü)."""
        import math
        from mathutils import Vector
        parts=self.shell()
        # 600 mm kanat, sol yan panelin ön köşesinde menteşeli, 45 derece açık:
        # plan uçları (9,0) ve (-415,-424); merkez (-203,-212).
        door=self.box('rot_door',(-9,-300,2),(9,300,598))
        door.rotation_euler=(0,0,math.radians(-45))
        door.location=Vector((-0.203,-0.212,0.300))
        bpy.context.view_layer.update()
        parts.append(door)
        r=self.runseg(parts)
        self.assertIn('rot_door',r['assignment'])
        self.assertEqual(r['assignment']['rot_door']['module'],r['assignment']['aleft']['module'])
        self.assertEqual(r['assignment']['rot_door']['reason'],'rotated_open_door_plan_hinge')

    def test_segment_preserves_world_geometry(self):
        parts=self.shell();before={o.name:[tuple(o.matrix_world@v.co) for v in o.data.vertices] for o in parts}
        self.runseg(parts)
        self.assertEqual(before,{o.name:[tuple(o.matrix_world@v.co) for v in o.data.vertices] for o in parts})
    def test_contact_markers_parented_and_rerun_idempotent(self):
        from run_batch import display
        parts=self.shell()+self.shell(600,p='b');r=self.runseg(parts)
        c=display(r,parts);first=[tuple(o.matrix_world.translation) for o in c.objects]
        c=display(r,parts);self.assertEqual(len(c.objects),1)
        self.assertTrue(all(o.parent in parts for o in c.objects))
        self.assertEqual(first,[tuple(o.matrix_world.translation) for o in c.objects])

    # --- v0.2 regresyonları: panel çapalı menteşe ve ikiz gövde raporu -----
    def test_door_hinged_on_inner_divider(self):
        """Menteşe iç bölmede olduğunda kapak modül bbox'ının dışında değildir."""
        parts=self.shell()
        parts.append(self.box('divider',(291,0,18),(309,300,582)))
        # sol gözün sağ kapağı: menteşe iç bölmenin sol yüzünde, 90 derece açık
        parts.append(self.box('inner_door',(273,-297,2),(291,0,598)))
        r=self.runseg(parts)
        self.assertIn('inner_door',r['assignment'])
        self.assertEqual(r['assignment']['inner_door']['module'],r['assignment']['aleft']['module'])
        self.assertEqual(r['assignment']['inner_door']['reason'],'open_door_outer_hinge_corner')

    def test_protruding_worktop_does_not_break_door_test(self):
        """Öne taşan bir tezgah modül bbox'ını bozar; panel çapası bundan etkilenmez."""
        parts=self.shell()
        parts.append(self.box('worktop',(0,-19,600),(600,300,618)))
        parts.append(self.box('door',(-16,-297,2),(2,0,598)))
        r=self.runseg(parts)
        self.assertIn('door',r['assignment'])
        self.assertEqual(r['assignment']['door']['module'],r['assignment']['aleft']['module'])

    def test_overlay_door_two_mm_proud_of_carcass(self):
        """Bindirmeli kapak gövde ön yüzünün 2 mm önünde durur; tolerans bunu kapsar."""
        parts=self.shell()
        parts.append(self.box('door',(-16,-297,2),(2,-2,598)))
        r=self.runseg(parts)
        self.assertIn('door',r['assignment'])

    def test_twin_carcasses_reported_not_merged(self):
        """Yan yana iki AYNI gövde ikiz adayı olarak raporlanır ama birleştirilmez."""
        parts=self.shell()+self.shell(600,p='b')
        r=self.runseg(parts)
        self.assertEqual(len(r['modules']),2)
        self.assertEqual(len(r['twin_candidates']),1)
        self.assertEqual(sorted(r['twin_candidates'][0]['modules']),
                         sorted(m['id'] for m in r['modules']))

    def test_different_side_by_side_shells_are_not_twins(self):
        """İç düzeni farklı yan yana gövdeler ikiz sayılmaz."""
        parts=self.shell()+self.shell(600,p='b')
        parts.append(self.box('bshelf',(618,0,300),(1182,300,318)))
        r=self.runseg(parts)
        self.assertEqual(len(r['modules']),2)
        self.assertEqual(r['twin_candidates'],[])

    def test_stacked_identical_shells_are_not_twins(self):
        """İkiz kuralı yalnız yan yana (eksen 0) için geçerlidir."""
        parts=self.shell()+self.shell(z=600,p='b')
        r=self.runseg(parts)
        self.assertEqual(r['twin_candidates'],[])

    def test_contested_leaf_is_flagged_not_moved(self):
        """Ortak duvara menteşeli kanat atanır ama 'çekişmeli' işaretlenir."""
        parts=self.shell()+self.shell(600,p='b')
        parts += [self.box('left_module_right_door',(598,-297,2),(616,0,598)),
                  self.box('right_module_left_door',(584,-297,2),(602,0,598))]
        r=self.runseg(parts)
        a=r['assignment']['left_module_right_door']
        self.assertEqual(a['module'],r['assignment']['aright']['module'])
        self.assertIn('hinge_on_shell_boundary',a)
        self.assertEqual(a['hinge_on_shell_boundary'],[r['assignment']['bleft']['module']])

    def test_leaf_width_evidence_adds_up(self):
        """İki kanat 600 mm gövdeyi kapatıyorsa genişlik toplamı gövdeyle örtüşür."""
        parts=self.shell()
        parts += [self.box('door_l',(-16,-297,2),(2,0,598)),self.box('door_r',(598,-297,2),(616,0,598))]
        r=self.runseg(parts)
        rows=r['leaf_width_evidence'][r['assignment']['door_l']['module']]
        self.assertEqual(len(rows),1)
        self.assertEqual(len(rows[0]['leaves']),2)
        self.assertAlmostEqual(rows[0]['leaf_width_sum_mm'],594.0,places=1)
        self.assertAlmostEqual(rows[0]['module_width_mm'],600.0,places=1)
        self.assertGreater(rows[0]['ratio'],0.98)

    def test_leaf_width_evidence_splits_tiers(self):
        """Alt ve üst kapak bankları ayrı kat sayılır; toplam 2.0 raporlanmaz."""
        parts=self.shell()
        parts += [self.box('low_l',(-16,-297,2),(2,0,296)),self.box('low_r',(598,-297,2),(616,0,296)),
                  self.box('up_l',(-16,-297,304),(2,0,598)),self.box('up_r',(598,-297,304),(616,0,598))]
        r=self.runseg(parts)
        rows=r['leaf_width_evidence'][r['assignment']['low_l']['module']]
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertEqual(len(row['leaves']),2)
            self.assertGreater(row['ratio'],0.98)
            self.assertLess(row['ratio'],1.02)

suite=unittest.defaultTestLoader.loadTestsFromTestCase(SegmentationTests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
import os
sys.stdout.flush();sys.stderr.flush();os._exit(0 if result.wasSuccessful() else 1)
