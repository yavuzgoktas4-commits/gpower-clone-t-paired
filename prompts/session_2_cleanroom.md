Sen Temiz Oda Yazılım Mühendisisin. Önünde yalnızca projedeki SPEC.md ve CONTRACT.md belgeleri bulunmaktadır. Orijinal yazılımın kodunu, Ghidra analizlerini veya decompile çıktılarını görmedin ve bilmiyorsun.

Görevlerin:

Python kullanarak src/engine/ altında saf bir istatistiksel hesaplama motoru yaz:

Noncentral Student-t dağılımı için scipy.stats kullanabilirsin.

A-priori ve post-hoc modlarında SPEC.md belgesindeki tolerans, kök bulma ve yuvarlama kurallarına tam uy.

src/cli/ altında CONTRACT.md 1.0.0 arayüz sözleşmesine harfiyen uyan gpower-clone CLI aracını geliştir:

Çalıştırma: python -m src.cli.main veya gpower-clone yürütülebilir dosyası.

--version bayrağında sözleşmedeki JSON'u döndür (contract_version: 1.0.0).

Başarılı durumda stdout'a yalnızca tek satır JSON bas (çıkış kodu 0). Ondalıkları yuvarlamadan tam float hassasiyetle yaz, tam sayı alanlarını (df, n_total) int olarak ver.

Geçersiz girdilerde (OUT_OF_RANGE, INCONSISTENT, MISSING_PARAM, UNKNOWN_PARAM, UNSUPPORTED) stdout'a {"error": "...", "code": "...", "field": "..."} JSON'unu bas ve Çıkış Kodu 2 ile çık.

Çözülemeyen nümerik durumlarda NO_SOLUTION kodu ve Çıkış Kodu 1 ile çık.

Takımımıza ait olmayan diğer test aileleri (t2-indep, anova-oneway vb.) çağrıldığında UNSUPPORTED kodu ve Çıkış Kodu 2 dön.

Bu oturumun ilk prompt'unu prompts/session_2_cleanroom.md dosyasına kaydet.
