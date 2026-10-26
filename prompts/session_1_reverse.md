# Session 1 — Reverse Engineering Prompt

## Oracle Extraction Prompt
Projedeki oracle/screenshots/ klasöründe GPower'dan alınmış 30 adet test ekran görüntüsü bulunmaktadır. Görevin:

Bu ekran görüntülerindeki girdi (Input Parameters) ve çıktı (Output Parameters) değerlerini tek tek oku.

oracle/ground_truth.csv dosyasını oluştur ve şu sütunlarla değerleri satır satır içine yaz:

id,mode,tails,dz,alpha,power_input,n_total_input,expected_ncp,expected_critical_t,expected_df,expected_n_total,expected_actual_power

Kılavuzdaki 25 açık referans vektörünü de oracle/public_vectors.jsonl olarak kaydet.

---

## Reverse Engineering Analysis Prompt
Sen bir Tersine Mühendislik Analistisin. Projedeki GPowerNT.exe (veya GPower.exe) dosyasını Ghidra ve REA araçlarını kullanarak analiz edeceksin. Konumuz K2 ailesi: t-paired (Means: Difference between two dependent means - matched pairs).

Kesinlikle uygulama kodu yazma. Yalnızca davranış ve algoritma çıkarımı yap.

Görevlerin:
- t-paired test ailesinin a-priori ve post-hoc hesaplama rutinlerini, FPU/kayan nokta işlemlerini ve fonksiyon adreslerini tespit et.
- Kılavuzda yer almayan şu kritik davranışları sök ve belgele:
  - $df = N - 1$ ilişkisi ve kritik $t$ değerinin hesaplanma yöntemi.
  - Noncentrality parameter ($\delta = dz \cdot \sqrt{N}$) formülünün ikili düzeydeki karşılığı.
  - A-priori modunda $N$ değerini bulurken kullanılan kök bulma algoritması, durma toleransı (tol), döngü sınırları ve $N$'nin tam sayıya yuvarlanma kuralı (ceil / yukarı yuvarlama adımları).
  - Uç değerlerdeki (ör. $\text{power} = \alpha$, $dz$ çok küçük/büyük) davranışlar.

Çıktı olarak iki dosya üret:
- LEDGER.md: Tespit ettiğin tüm bulguları [REA] (fonksiyon adresi/dize kanıtı ile), [DOK] (resmi makale/kılavuz referansı) ve [AJAN] (kanıtlanamayan çıkarımlar) etiketleriyle yaz. Puanın [REA] satırlarından geldiğini unutma.
- SPEC.md: Çıkarılan bu davranışları Gherkin formatında (Feature, Scenario, Given, When, Then) tam bir kabul kriteri belgesi olarak yaz.
- Bu oturumun ilk prompt'unu prompts/session_1_reverse.md olarak kaydet.
