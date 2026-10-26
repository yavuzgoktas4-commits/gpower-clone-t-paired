# `gpower-clone` — K2 Ailesi: `t-paired` İstatistiksel Güç ve Örneklem Büyüklüğü Motoru

> ### Tamamlanan Katmanlar Bildirimi
> Bu projede ödev kapsamındaki **tüm katmanlar (Temel + Bonus: 110 / 110 puan kapsamı)** eksiksiz olarak tamamlanmış ve doğrulanmıştır:
> - **[x] Temel Katman — Saf İstatistiksel Hesaplama Motoru ve CLI (`85 Puan`):** `src/engine/` ve `src/cli/` (`gpower-clone` / `python -m src.cli.main`), [SPEC.md](file:///c:/Users/pc/Desktop/GPower/SPEC.md), [LEDGER.md](file:///c:/Users/pc/Desktop/GPower/LEDGER.md), [HALLUCINATIONS.md](file:///c:/Users/pc/Desktop/GPower/HALLUCINATIONS.md), [oracle/ground_truth.csv](file:///c:/Users/pc/Desktop/GPower/oracle/ground_truth.csv) (30 vektörde **%100.00** tam $N$ ve $df$ eşleşmesi).
> - **[x] Bonus Katman 1 — MCP (Model Context Protocol) Sunucusu (`+15 Puan`):** `src/mcp/` altında hesap mantığını kopyalamadan doğrudan `src.engine` modülünü çağıran `power_analysis` MCP sunucusu ve [tests/test_mcp_equivalence.py](file:///c:/Users/pc/Desktop/GPower/tests/test_mcp_equivalence.py) eşdeğerlik testleri (**%100.00** bayt-bayt CLI == MCP JSON uyumu).
> - **[x] Bonus Katman 2 — Klinik AI Ajanı (`+10 Puan`):** `src/agent/` altında hekimlerin Türkçe klinik araştırma sorularını Sistem-1 sınıflandırıcısıyla ayrıştırıp MCP `power_analysis` aracını çağırarak yanıtlayan ajan, 10 soruluk değerlendirme seti ([tests/evaluation_questions.json](file:///c:/Users/pc/Desktop/GPower/tests/evaluation_questions.json)), çağrı kayıtları ([logs/agent_calls.jsonl](file:///c:/Users/pc/Desktop/GPower/logs/agent_calls.jsonl)) ve Vision GUI vs. MCP token/süre ölçüm raporu ([AGENT_COST.md](file:///c:/Users/pc/Desktop/GPower/AGENT_COST.md)).

---

## 1. İncelenen Hedef İkili Dosya (Binary) ve SHA-256 Özeti

| Özellik | Değer |
| :--- | :--- |
| **Orijinal Yazılım** | G\*Power 3.1.9.7 (Derleme 143, Windows x86 `PE32`) |
| **Dosya Adı** | `GPowerNT.exe` (`2,287,616` bayt) |
| **SHA-256 Hash** | `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812` |
| **İncelenen Test Ailesi** | **K2 — `t-paired`**: `Means: Difference between two dependent means (matched pairs)` (`PowerTPairedMean`, Test ID `0xcc`) |
| **Desteklenen Modlar** | `a-priori` (Örneklem büyüklüğü $N$ hesabı) ve `post-hoc` (Gerçekleşen güç $1-\beta$ hesabı) |

> **Not:** Etik ve yasal kurallar gereği `GPowerNT.exe` / `GPower.exe` ikili dosyaları `.gitignore` ile hariç tutulmuştur ve depoda yer almaz.

---

## 2. Demo Videosu, REA Doğrulaması ve Diferansiyel Test Uyum Özeti

- **60 Saniyelik CLI Demo Videosu:** <https://youtu.be/zTfv5gz5ZSg>
- **REA ve Ghidra Sağlayıcı Doğrulaması:**
  - Oturum başında ajana yöneltilen *"REA araçları ve Ghidra sağlayıcısı bu oturumda kullanılabilir mi?"* sorusunun doğrulama çıktısı:
  - `rea` MCP sunucusu (`rea-agents` v6.5.0, 207 MCP aracı; `open_binary`, `inspect_pe_resources`, `inspect_artifact`, `inspect_managed_artifact`, `close_binary` vb.) aktif olarak doğrulanmış ve kanıt kimlikleri (`ev_953c1e12...`, `ev_b3365da9...`, `ev_7d12a938...`) [LEDGER.md](file:///c:/Users/pc/Desktop/GPower/LEDGER.md) içinde kayıt altına alınmıştır.
  - *(Ekran görüntüsü referansı: `docs/rea_verification.png` / oturum doğrulama çıktısı)*

### 2.1. Diferansiyel Test Uyum Oranı Özeti (`tests/test_differential.py`)

Motorumuzun çıktıları, G\*Power 3.1.9.7 ekran görüntülerinden elde edilen [oracle/ground_truth.csv](file:///c:/Users/pc/Desktop/GPower/oracle/ground_truth.csv) (`30` vektör) ve kılavuzdaki [oracle/public_vectors.jsonl](file:///c:/Users/pc/Desktop/GPower/oracle/public_vectors.jsonl) (`25` açık vektör) ile otomatik olarak karşılaştırılmıştır:

| Veri Kümesi | Toplam Vektör | $N$ (`n_total`) ve $df$ Tam Eşleşme ($\|\text{fark}\| == 0$) | Kayan Nokta (`ncp`, `critical_t`, `actual_power`) Uyumu ($\le 10^{-6}$ Tolerans) | Maksimum Kayan Nokta Mutlak Farkı | Genel Başarı Oranı |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `oracle/ground_truth.csv` | `30` (20 a-priori, 10 post-hoc) | **`30 / 30` (%100.00)** | **`30 / 30` (%100.00)** | $4.97 \times 10^{-8}$ | **%100.00** |
| `oracle/public_vectors.jsonl` | `25` (15 a-priori, 10 post-hoc) | **`25 / 25` (%100.00)** | **`25 / 25` (%100.00)** | $4.97 \times 10^{-8}$ | **%100.00** |
| **CLI $\leftrightarrow$ MCP Eşdeğerliği** | `30` CSV + `25` JSONL | **`55 / 55` (%100.00)** | **Bayt-bayt birebir JSON eşleşmesi** | $0.0$ | **%100.00** |

---

## 3. Kurulum ve Tek Komutla Çalıştırma Adımları

### 3.1. Gereksinimler ve Kurulum
Proje Python $\ge 3.10$ ve dağılım fonksiyonları için yalnızca `scipy` paketini kullanır:

```bash
pip install scipy
```

### 3.2. CLI Aracını Çalıştırma (`gpower-clone` / `python -m src.cli.main`)

**Sürüm Sorgusu (`--version`):**
```bash
python -m src.cli.main --version
# veya Windows'ta:
.\gpower-clone.cmd --version
```
Çıktı (Çıkış Kodu `0`):
```json
{"name": "gpower-clone", "version": "1.0.0", "contract_version": "1.0.0", "test": "t-paired", "supported_tests": ["t-paired"]}
```

**A-Priori Örneklem Büyüklüğü Hesabı (`--mode a-priori`):**
```bash
python -m src.cli.main --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.80
```
Çıktı (Çıkış Kodu `0`):
```json
{"ncp": 2.9154759474226504, "critical_t": 2.0345152974493383, "df": 33, "n_total": 34, "actual_power": 0.8077775012792738}
```

**Post-Hoc İstatistiksel Güç Hesabı (`--mode post-hoc`):**
```bash
python -m src.cli.main --test t-paired --mode post-hoc --tails 1 --dz 0.11 --alpha 0.18 --n-total 546
```
Çıktı (Çıkış Kodu `0`):
```json
{"ncp": 2.5703307180205432, "critical_t": 0.9161374445293511, "df": 545, "n_total": 546, "actual_power": 0.9509338931871906}
```

### 3.3. MCP Sunucusunu Çalıştırma (`src/mcp/`)
Standart `stdio` JSON-RPC 2.0 protokolü üzerinden MCP sunucusunu başlatmak için:
```bash
python -m src.mcp.server
```

### 3.4. Klinik AI Ajanını Çalıştırma (`src/agent/`)
Hekimin Türkçe klinik sorusunu doğrudan komut satırından sormak için:
```bash
python -m src.agent "Tip 2 diyabetli aynı olgularda 12 haftalık tedavi öncesi ve sonrası HbA1c değişimini çift yönlü eşleştirilmiş t-testi ile inceleyeceğiz. dz = 0.5, alfa = 0.05 ve güç = 0.80 için gereken toplam hasta sayısı nedir?"
```

### 3.5. Test Paketlerini Tek Komutla Çalıştırma
```bash
# 1. Diferansiyel Test (30 CSV + 25 JSONL vektörü subprocess ile sınar):
python tests/test_differential.py

# 2. CLI <-> MCP Eşdeğerlik Testi:
python tests/test_mcp_equivalence.py

# 3. Klinik Ajan 10 Soru Değerlendirme ve Token Kıyaslama Testi:
python tests/test_agent_evaluation.py

# 4. Tüm Birim ve Entegrasyon Testlerini Birlikte Çalıştırma:
python -m unittest discover -s tests -v
```

---

## 4. MCP Sunucusu Araç Şeması (`power_analysis`)

`src/mcp/server.py` içindeki MCP sunucusu `power_analysis` adlı tek bir araç sunar ve tüm hesaplamaları `src.engine.paired_t.calculate_t_paired` fonksiyonuna delege eder.

### 4.1. Girdi Alanları (`inputSchema`)
| Alan Adı | JSON Tipi | Zorunluluk | Kabul Aralığı / Değerler | Açıklama |
| :--- | :--- | :---: | :--- | :--- |
| `test` | `string` | Zorunlu | `"t-paired"` | İstatistiksel test ailesi kimliği (`t2-indep`, `anova-oneway` vb. için `UNSUPPORTED` döner) |
| `mode` | `string` | Zorunlu | `"a-priori"`, `"post-hoc"` | Analiz modu (`a-priori`: $N$ hesabı, `post-hoc`: güç hesabı) |
| `tails` | `integer` | Zorunlu | `1` veya `2` | Kuyruk sayısı (`1`: tek kuyruklu, `2`: çift kuyruklu) |
| `dz` | `number` | Zorunlu | A-priori: $10^{-5} \le \|dz\| \le 20.0$<br>Post-hoc: $-20.0 \le dz \le 20.0$ | Eşleştirilmiş fark etki büyüklüğü ($d_z$) |
| `alpha` | `number` | Zorunlu | $10^{-7} \le \alpha \le 0.9999999$ | I. tip hata olasılığı ($\alpha$) |
| `power` | `number` | `a-priori` için zorunlu | $10^{-7} \le \text{power} \le 0.9999999$ ($\text{power} \ge \alpha$) | Hedef istatistiksel güç ($1-\beta$) |
| `n_total` | `integer` | `post-hoc` için zorunlu | $3 \le N \le 2147483646$ | Toplam örneklem (çift) büyüklüğü ($N$) |

### 4.2. Çıktı Alanları (`structuredContent` / `content[0].text`)
- **Başarılı Durum (`isError: false`):**
  - `ncp` (`float`): Merkezilikten uzaklık parametresi ($\delta = |dz| \cdot \sqrt{N}$)
  - `critical_t` (`float`): Merkezi Student-$t$ kritik eşik değeri ($t_{\text{crit}} = F_{t, df}^{-1}(1 - \alpha/k)$)
  - `df` (`int`): Serbestlik derecesi ($df = N - 1$)
  - `n_total` (`int`): Toplam örneklem (çift) büyüklüğü ($N$)
  - `actual_power` (`float`): Gerçekleşen istatistiksel güç ($1-\beta$)
- **Hata Durumu (`isError: true`):**
  - `error` (`string`): İnsan tarafından okunabilir hata açıklaması
  - `code` (`string`): `OUT_OF_RANGE` | `INCONSISTENT` | `MISSING_PARAM` | `UNKNOWN_PARAM` | `UNSUPPORTED` | `NO_SOLUTION`
  - `field` (`string`): Hataya neden olan parametre alanı

---

## 5. `CONTRACT.md` 1.0.0 Mimari Karar ve Yorum Beyanı

1. **Temiz Oda (Clean-Room) İzolasyonu:** Tersine mühendislik bulguları yalnızca [LEDGER.md](file:///c:/Users/pc/Desktop/GPower/LEDGER.md) ve Gherkin formatındaki [SPEC.md](file:///c:/Users/pc/Desktop/GPower/SPEC.md) belgelerine aktarılmıştır. `src/` altındaki hiçbir kaynak kod dosyasında decompile çıktısı, makine buyruğu veya bellek adresi yer almaz.
2. **Tek Kaynaklı Hesaplama Çekirdeği (`src/engine/`):** Tüm istatistiksel formüller, Brent kök bulma algoritması (`tol = 1e-10`, `EPS = 2^-53`, `max_iter = 300`), iki aşamalı tam sayıya yuvarlama kuralı ($\lceil \lfloor N \cdot 10^{10} + 0.5 \rfloor / 10^{10} \rceil$) ve parametre doğrulama kuralları yalnızca [`src/engine/paired_t.py`](file:///c:/Users/pc/Desktop/GPower/src/engine/paired_t.py) içinde tanımlanmıştır. Hem CLI (`src/cli/`) hem de MCP sunucusu (`src/mcp/`) bu motoru çağırır.
3. **Sözleşme Öncelik Sırası (`UNSUPPORTED` vs. `UNKNOWN_PARAM`):** Başka bir test ailesi (`--test t2-indep --ratio 1` vb.) çağrıldığında, o aileye özgü bayrakların `UNKNOWN_PARAM` üretmemesi için önce `--test` parametresi denetlenir ve sözleşme gereği her zaman `code: "UNSUPPORTED", field: "test"` (Çıkış Kodu `2`) döndürülür.
4. **Sistem-1 Sınıflandırma Tasarımı (`src/agent/`):** Klinik ajan katmanında 7 etiketli (`t2-indep`, `t-paired`, `anova-oneway`, `chi2-contingency`, `multireg-r2`, `ambiguous`, `unsupported`) deterministik bir Sistem-1 sınıflandırıcı kullanılmış; güven skoru `0.75`'in altında kaldığında veya `ambiguous`/`unsupported` döndüğünde hesaplama yapılmadan araştırmacıdan netleştirme istenmesi garanti altına alınmıştır.

---

## 6. Proje Dizin Yapısı

```text
GPower/
├── .gitignore
├── AGENT_COST.md                  # Vision GUI vs. MCP token/süre ölçümü ve süreç günlüğü
├── CONTRACT.md                    # CLI, MCP ve Klinik Ajan arayüz sözleşmesi (1.0.0)
├── HALLUCINATIONS.md              # Tespit edilen ve testlerle düzeltilen 3 yanılgı
├── LEDGER.md                      # [REA], [DOK] ve [AJAN] etiketli kanıt defteri
├── README.md                      # Kurulum, kullanım, mimari beyan ve akademik atıflar
├── SPEC.md                        # Gherkin formatında tam kabul kriterleri
├── gpower-clone                   # POSIX yürütülebilir CLI sarmalayıcısı
├── gpower-clone.cmd               # Windows CMD yürütülebilir CLI sarmalayıcısı
├── gpower-clone.ps1               # PowerShell yürütülebilir CLI sarmalayıcısı
├── pyproject.toml                 # Python paket yapılandırması
├── logs/
│   └── agent_calls.jsonl          # 10 klinik sorunun MCP araç çağrı kayıtları
├── oracle/
│   ├── ground_truth.csv           # 30 ekran görüntüsünden çıkarılan kâhin tablosu
│   ├── public_vectors.jsonl       # 25 açık referans vektörü
│   └── screenshot/                # G*Power 3.1.9.7 ekran görüntüleri (paired_01..30.png)
├── prompts/
│   ├── session_1_reverse.md       # Oturum 1 (Tersine Mühendislik) ilk prompt'u
│   └── session_2_cleanroom.md     # Oturum 2 (Temiz Oda Geliştirme) ilk prompt'u
├── src/
│   ├── engine/                    # Saf istatistiksel hesaplama motoru (paired_t.py, errors.py)
│   ├── cli/                       # CONTRACT.md 1.0.0 uyumlu CLI (main.py)
│   ├── mcp/                       # İnce JSON-RPC 2.0 MCP sunucusu (server.py)
│   └── agent/                     # Türkçe klinik AI ajanı (clinical_agent.py)
└── tests/
    ├── evaluation_questions.json  # 10 Türkçe/İngilizce kurgusal klinik araştırma sorusu
    ├── test_differential.py       # Subprocess tabanlı diferansiyel test düzeneği
    ├── test_mcp_equivalence.py    # CLI == MCP bayt-bayt JSON eşdeğerlik testleri
    └── test_agent_evaluation.py   # Klinik ajan doğruluk ve token kıyaslama testleri
```

---

## 7. Akademik Atıf ve Etik Beyan

Bu çalışma, eğitim ve bilimsel birlikte çalışabilirlik (ajan çağına uygun CLI/MCP arayüzü önerisi) amacıyla yürütülmüştür. Orijinal **G\*Power** yazılımının tüm hakları yazarlarına aittir; bu proje G\*Power'ın kendisi değildir ve G\*Power adıyla dağıtılamaz.

**Akademik Atıflar:**
- Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). G\*Power 3: A flexible statistical power analysis program for the social, behavioral, and biomedical sciences. *Behavior Research Methods*, 39(2), 175–191. https://doi.org/10.3758/BF03193146
- Faul, F., Erdfelder, E., Buchner, A., & Lang, A.-G. (2009). Statistical power analyses using G\*Power 3.1: Tests for correlation and regression analyses. *Behavior Research Methods*, 41(4), 1149–1160. https://doi.org/10.3758/BRM.41.4.1149
