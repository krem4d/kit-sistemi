Frenlli menteşe [ok]
Frensiz menteşe [ok]
Menteşe tabanı [ok]
Modül Bağlantı [ok]
Raf Pimi [ok]
Linco Gövde [ok]
Uzun Linco [sınanmadı]
Ayarlı Ayak [ok]
Ray seti Bağlantısı [Ray setinin kaç cm olduğunu yanlış buldu sayısını doğru buldu ama daha çok denenmesi lazım]
Askılık Flanşı [ok]
Ağaç Vidası [ok]
Arkalık çivisi [kontrol gerekli]
Renkli Parçalar [daha eklenmedi]
L Bağlantı seti [daha eklenmedi] 

Modül Modül bağlantı algoritması parçaları bulurken birbirine bağlanmaması gereken kısımlarıda bağladı 
Bunu düzeltmek için algoritmayı tamamen değiştirmiz gerekiyo öncelikle bütün modül bağlantı deliği hacmiye uygun olan deliklere bakılır daha sonrada birbirleri arasında 18mm (%0.1 tolerans) olan deliklerin ikisi bir şekilde sayılıp modül modül bağlantı olur tabi bu delikler bulunduktan sonra önce kulp algoritması çalışır ve bu algoritma sadece modül bağlantı delikleri - kulp delikleri olan kümede çalışır 

[DÜZELTİLDİ] pair_count (en-yakın-komşu, 200mm eşik) kaldırıldı; yerine
detect_modul_baglanti_pairs (TAM 18mm ±%0.1 kesin mesafe) geldi — kulp
algoritması hâlâ önce çalışıyor, yeni eşleştirme sadece kulp'tan arta kalan
delik kümesinde. Gerçek FBX ölçümü (diag_modul_mesafe.py) doğru çiftlerin
tam 18.000mm, bir sonraki alakasız mesafenin ise 101mm+ olduğunu doğruladı
(9313 siparişinde 2 delik artık YANLIŞ eşlenmek yerine eşleşmemiş kalıyor).
6 eski + 6 yeni siparişte pipeline yeniden çalıştırıldı, sonuçlar tutarlı.
Görsel doğrulama için: moduller_baglama_empty.py (aynı mantıkla, Empty
koyarak).