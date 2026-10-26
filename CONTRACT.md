# CLI Arayüz Sözleşmesi (CONTRACT) — Sürüm 1.0.0

Bu belge, `gpower-clone` komut satırı aracının (`python -m src.cli.main` veya `gpower-clone`) girdi bayraklarını, JSON çıktı şemasını, hata kodlarını ve çıkış kodlarını (exit codes) tanımlar.

- **Sözleşme Sürümü (`contract_version`):** `1.0.0`
- **Bu Depoda Desteklenen Test Ailesi:** `t-paired` (`Means: Difference between two dependent means (matched pairs)`)

---

## 1. Sürüm Sorgusu (`--version`)

Komut:
```bash
gpower-clone --version
# veya
python -m src.cli.main --version
```

`stdout` çıktısı (tek satır JSON, Çıkış Kodu `0`):
```json
{"name":"gpower-clone","version":"1.0.0","contract_version":"1.0.0","test":"t-paired","supported_tests":["t-paired"]}
```

---

## 2. Desteklenen Test Ailesi ve Parametreler (`t-paired`)

### 2.1. Ortak Zorunlu Parametreler
| Bayrak | Tip | Kabul Edilen Değerler / Aralık | Alan Adı (`field`) | Açıklama |
| :--- | :--- | :--- | :--- | :--- |
| `--test` | `string` | `t-paired` | `test` | Test ailesi kimliği (`t2-indep`, `anova-oneway`, `chi2-contingency`, `multireg-r2` vb. için `UNSUPPORTED` döner) |
| `--mode` | `string` | `a-priori`, `post-hoc` | `mode` | Analiz modu (`a-priori`: örneklem büyüklüğü $N$ hesabı; `post-hoc`: gerçekleşen güç hesabı) |
| `--tails` | `int` | `1` veya `2` | `tails` | Kuyruk sayısı (`1`: tek kuyruklu, `2`: çift kuyruklu) |
| `--dz` | `float` | A-priori: $10^{-5} \le \|dz\| \le 20.0$<br>Post-hoc: $-20.0 \le dz \le 20.0$ | `dz` | Eşleştirilmiş fark etki büyüklüğü ($d_z$) |
| `--alpha` | `float` | $10^{-7} \le \alpha \le 0.9999999$ | `alpha` | I. tip hata olasılığı ($\alpha$) |

### 2.2. Moda Özgü Zorunlu Parametreler
- **`--mode a-priori` için:**
  - `--power <float>` (`field`: `power`): Hedef istatistiksel güç ($1-\beta$). Kabul aralığı: $10^{-7} \le \text{power} \le 0.9999999$ ve $\text{power} \ge \alpha$ (`power < alpha` ise `INCONSISTENT`).
  - `--n-total` bu modda **verilemez** (verilirse `INCONSISTENT`).
- **`--mode post-hoc` için:**
  - `--n-total <int>` (veya `--n_total` / `--n`, `field`: `n_total`): Toplam çift (örneklem) sayısı $N$. Kabul aralığı: $3 \le N \le 2147483646$ tam sayı.
  - `--power` bu modda **verilemez** (verilirse `INCONSISTENT`).

---

## 3. Başarılı Çıktı Şeması (Çıkış Kodu `0`)

Başarılı hesaplamada `stdout` akışına **yalnızca tek satır JSON** yazılır ve süreç **Çıkış Kodu `0`** ile sonlanır:
- Kayan noktalı değerler (`ncp`, `critical_t`, `actual_power`) yuvarlanmadan tam IEEE-754 `float` hassasiyetiyle yazılır.
- Tam sayı alanları (`df`, `n_total`) JSON `int` tipinde yazılır.

### Örnek Çağrı (A-priori):
```bash
python -m src.cli.main --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.80
```
### Örnek Çıktı:
```json
{"ncp":2.9154759474226504,"critical_t":2.0345152974493383,"df":33,"n_total":34,"actual_power":0.80777752820832}
```

### Örnek Çağrı (Post-hoc):
```bash
python -m src.cli.main --test t-paired --mode post-hoc --tails 1 --dz 0.11 --alpha 0.18 --n-total 546
```
### Örnek Çıktı:
```json
{"ncp":2.570330718020543,"critical_t":0.9161373977234766,"df":545,"n_total":546,"actual_power":0.9509339157308046}
```

---

## 4. Hata Şeması ve Çıkış Kodları

Hata durumunda `stdout` akışına **yalnızca tek satır JSON** basılır:
```json
{"error":"<açıklama>","code":"<HATA_KODU>","field":"<alan_adı>"}
```

| Hata Kodu (`code`) | Çıkış Kodu | Tetiklenme Koşulu |
| :--- | :---: | :--- |
| `OUT_OF_RANGE` | `2` | Parametre tipinin geçersiz olması veya sayısal değerin `SPEC.md` sınırları dışında kalması (`tails`, `dz`, `alpha`, `power`, `n_total`). |
| `INCONSISTENT` | `2` | Parametreler arası mantıksal çelişki (ör. A-priori modunda `power < alpha`, A-priori modunda `--n-total` verilmesi, Post-hoc modunda `--power` verilmesi). |
| `MISSING_PARAM` | `2` | Zorunlu bir parametrenin (`test`, `mode`, `tails`, `dz`, `alpha`, `power` veya `n_total`) eksik olması. |
| `UNKNOWN_PARAM` | `2` | Sözleşmede yer almayan veya `t-paired` ailesine ait olmayan bayrak kullanımı (ör. `--ratio`, `--foo`). |
| `UNSUPPORTED` | `2` | Başka bir test ailesinin (`t2-indep`, `anova-oneway`, `chi2-contingency`, `multireg-r2` vb.) veya desteklenmeyen bir modun çağrılması. |
| `NO_SOLUTION` | `1` | Kök bulma algoritmasının yakınsayamaması (300 iterasyon aşımı), sayısal taşma veya bulunan $N$ değerinin üst sınırı (`2147483646`) aşması. |

---

## 7. MCP Sunucusu Sözleşmesi (`power_analysis`)

`src/mcp/` altındaki MCP sunucusu (`python -m src.mcp.server`), hesaplama mantığını kopyalamadan doğrudan `src.engine` modülünü çağıran ince bir JSON-RPC 2.0 adaptörüdür ve `power_analysis` adlı tek bir araç (tool) sunar.

### 7.1. Araç Şeması (`tools/list`)
- **Araç Adı (`name`):** `power_analysis`
- **Girdi Şeması (`inputSchema`):**
  - `test` (`string`, zorunlu): `"t-paired"`
  - `mode` (`string`, zorunlu): `"a-priori"` veya `"post-hoc"`
  - `tails` (`integer`, zorunlu): `1` veya `2`
  - `dz` (`number`, zorunlu): Etki büyüklüğü $d_z$
  - `alpha` (`number`, zorunlu): I. tip hata olasılığı $\alpha$
  - `power` (`number`, `a-priori` için zorunlu): Hedef güç ($1-\beta$)
  - `n_total` (`integer`, `post-hoc` için zorunlu): Toplam örneklem büyüklüğü $N$

### 7.2. Çıktı ve Hata Eşdeğerliği (`tools/call`)
- **Başarılı çağrıda (`isError: false`):** `content[0].text` alanı CLI `stdout` çıktısıyla **birebir aynı** tek satır JSON dizesini (`{"ncp": ..., "critical_t": ..., "df": ..., "n_total": ..., "actual_power": ...}`) içerir.
- **Hatalı çağrıda (`isError: true`):** `content[0].text` alanı CLI hata çıktısıyla **birebir aynı** `{"error": "...", "code": "...", "field": "..."}` JSON dizesini içerir.

---

## 8. Klinik AI Ajanı ve Çağrı Kayıt Sözleşmesi (`src/agent/`)

`src/agent/` altındaki klinik ajan katmanı, hekimin doğal dilde (Türkçe) sorduğu klinik araştırma sorusunu ayrıştırır, MCP sunucusundaki `power_analysis` aracını (`tools/call`) çağırır ve dönen sonucu hekime açıklar.

### 8.1. Temel Kurallar
1. **Sıfır Ajan İçi Hesaplama:** Ajan kesinlikle kendi içinde $N$, $df$, $t_{\text{crit}}$, $\delta$ veya güç hesabı yapmaz; tüm sayılar yalnızca MCP `power_analysis` aracından gelir.
2. **Sistem-1 Test Ailesi Sınıflandırması ve Güven Eşiği:**
   - Etiket kümesi: `t2-indep`, `t-paired`, `anova-oneway`, `chi2-contingency`, `multireg-r2`, `ambiguous`, `unsupported`.
   - Güven skoru `confidence < 0.75` ise veya etiket `ambiguous` / `unsupported` ise ajan hesap yapmadan araştırmacıdan netleştirme ister veya `UNSUPPORTED` döner.
3. **Çağrı Kayıt Formatı (`logs/agent_calls.jsonl`):**
   Her araç çağrısı `logs/agent_calls.jsonl` dosyasına tek satır JSON olarak kaydedilir:
   ```json
   {"ts": "2026-10-26T23:32:00+03:00", "question": "...", "tool_input": {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8}, "tool_output": {"ncp": 2.9154759474226504, "critical_t": 2.0345152974493383, "df": 33, "n_total": 34, "actual_power": 0.8077775012792738}, "tokens_in": 92, "tokens_out": 68}
   ```
