"""Sütun/braket kuralının saf Python sentetik düzen testleri (Blender gerekmez).

Çalıştırma:  python3 tests/test_sutunlar.py

Düzen uzayı assembly-module-link ile aynı: bir dizide 1..4 sütun, her sütunda
1..3 modül, sütun yükseklikleri bağımsız → 3+9+27+81 = 120 düzen. Her düzende
beklenen braket = 2 × sütun sayısı (Kerem, 2026-09-29). Modül genişlikleri,
derinlikleri ve yükseklikleri sütundan sütuna değişir; üst modüller alttakinden
sığ olabilir (asma dolap). Beklenen değer düzenin TANIMINDAN gelir, algoritmadan
değil.
"""
import itertools
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "module_ayirici"))
import sutunlar  # noqa: E402

GENISLIKLER = [450.0, 600.0, 1000.0, 700.0]      # sütun başına genişlik (mm)
YUKSEKLIKLER = [1800.0, 400.0, 720.0]            # sıra başına modül yüksekliği (alttan)


def duzen(yukseklikler, derinlik_ust=350.0):
    """yukseklikler = sütun başına modül sayısı (soldan). Modül kutuları döner."""
    moduller = []
    x = 0.0
    for c, h in enumerate(yukseklikler):
        w = GENISLIKLER[c % len(GENISLIKLER)]
        z = 0.0
        for r in range(h):
            yh = YUKSEKLIKLER[(r + c) % len(YUKSEKLIKLER)]
            derinlik = 580.0 if r == 0 else derinlik_ust
            moduller.append({"id": f"C{c}R{r}", "lo": [x, 0.0, z], "hi": [x + w, derinlik, z + yh]})
            z += yh
        x += w
    return moduller


def braket(moduller):
    return sutunlar.duvar_braketi_sayisi(len(sutunlar.sutunlari_bul(moduller)))


class DuzenTestleri(unittest.TestCase):
    def test_kerem_ornekleri(self):
        self.assertEqual(braket(duzen([3, 3])), 4)          # L2-33
        self.assertEqual(braket(duzen([1, 1, 1, 1])), 8)    # L4-1111
        self.assertEqual(braket(duzen([1])), 2)             # tek modül

    def test_farkli_yukseklikte_yan_yana_sutunlar(self):
        # alçak dolap yüksek dolabın yanında: 3 sütun, farklı modül sayısı ve boy
        m = duzen([1, 3, 2])
        self.assertEqual(braket(m), 6)
        gruplar = sutunlar.sutunlari_bul(m)
        self.assertEqual([len(g) for g in gruplar], [1, 3, 2])
        # sütun içi sıralama alttan üste
        for g in gruplar:
            z = [m[i]["lo"][2] for i in g]
            self.assertEqual(z, sorted(z))

    def test_120_duzenin_hepsi(self):
        sayac = 0
        for n in range(1, 5):
            for hs in itertools.product(range(1, 4), repeat=n):
                m = duzen(list(hs))
                self.assertEqual(braket(m), 2 * n, hs)
                self.assertEqual(sorted(len(g) for g in sutunlar.sutunlari_bul(m)), sorted(hs), hs)
                sayac += 1
        self.assertEqual(sayac, 120)

    def test_giris_sirasi_onemsiz(self):
        m = duzen([2, 1, 3])
        self.assertEqual(braket(list(reversed(m))), braket(m))

    def test_ust_modul_dar_ve_kaydirilmis(self):
        # üst modül alttakinden dar ve 100 mm içeride: yine aynı sütun (oran 1.0)
        alt = {"lo": [0, 0, 0], "hi": [800, 580, 1800]}
        ust = {"lo": [100, 0, 1800], "hi": [600, 350, 2200]}
        self.assertEqual(braket([alt, ust]), 2)

    def test_yan_duvar_bindirmesi_ayri_sutun(self):
        # komşu sütunların kutuları birkaç mm bindirse de ayrı sütun kalır
        a = {"lo": [0, 0, 0], "hi": [600, 580, 1800]}
        b = {"lo": [597, 0, 0], "hi": [1197, 580, 1800]}
        self.assertEqual(braket([a, b]), 4)

    def test_kose_L_dizilim(self):
        # x kolundaki köşe modülü ile y kolundaki modül x'te örtüşür ama y'de
        # örtüşmez → ayrı sütun
        kose = {"lo": [0, 0, 0], "hi": [600, 580, 1800]}
        yan = {"lo": [0, 580, 0], "hi": [580, 1180, 1800]}
        self.assertEqual(braket([kose, yan]), 4)

    def test_bos(self):
        self.assertEqual(sutunlar.sutunlari_bul([]), [])
        self.assertEqual(braket([]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
