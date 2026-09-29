"""Askılık borusu boyu kuralının saf Python testleri (Blender gerekmez).

Çalıştırma:  python3 tests/test_askilik.py

Kural (Kerem, 2026-09-29): aynı modülde X/Y boyunca birbirine bakan iki flanş =
1 boru; boy = iki panelin iç yüz orta noktaları arası Öklid mesafesi − 1 cm, tam
cm'ye yarım-yukarı yuvarlanır. Beklenen değerler düzenin TANIMINDAN elle hesaplanır.
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "module_ayirici"))
import askilik  # noqa: E402

T = 18.0


def pano(ad, lo, hi):
    return {"ad": ad, "lo": list(lo), "hi": list(hi)}


def flans(p, merkez, modul="M01"):
    return {"merkez": list(merkez), "pano": p["ad"], "modul": modul,
            "pano_lo": p["lo"], "pano_hi": p["hi"]}


# 700 mm genişliğinde gövde: sol duvar x 0–18, sağ duvar x 682–700 → iç boşluk 664.
SOL = pano("sol", (0, 0, 0), (T, 580, 1850))
SAG = pano("sag", (700 - T, 0, 0), (700, 580, 1850))


class YuvarlamaTestleri(unittest.TestCase):
    def test_yarim_yukari(self):
        self.assertEqual(askilik.yarim_yukari(64.5), 65)   # round(64.5) == 64 olurdu
        self.assertEqual(askilik.yarim_yukari(65.5), 66)
        self.assertEqual(askilik.yarim_yukari(65.49), 65)
        self.assertEqual(askilik.yarim_yukari(65.0), 65)
        self.assertEqual(round(64.5), 64)                   # banker yuvarlamasının kanıtı

    def test_bir_cm_kesinti_ve_yuvarlama(self):
        self.assertEqual(askilik.ASKILIK_KESINTI_MM, 10.0)
        self.assertEqual(askilik.boru_boyu_cm(664.0), 65)   # 654 mm → 65.4 → 65
        self.assertEqual(askilik.boru_boyu_cm(665.0), 66)   # 655 mm → 65.5 → 66 (yarım yukarı)
        self.assertEqual(askilik.boru_boyu_cm(675.0), 67)   # 665 → 66.5 → 67 (round() 66 derdi)
        self.assertEqual(askilik.boru_boyu_cm(664.9), 65)   # 654.9 → 65.49 → 65
        self.assertEqual(askilik.boru_boyu_cm(970.0), 96)   # 960 → 96.0
        self.assertEqual(askilik.boru_boyu_cm(10.0), 0)


class EslestirmeTestleri(unittest.TestCase):
    def test_tek_boru_x(self):
        b, e = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5)),
                                 flans(SAG, (683.5, 297.5, 1779.5))])
        self.assertEqual(e, [])
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["uzunluk_cm"], 65)
        self.assertEqual(b[0]["ham_mm"], 664.0)
        self.assertEqual(b[0]["eksen_boslugu_mm"], 664.0)
        self.assertEqual((b[0]["eksen"], b[0]["modul"]), ("x", "M01"))

    def test_giris_sirasi_onemsiz(self):
        f = [flans(SAG, (683.5, 297.5, 1779.5)), flans(SOL, (16.5, 297.5, 1779.5))]
        self.assertEqual(askilik.eslestir(f)[0][0]["uzunluk_cm"], 65)

    def test_iki_boru_farkli_yukseklik_capraz_eslesmez(self):
        f = [flans(SOL, (16.5, 297.5, 1779.5)), flans(SOL, (16.5, 297.5, 895.5)),
             flans(SAG, (683.5, 297.5, 895.5)), flans(SAG, (683.5, 297.5, 1779.5))]
        b, e = askilik.eslestir(f)
        self.assertEqual((len(b), e), (2, []))
        for x in b:
            self.assertEqual(x["flanslar"][0][2], x["flanslar"][1][2])
            self.assertEqual(x["uzunluk_cm"], 65)

    def test_y_ekseni(self):
        on = pano("on", (0, 0, 0), (600, T, 800))
        arka = pano("arka", (0, 418, 0), (600, 418 + T, 800))  # iç boşluk 400
        b, e = askilik.eslestir([flans(on, (300, 16.5, 700)), flans(arka, (300, 419.5, 700))])
        self.assertEqual((len(b), b[0]["eksen"], b[0]["uzunluk_cm"]), (1, "y", 39))  # 390 mm

    def test_hiza_toleransi(self):
        tol = askilik.ASKILIK_HIZA_TOL_MM
        ic = [flans(SOL, (16.5, 297.5, 1779.5)), flans(SAG, (683.5, 297.5, 1779.5 + tol - 1))]
        dis = [flans(SOL, (16.5, 297.5, 1779.5)), flans(SAG, (683.5, 297.5, 1779.5 + tol + 1))]
        self.assertEqual(len(askilik.eslestir(ic)[0]), 1)
        b, e = askilik.eslestir(dis)
        self.assertEqual((b, [x["neden"] for x in e]), ([], ["karsi_flans_yok"] * 2))

    def test_farkli_modul_eslesmez(self):
        # modül sınırında sırt sırta iki duvar: M01'in sağ duvarı ↔ M02'nin sol duvarı
        m2_sol = pano("m2sol", (700, 0, 0), (700 + T, 580, 1850))
        b, e = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5), "M01"),
                                 flans(m2_sol, (716.5, 297.5, 1779.5), "M02")])
        self.assertEqual(b, [])
        self.assertEqual(len(e), 2)

    def test_modul_bilinmiyorsa_eslesmez(self):
        b, e = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5), None),
                                 flans(SAG, (683.5, 297.5, 1779.5), None)])
        self.assertEqual(b, [])
        self.assertEqual([x["neden"] for x in e], ["modul_yok", "modul_yok"])

    def test_ayni_pano_eslesmez(self):
        b, _ = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5)), flans(SOL, (16.5, 297.5, 1779.5))])
        self.assertEqual(b, [])

    def test_yatay_panoda_flans_eslesmez(self):
        # normal z olan (yatay) panolar: boru X/Y'de olmalı
        alt = pano("alt", (0, 0, 0), (600, 580, T))
        ust = pano("ust", (0, 0, 800), (600, 580, 800 + T))
        b, _ = askilik.eslestir([flans(alt, (300, 290, 16.5)), flans(ust, (300, 290, 801.5))])
        self.assertEqual(b, [])

    def test_pano_normali_eksen_degilse_eslesmez(self):
        # flanşlar x'te karşılıklı ama bir pano y-normalli
        y_pano = pano("ypano", (600, 0, 0), (1200, T, 1850))
        b, _ = askilik.eslestir([flans(SOL, (16.5, 9, 1779.5)), flans(y_pano, (683.5, 9, 1779.5))])
        self.assertEqual(b, [])

    def test_dis_yuzdeki_flans_eslesmez(self):
        # sağ duvarın DIŞ yüzündeki (x=699.5) flanş iç taraftaki boruya ait olamaz
        b, _ = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5)), flans(SAG, (699.5, 297.5, 1779.5))])
        self.assertEqual(b, [])

    def test_ara_bolmeli_iki_boru(self):
        # sol duvar | orta bölme (x 382–400, iki yüzünde flanş) | sağ duvar
        orta = pano("orta", (382, 0, 0), (400, 580, 1850))
        f = [flans(SOL, (16.5, 297.5, 1779.5)), flans(orta, (383.5, 297.5, 1779.5)),
             flans(orta, (398.5, 297.5, 1779.5)), flans(SAG, (683.5, 297.5, 1779.5))]
        b, e = askilik.eslestir(f)
        self.assertEqual(e, [])
        self.assertEqual(sorted((x["panolar"][0], x["panolar"][1], x["uzunluk_cm"]) for x in b),
                         [("orta", "sag", 27), ("sol", "orta", 35)])   # 282→27.2, 364→35.4

    def test_oklid_mesafesi_eksen_boslugundan_buyuk(self):
        # kısa asma bölme: yüz merkezleri z'de 400 mm kayık → Öklid, eksen boşluğundan uzun
        asma = pano("asma", (382, 0, 1050), (400, 580, 1850))   # z merkezi 1450; duvar 925
        b, _ = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5)), flans(asma, (383.5, 297.5, 1779.5))])
        self.assertEqual(b[0]["eksen_boslugu_mm"], 364.0)
        ham = (364.0 ** 2 + 525.0 ** 2) ** 0.5
        self.assertAlmostEqual(b[0]["ham_mm"], round(ham, 1))
        self.assertEqual(b[0]["uzunluk_cm"], askilik.yarim_yukari((ham - 10) / 10))  # 63

    def test_bos(self):
        self.assertEqual(askilik.eslestir([]), ([], []))

    def test_tek_eksik_flans(self):
        b, e = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5))])
        self.assertEqual((b, e[0]["neden"]), ([], "karsi_flans_yok"))


class OzetVePdfTestleri(unittest.TestCase):
    def test_ozet(self):
        b, e = askilik.eslestir([flans(SOL, (16.5, 297.5, 1779.5)), flans(SAG, (683.5, 297.5, 1779.5))])
        o = askilik.ozet(b, e, 2)
        self.assertEqual((o["flans"], o["eslesen_boru"], o["beklenen_boru"], o["tutarli"]), (2, 1, 1, True))
        o = askilik.ozet([], [{"neden": "karsi_flans_yok"}] * 2, 2)
        self.assertFalse(o["tutarli"])
        self.assertTrue(askilik.ozet([], [], 0)["tutarli"])

    def test_pdf_hucre(self):
        b = lambda *ls: [{"uzunluk_cm": L} for L in ls]  # noqa: E731
        self.assertEqual(askilik.pdf_hucre_metni(0, []), "")
        self.assertEqual(askilik.pdf_hucre_metni(None, []), "")
        self.assertEqual(askilik.pdf_hucre_metni(2, b(66, 96)), "2 (96, 66 cm)")
        self.assertEqual(askilik.pdf_hucre_metni(3, b(96, 66, 96)), "3 (2×96, 66 cm)")
        self.assertEqual(askilik.pdf_hucre_metni(2, b(96)), "2 (96, ? cm)")
        self.assertEqual(askilik.pdf_hucre_metni(1, []), "1 (? cm)")
        self.assertEqual(askilik.pdf_hucre_metni(3, []), "3 (3×? cm)")


if __name__ == "__main__":
    unittest.main(verbosity=1)
