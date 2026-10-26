# Tersine Mühendislik Bulguları Defteri (LEDGER) — K2 Ailesi: `t-paired` (`PowerTPairedMean`)

Bu belge, `GPowerNT.exe` (G\*Power 3.1.9.7, derleme 143) ikili dosyası üzerinde REA (Reverse Engineer Anything) araçları ve statik x86/SSE2/x87 FPU sökümü (disassembly) kullanılarak gerçekleştirilen tersine mühendislik analizinin kanıt defteridir. Tüm bulgular aşağıdaki üç kanıt etiketiyle sınıflandırılmıştır:

- **`[REA]`**: Doğrudan ikili dosyadan (sanal adres `VA`, dosya ofseti, `vtable` indeksi, makine buyruğu dizisi, `.rdata` sabiti/dizesi veya REA kanıt kimliği `ev_...`) elde edilen kesin tersine mühendislik kanıtları.
- **`[DOK]`**: G\*Power 3 resmi kılavuzu (Faul, Erdfelder, Lang, & Buchner, 2007; Faul, Erdfelder, Buchner, & Lang, 2009) ve standart istatistik/sayısal analiz literatürü referansları.
- **`[AJAN]`**: Doğrudan sembol tablosunda yer almayan (strip edilmiş) ancak kontrol akışı, sabitler ve çağrı grafiklerinden çıkarılan analitik/mimari yorumlar.

---

## 1. İkili Dosya (Binary) Kimliği ve REA Kanıt Kayıtları

- **`[REA]`** **Hedef İkili Dosya:** `GPowerNT.exe` (`2,287,616` bayt), SHA-256: `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`, format: `PE32` (`pei-i386`, 32-bit x86 Windows GUI), `ImageBase = 0x00400000` (REA Kanıt Kimliği: `ev_b3365da9b541f3fb5094feb1182dece10d7da70c93788d88438bce6918cc6694`, alt envanter kanıtı: `ev_53b89b895b9a4ae2d5c7ae04254a583d87a44096ef9d50b95666889889282a50`, kök artefakt kimliği: `art_1011c7d03a3a196495d11d861aab7e83cc2915c5428091f0c64125f59dbbeadd`).
- **`[REA]`** **PE Bölüm (Section) Yerleşimi ve Yönetilmeyen Kod Doğrulaması:** REA `inspect_managed_artifact` kanıtı (`ev_7d12a9384f2cd8a6616c4207bf7f88dd03128d664736b7f147cfc6f4dfebe2e7`, üst kanıt `ev_f6bffab10c720131ad987584d6499f5fa3a762cd502a227c3ae3a1bbfa8365f1`) ve PE kaynak analizi (`ev_953c1e12223997c5b6f01e78d57376c75f585a983802459e36b08a791b26e502`) ikili dosyanın yerel (native) MSVC C++ derlemesi olduğunu ve 4 bölümden oluştuğunu doğrular:
  - `.text`: `VA = 0x00401000`, `VirtualSize = 0x001bca07`, `RawOffset = 0x00000400`, `RawSize = 0x001bcc00`
  - `.rdata`: `VA = 0x005be000`, `VirtualSize = 0x00049a6e`, `RawOffset = 0x001bd000`, `RawSize = 0x00049c00`
  - `.data`: `VA = 0x00608000`, `VirtualSize = 0x000818c8`, `RawOffset = 0x00206c00`, `RawSize = 0x00006a00`
  - `.rsrc`: `VA = 0x0068a000`, `VirtualSize = 0x000211d0`, `RawOffset = 0x0020d600`, `RawSize = 0x00021200`

---

## 2. RTTI Sınıf Hiyerarşisi, Vtable Yapısı ve Bellek Yerleşimi

- **`[REA]`** **MSVC RTTI Sınıf Kimliği (`PowerTPairedMean`):** `.data` ve `.rdata` bölümlerindeki MSVC Run-Time Type Information (RTTI) yapıları incelendiğinde `t-paired` ailesini temsil eden sınıfın tam C++ mangled adı `.?AVPowerTPairedMean@@` olarak tespit edilmiştir:
  - `TypeDescriptor` adresi: `0x0060ce88` (isim dizesi `0x0060ce90`: `".?AVPowerTPairedMean@@"`)
  - `CompleteObjectLocator` (COL) adresi: `0x005ef6a0` (`0x005cac5c` adresindeki `vtable[-1]` işaretçisi tarafından referans alınır)
  - `ClassHierarchyDescriptor` adresi: `0x005ef6b4` (`num_bases = 5`, `BaseClassArray` adresi: `0x005ef6c4`)
  - Nesne boyutu (allocation size): `0x368` (`872` bayt) — fabrika oluşturucusu `0x004d2ebe` (`push 0x368; call 0x005aa095 [operator new]`) ve klonlayıcı `0x004dc9fd` (`push 0x368; call 0x005aa095`) içinde doğrulanmıştır.
- **`[REA]`** **Kalıtım Zinciri (Inheritance Hierarchy):** `0x005ef6c4` adresindeki `BaseClassArray` diziliminden 5 seviyeli kalıtım ağacı çıkarılmıştır:
  1. `PowerTPairedMean`: `vtable = 0x005cac60` (dosya ofseti `0x001c9c60`), `COL = 0x005ef6a0`, `TD = 0x0060ce88`
  2. `PowerTOneMean`: `vtable = 0x005ca8d0` (dosya ofseti `0x001c98d0`), `COL = 0x005ef5a4`, `TD = 0x0060ce28` (`".?AVPowerTOneMean@@"`)
  3. `PowerT`: `vtable = 0x005ca2d8` (dosya ofseti `0x001c92d8`), `COL = 0x005ef404`, `TD = 0x0060cd90` (`".?AVPowerT@@"`)
  4. `PowerAnalysis`: `vtable = 0x005c68b8` (dosya ofseti `0x001c58b8`), `COL = 0x005ee81c`, `TD = 0x0060c8a4` (`".?AVPowerAnalysis@@"`)
  5. `Root`: `BCD = 0x005ee71c`, `TD = 0x0060c618` (`".?AVRoot@@"`)
- **`[REA]`** **`PowerTPairedMean` ve `PowerTOneMean` Matematiksel Özdeşliği:** `0x005cac60` (`PowerTPairedMean`) ve `0x005ca8d0` (`PowerTOneMean`) sanal metod tabloları (75'er giriş, `0x000`–`0x128` ofsetleri) karşılaştırıldığında, **75 sanal metodun 70'inin birebir aynı fonksiyon adreslerini gösterdiği**, `PowerTPairedMean` sınıfının yalnızca aşağıdaki 5 metodu ezdiği (override ettiği) kanıtlanmıştır:
  - `vtable[+0x00c]` (indeks 3 — Clone): `0x004dc9d0` (`PowerTOneMean` içinde `0x004dba40`). `0x368` bayt ayırır ve `0x004dc9b0` kopya oluşturucusunu çağırır.
  - `vtable[+0x078]` (indeks 30 — Test Adı): `0x004dcf10` (`PowerTOneMean` içinde `0x004dbae0`). `.rdata` `0x005cb56c` (dosya ofseti `0x001ca56c`) adresindeki `"Means: Difference between two dependent means (matched pairs)"` dizesini döndürür.
  - `vtable[+0x0a4]` (indeks 41 — Etki Büyüklüğü Parametre Kimliği): `0x004d2950` (`mov eax, 0x60; ret`). `PowerTOneMean` içindeki `0x00496970` (`mov eax, 0x11; ret` -> `"Effect size d"`) yerine `0x60` kimliğini döndürerek arayüzde `"Effect size dz"` (`0x005cb684`, dosya ofseti `0x001ca684`) etiketinin kullanılmasını sağlar.
  - `vtable[+0x0ac]` (indeks 43 — Test Kimliği / Enum): `0x004d2b00` (`mov eax, 0xcc; ret`). `PowerTOneMean` için `0xcb` (`0x004db920`) iken `PowerTPairedMean` için `0xcc` döndürür (`0x004d2ea5` fabrika switch-case tablosunda `0xcc` -> `PowerTPairedMean`).
  - `vtable[+0x0c4]` (indeks 49 — Arayüz / Yardım Kurulumu): `0x004dcd60` (`PowerTOneMean` içinde `0x004dbe50`).
- **`[DOK]`** İstatistiksel olarak eşleştirilmiş iki bağımlı grup arasındaki fark testi ($d_z = \mu_{\text{diff}} / \sigma_{\text{diff}}$), fark puanlarının ($\text{diff}_i = X_{1i} - X_{2i}$) sıfır sabitine karşı tek örneklem $t$-testi ile matematiksel olarak özdeştir (Faul et al., 2007, s. 182–183).
- **`[REA]`** **Temel Sanal Metod (Vtable) ve Yardımcı Fonksiyon Adres Tablosu:**
  - `0x004dbd00`: `PowerTOneMean::PowerTOneMean` yapıcısı (constructor). `0x004d2180` (`PowerT::PowerT`) yapıcısını çağırır, `vtable` adresini `0x005ca8d0` yapar, ardından `PowerTPairedMean` oluşturulurken `0x004d2ee4` veya `0x004dc9b0` tarafından `vtable` `0x005cac60` olarak atanır.
  - `0x004dc2a0` (`vtable[+0x008]`, indeks 2): Ana hesaplama dağıtıcısı (`Calculate` / `Dispatch`). `[esi+0x48]` adresindeki analiz moduna (`0` = A-priori, `1` = Compromise, `2` = Criterion, `3` = Post-hoc, `4` = Sensitivity) göre dallanır (`0x004dca78` jump table).
  - `0x00496830` (`vtable[+0x004]`, indeks 1): Kök bulucu hedef fonksiyon dağıtıcısı (`ObjectiveFunction`). `[ecx+0x2ac] == 0` (A-priori $N$ çözümü) olduğunda `vtable[+0x11c]` (`0x004968d0`) fonksiyonunu çağırır.
  - `0x004968d0` (`vtable[+0x11c]`, indeks 71): A-priori hedef fonksiyonu $f(N) = \text{Power}(|dz|, \alpha, N) - \text{power}_{\text{input}}$.
  - `0x00496aa0` (`vtable[+0x048]`, indeks 18): A-priori örneklem büyüklüğü ($N$) çözücü ana rutini.
  - `0x0049a210` (`vtable[+0x064]`, indeks 25) ve `0x004962d0`: A-priori kök arama aralığı $[x_{\text{low}}, x_{\text{high}}]$ ilklendirme (bracketing) rutinleri.
  - `0x004f9bb0`: Brent kök bulma algoritması (`zbrent` türevi; bisection + secant + inverse quadratic interpolation).
  - `0x00496a20` (`vtable[+0x074]`, indeks 29): İki aşamalı tam sayıya yukarı yuvarlama (`round-to-1e-10` + `ceil`) rutini.
  - `0x004bdee0` (`vtable[+0x030]`, indeks 12): Verilen $(dz, \alpha, N)$ için güç (`Power`) hesaplama sarmalayıcısı; $N_1 = N_2 = 0.5 \cdot N$ atamasını yapar ve `vtable[+0x034]` (`0x004d38b0`) rutinini çağırır.
  - `0x004d38b0` (`vtable[+0x034]`, indeks 13): `PowerT` çekirdek hesaplama rutini (`Critical t`, `df`, $\delta$ ve `Actual power` / `Power` hesabı).
  - `0x004db950` (`vtable[+0x124]`, indeks 73): Serbestlik derecesi ($df = N - 1$) hesaplama rutini.
  - `0x004dc1b0` (`vtable[+0x128]`, indeks 74): Merkezilikten uzaklık parametresi ($\delta = dz \cdot \sqrt{N}$) birincil hesaplama rutini.
  - `0x004dbdc0` (`vtable[+0x050]`, indeks 20): `0x004d38b0` içinden çağrılan $\delta = dz \cdot \sqrt{N_1 + N_2}$ yardımcı rutini.
  - `0x004fa7e0` (`TDistribution::vtable[+0x04]`, indeks 1): Merkezi (`0x004514f0`) ve merkezi olmayan (`0x004f9fa0`) Student $t$ birikimli dağılım fonksiyonu (`CDF`).
  - `0x004fb8c0` (`TDistribution::vtable[+0x08]`, indeks 2): Student $t$ ters birikimli dağılım / kantil fonksiyonu (`Inverse CDF` / `Quantile`, merkezi durumda `0x004514f0` `cdft` `which=2` çağrısı).
- **`[REA]`** **`PowerTPairedMean` Nesne İçi Alan Ofsetleri (`this` işaretçisi `ecx`/`esi`/`edi`):**
  - `[this+0x48]` (`DWORD`): Analiz modu (`0` = A-priori, `3` = Post-hoc).
  - `[this+0x58]` (`TDistribution*`): `0x004d219e` adresinde `0x28` bayt olarak ayrılan ve `vtable = 0x005c4a20` (`.?AVTDistribution@@`) atanan dağılım nesnesi işaretçisi. İç parametre bloğu `[dist+0x08]` (`dist+0x10` adresini gösterir):
    - `[[this+0x58]+0x08]+0x00` (`double`): Dağılımın anlık $\delta$ (noncentrality) parametresi (`0x0043e520` `vtable[+0x2c]` ile güncellenir).
    - `[[this+0x58]+0x08]+0x08` (`double`): Dağılımın anlık $df$ (serbestlik derecesi) parametresi.
  - `[this+0x60]` (`double`): Maksimum arama sınırı ölçeği (`0x00496f2e` adresinde `0x005c5178` = `100000.0` ile ilklendirilir).
  - `[this+0x68]` (`double`): Kök arama alt sınırı $x_{\text{low}}$ (`N_min`).
  - `[this+0x70]` (`double`): Kök arama üst sınırı $x_{\text{high}}$.
  - `[this+0x80]` (`double`): Çıktı serbestlik derecesi (`df`).
  - `[this+0x90]` (`double`): Çıktı merkezilikten uzaklık parametresi (`Noncentrality parameter` $\delta$).
  - `[this+0x98]` (`double`): Çıktı kritik $t$ değeri (`Critical t`).
  - `[this+0xa8]` (`double`): Grup çarpan adımı (`0x004bdb9b` adresinde `0x005c6e50` = `1.0000000000000009` / `0x3ff0000000000004` ile ilklendirilir).
  - `[this+0xb0]` (`double`): $\alpha$ hata olasılığı (`alpha`, varsayılan `0.05` @ `0x005c6db0`).
  - `[this+0xb8]` (`double`): Güç (`1-beta err prob`, varsayılan `0.95` @ `0x005c6db8`; Post-hoc modunda hesaplanan güç çıktısı `0x004dc998` adresinde buraya yazılır).
  - `[this+0xc0]`, `[this+0xc8]` (`double`): İç grup örneklem büyüklükleri $N_1, N_2$ (`0x004bdee0` içinde her biri $0.5 \cdot N$ olarak atanır, böylece $N_1 + N_2 = N$).
  - `[this+0xd8]` (`double`): Etki büyüklüğü $dz$ (`Effect size dz`, varsayılan `0.5` @ `0x005c29a8`).
  - `[this+0xe8]` (`double`): Toplam örneklem büyüklüğü $N$ (`Total sample size`, varsayılan `100.0` @ `0x005c3b58`).
  - `[this+0x108]` (`double`): A-priori modunda tam sayı $N$ için yeniden hesaplanan gerçekleşen güç (`Actual power`).
  - `[this+0x2a8]` (`BYTE`): İki örneklem bayrağı (`0x004dbd64` adresinde `0` atanır; `PowerTTwoMeans` için `1`).
  - `[this+0x2a9]` (`BYTE`): Kuyruk (tail) bayrağı (`1` = Tek kuyruklu / One-tailed, `0` = Çift kuyruklu / Two-tailed).
  - `[this+0x2ac]` (`DWORD`): Çözücü hedef modu (`0` = A-priori $N$ çözümü).
  - `[this+0x358]` (`BYTE`): Bilinen varyans bayrağı (`0x004dbd70` adresinde `0` atanır; `0` olduğunda $df = N - 1$ için $1.0$ çıkarılır).
  - `[this+0x35c]` (`DWORD`): Çarpan tablosu indeksi (`0x004dbd6b` adresinde `0` atanır; `0x006096a8[0] = 1.0`).
  - `[this+0x360]` (`DWORD`): Sonlu anakütle büyüklüğü $N_{\text{pop}}$ (`0x004dbd75` adresinde `-1` / `0xffffffff` atanır; devre dışı).

---

## 3. Kritik Davranış 1: $df = N - 1$ İlişkisi ve Kritik $t$ (`Critical t`) Hesaplama Yöntemi

### 3.1. Serbestlik Derecesi ($df = N - 1$) Hesabı
- **`[REA]`** **Fonksiyon Adresi:** `0x004db950` (`PowerTOneMean` / `PowerTPairedMean` `vtable[+0x124]`, indeks 73).
- **`[REA]`** **Makine Buyrukları ve FPU/SSE2 Akışı (`0x004db950`–`0x004db987`):**
  1. `0x004db950`: `mov eax, DWORD PTR [ecx+0x35c]` — çarpan tablosu indeksini (`0`) yükler.
  2. `0x004db956`: `movsd xmm0, QWORD PTR [eax*8+0x6096a8]` — `.data` `0x006096a8` adresindeki `1.0` (`double`) çarpanını `xmm0` yazmacına yükler.
  3. `0x004db95f`: `mulsd xmm0, QWORD PTR [ecx+0xe8]` — `xmm0` değerini `[this+0xe8]` adresindeki toplam örneklem büyüklüğü $N$ ile çarpar ($1.0 \cdot N$).
  4. `0x004db967`: `cmp BYTE PTR [ecx+0x358], 0x0` ve `0x004db96e`: `jne 0x4db978` — `[this+0x358]` bayrağını kontrol eder (`0x004dbd70` yapıcısında sabit `0` atanmıştır).
  5. `0x004db970`: `subsd xmm0, QWORD PTR ds:0x5c19a0` — `.rdata` `0x005c19a0` adresindeki IEEE-754 çift duyarlıklı `1.0` (`0x3ff0000000000000`) sabitini `xmm0`'dan çıkarır:
     $$df = 1.0 \cdot N - 1.0 = N - 1$$
  6. `0x004db978`–`0x004db97e`: `mov eax, DWORD PTR [ecx+0x58]; mov eax, DWORD PTR [eax+0x8]; movsd QWORD PTR [eax+0x8], xmm0` — hesaplanan $df$ değerini doğrudan `TDistribution` nesnesinin parametre bloğuna (`[[this+0x58]+0x08]+0x08`) yazar ve `0x004db983` (`fld QWORD PTR [esp]`) ile `st(0)` x87 FPU yığını tepesinde döndürür.
  7. Çağıran rutin `0x004d38b0` (`0x004d390c`: `call DWORD PTR [eax+0x124]`), dönen $df$ değerini `0x004d3912` (`fstp QWORD PTR [edi+0x80]`) buyruğuyla çıktı alanı `[this+0x80]` (`expected_df`) içine kaydeder.
- **`[DOK]`** Eşleştirilmiş çiftler $t$-testinde $N$ çift (fark puanı) üzerinden örneklem ortalaması tahmin edildiği için serbestlik derecesi $df = N - 1$'dir (Faul et al., 2007, s. 182).

### 3.2. Kritik $t$ (`Critical t`) Hesaplama Yöntemi
- **`[REA]`** **Fonksiyon Adresleri:**
  - Çağıran çekirdek rutin: `0x004d38b0` (`PowerT::vtable[+0x034]`, indeks 13; `0x004d3918`–`0x004d39c1` aralığı).
  - Kantil (Inverse CDF) metodu: `0x004fb8c0` (`TDistribution::vtable[+0x08]`, indeks 2).
  - Alt seviye merkezi $t$ ters CDF çözücüsü: `0x004514f0` (DCDFLIB `cdft` rutini, `which = 2`).
- **`[REA]`** **Kuyruk Bayrağı (`[this+0x2a9]`) Kodlaması:**
  - Arayüzdeki `"Tail(s)"` açılır kutusundan okunan indeks (`ebx`: `0` = `"One"`, `1` = `"Two"`), A-priori modunda `0x004dc3bc` (`test ebx, ebx; sete al; mov BYTE PTR [esi+0x2a9], al`) ve Post-hoc modunda `0x004dc7aa` (`test ebx, ebx; sete al; mov BYTE PTR [esi+0x2a9], al`) buyruklarıyla `[this+0x2a9]` alanına yazılır:
    - Tek kuyruk (`tails = 1`, dropdown indeksi `0`): `[this+0x2a9] = 1`
    - Çift kuyruk (`tails = 2`, dropdown indeksi `1`): `[this+0x2a9] = 0`
- **`[REA]`** **Adım Adım `Critical t` Hesaplama Akışı (`0x004d3918`–`0x004d39c1`):**
  1. **Merkezi $t$ Dağılımına Sıfırlama ($\delta = 0.0$):**
     - `0x004d3918`–`0x004d3934`: `mov ecx, DWORD PTR [edi+0x58]; xorps xmm0, xmm0; movsd QWORD PTR [esp], xmm0; call DWORD PTR [eax+0x2c]` (`0x0043e520`) buyruklarıyla `TDistribution` nesnesinin merkezilikten uzaklık parametresi $\delta = 0.0$ yapılır.
  2. **Etki Büyüklüğü Mutlak Değer Ön İşlemesi ($|dz|$):**
     - Hem A-priori (`0x004dc3cb`: `andps xmm0, XMMWORD PTR ds:0x5c1a20`) hem de Post-hoc (`0x004dc7c8`: `andps xmm0, XMMWORD PTR ds:0x5c1a20`) modlarında, `.rdata` `0x005c1a20` adresindeki `0x7fffffffffffffff` bit maskesi uygulanarak `[this+0xd8]` alanına $|dz| \ge 0$ yazılır.
  3. **Olasılık ($p$) ve Kuyruk Böleni ($k$) Hesabı (`0x004d3937`–`0x004d3989`):**
     - `0x004d3941`: `movsd xmm0, QWORD PTR [edi+0xd8]` ($|dz|$) ve `0x004d3949`: `movsd xmm2, QWORD PTR [edi+0xb0]` ($\alpha$).
     - `0x004d3955`–`0x004d395e`: `comisd xmm0, QWORD PTR [esp+0x20]` (`0.0`) ve `jb 0x4d398d`. Standart hesaplamada $|dz| \ge 0.0$ olduğundan `jb` dallanması alınmaz ve `0x004d3960` adresine devam edilir.
     - `0x004d3960`–`0x004d397a`:
       ```assembly
       cmp    BYTE PTR [esp+0x1f], 0x0      ; [edi+0x2a9] == 0 (Two-tailed mi?)
       movsd  xmm1, QWORD PTR ds:0x5c19a0   ; xmm1 = 1.0 (0x3ff0000000000000)
       sete   al                            ; Two-tailed ise al = 1, One-tailed ise al = 0
       movd   xmm0, eax
       cvtdq2pd xmm0, xmm0                  ; xmm0 = 1.0 (Two-tailed) veya 0.0 (One-tailed)
       addsd  xmm0, xmm1                    ; xmm0 = k = 2.0 (Two-tailed) veya 1.0 (One-tailed)
       divsd  xmm2, xmm0                    ; xmm2 = alpha / k
       subsd  xmm1, xmm2                    ; xmm1 = p = 1.0 - (alpha / k)
       ```
     - (Eğer içsel bir çağrıda $dz < 0$ gelirse `0x004d398d` bloğu $p = \alpha / k$ değerini `1.0`'dan çıkarmadan doğrudan kullanır).
  4. **Merkezi Student $t$ Ters CDF (`0x004fb8c0` -> `0x004514f0`) Çağrısı:**
     - `0x004d39bd`: `call DWORD PTR [eax+0x8]` (`0x004fb8c0`) çağrılır.
     - `0x004fb8c0` içinde `0x004fb909` (`subsd xmm0, xmm4`) ile tamamlayıcı olasılık $q = 1.0 - p = \alpha / k$ hesaplanır, `[ebp-0xa0] = 2` (`which = 2`, yani $(p, q, df)$ verildiğinde $t$ sınırını bul) atanır, $|\delta| < 10^{-100}$ (`0x005c3f38` = `1e-100`) koşulu sağlandığı için `0x004fb981` adresinde `call 0x004514f0` (`cdft`) çağrılır:
       $$t_{\text{crit}} = F_{t, df}^{-1}\!\left(1 - \frac{\alpha}{k}\right), \quad k = \begin{cases} 1, & \text{Tek kuyruk (One-tailed)} \\ 2, & \text{Çift kuyruk (Two-tailed)} \end{cases}$$
     - `0x004d39c1`: `fstp QWORD PTR [edi+0x98]` buyruğuyla sonuç `[this+0x98]` (`expected_critical_t`) alanına kaydedilir.
- **`[AJAN]`** **$\alpha > 0.5$ Uç Durumunda Negatif `Critical t` Davranışı:** Tek kuyruklu testte $\alpha > 0.5$ verildiğinde (örneğin `paired_27` vektöründe $\alpha = 0.7$, $dz = 0.3$, $\text{power} = 0.85 \implies N = 4, df = 3$), formül $p = 1 - \alpha = 0.3 < 0.5$ ürettiği için merkezi $t$ dağılımının medyanı ($0$) altında kalan kantil hesaplanır ve `Critical t` negatif çıkar ($F_{t,3}^{-1}(0.3) = -0.5843897$).

---

## 4. Kritik Davranış 2: Noncentrality Parameter ($\delta = dz \cdot \sqrt{N}$) İkili Düzeydeki Karşılığı

- **`[REA]`** İkili dosyada $\delta$ hesabını gerçekleştiren iki eşdeğer sanal metod bulunmaktadır:
  1. **Birincil $\delta$ Metodu — `0x004dc1b0` (`vtable[+0x128]`, indeks 74):**
     - **Çağrıldığı Yerler:** A-priori modunda çıktı kaydı (`0x004dc407`: `call DWORD PTR [eax+0x128]`; `0x004dc40d`: `fstp QWORD PTR [esi+0x90]`) ve Post-hoc modunda çıktı kaydı (`0x004dc973`: `call DWORD PTR [eax+0x128]`; `0x004dc979`: `fstp QWORD PTR [esi+0x90]`).
     - **Makine Buyrukları (`0x004dc1b0`–`0x004dc227`):**
       ```assembly
       4dc1bc: mov    eax, DWORD PTR [esi+0x35c]      ; eax = 0
       4dc1c2: movsd  xmm3, QWORD PTR [eax*8+0x6096a8]; xmm3 = 1.0 (0x006096a8[0])
       4dc1cb: mov    eax, DWORD PTR [esi+0x360]      ; eax = -1 (sonlu anakütle kapalı)
       4dc1d1: test   eax, eax
       4dc1d3: jle    0x4dc1f9                        ; eax <= 0 olduğundan doğrudan 0x4dc1f9'a atlar
       ...
       4dc1f9: mulsd  xmm3, QWORD PTR [ebp+0x8]       ; xmm3 = 1.0 * N
       4dc1fe: xorps  xmm1, xmm1                      ; xmm1 = 0.0
       4dc201: movaps xmm0, xmm3                      ; xmm0 = N
       4dc204: ucomisd xmm1, xmm0                     ; 0.0 ile N karşılaştırması
       4dc208: ja     0x4dc210                        ; N < 0 ise _libm_sse2_sqrt_precise
       4dc20a: sqrtsd xmm0, xmm0                      ; Donanımsal SSE2 karekök: xmm0 = sqrt(N)
       4dc20e: jmp    0x4dc215
       4dc210: call   0x5ac01d                        ; __libm_sse2_sqrt_precise yedek çağrısı
       4dc215: mulsd  xmm0, QWORD PTR [esi+0xd8]      ; xmm0 = sqrt(N) * |dz|
       4dc21d: movsd  QWORD PTR [ebp+0x8], xmm0
       4dc222: fld    QWORD PTR [ebp+0x8]             ; st(0) = delta
       ```
  2. **Güç Hesabı İçi $\delta$ Yardımcı Metodu — `0x004dbdc0` (`vtable[+0x050]`, indeks 20):**
     - **Çağrıldığı Yer:** `0x004d38b0` içinde `Critical t` hesaplandıktan hemen sonra (`0x004d39e4`: `call DWORD PTR [eax+0x50]`) çağrılır ve dönen değer `0x004d39ef` (`call DWORD PTR [esi+0x2c]` -> `0x0043e520`) ile `TDistribution` nesnesine atanır.
     - **Makine Buyrukları (`0x004dbdc0`–`0x004dbe40`):**
       - `0x004bdee0` sarmalayıcısı `0x004bdef6` (`mulsd xmm0, QWORD PTR ds:0x5c29a8` [`0.5`]) ile `[this+0xc0] = 0.5 * N` ve `[this+0xc8] = 0.5 * N` atamalarını önceden yapmıştır.
       - `0x004dbdd1`: `movsd xmm3, QWORD PTR [esi+0xc0]` ve `0x004dbdd9`: `addsd xmm3, QWORD PTR [esi+0xc8]` ile $N = N_1 + N_2 = 0.5 N + 0.5 N = N$ toplamını elde eder.
       - `0x004dbe12`: `mulsd xmm2, xmm3` ($1.0 \cdot N$), `0x004dbe23`: `sqrtsd xmm0, xmm0` ($\sqrt{N}$) ve `0x004dbe2e`: `mulsd xmm0, QWORD PTR [ebp+0x8]` ($\sqrt{N} \cdot |dz|$) buyruklarıyla aynı IEEE-754 çift duyarlıklı ($\text{binary64}$) işlemi yürütür:
         $$\delta = \text{sqrtsd}(N) \times |dz|$$
- **`[DOK]`** G\*Power 3 makalesinde (Faul et al., 2007, s. 182) eşleştirilmiş örneklem $t$-testi için merkezilikten uzaklık parametresi $\delta = d_z \sqrt{N}$ olarak tanımlanmıştır.

---

## 5. Post-Hoc Güç (`Actual power` / `Power (1-β err prob)`) Hesaplama Rutini

- **`[REA]`** **Çağrı Zinciri:** `0x004dc2a0` (Case 3: `0x004dc67c`) $\rightarrow$ `0x004dc98b` (`call DWORD PTR [eax+0x30]` = `0x004bdee0`) $\rightarrow$ `0x004bdf25` (`call DWORD PTR [eax+0x34]` = `0x004d38b0`).
- **`[REA]`** **Kuyruk Sayısına Göre Güç Formülü (`0x004d39f2`–`0x004d3a7f`):**
  - `0x004d39f2`: `cmp BYTE PTR [edi+0x2a9], 0x0` ve `0x004d39f9`: `je 0x4d3a32` ile tek/çift kuyruk ayrımı yapılır:
  1. **Tek Kuyruklu Test (`[this+0x2a9] == 1`, `0x004d39fb`–`0x004d3a30`):**
     - $|dz| \ge 0$ (`0x004d3a15`: `jae 0x4d3a24`) için `0x004d3a24` adresinde `TDistribution::Cdf` (`[[edi+0x58]]+0x04` = `0x004fa7e0`) fonksiyonu $x = t_{\text{crit}}$ (`[edi+0x98]`) argümanıyla çağrılır, ardından `0x004d3a26` (`fld1`) ve `0x004d3a28` (`fsubrp st(1), st`) buyruklarıyla `1.0`'dan çıkarılır:
       $$\text{Power}_{1\text{-kuyruk}} = 1.0 - F_{t, df, \delta}(t_{\text{crit}})$$
  2. **Çift Kuyruklu Test (`[this+0x2a9] == 0`, `0x004d3a32`–`0x004d3a72`):**
     - `0x004d3a44`: `call DWORD PTR [eax+0x4]` (`0x004fa7e0`) ile üst kritik sınırda merkezi olmayan $t$ CDF değeri $P_1 = F_{t, df, \delta}(+t_{\text{crit}})$ hesaplanır ve `[esp+0x20]` (`0x004d3a5b`) adresine saklanır.
     - `0x004d3a4f`–`0x004d3a54`: `movsd xmm0, QWORD PTR [edi+0x98]; xorps xmm0, XMMWORD PTR ds:0x5c3cf0` — `.rdata` `0x005c3cf0` adresindeki işaret biti maskesi (`0x8000000000000000`, `-0.0`) ile XOR yapılarak $-t_{\text{crit}}$ elde edilir.
     - `0x004d3a69`: `call DWORD PTR [eax+0x4]` (`0x004fa7e0`) ile alt kritik sınırda merkezi olmayan $t$ CDF değeri $P_2 = F_{t, df, \delta}(-t_{\text{crit}})$ hesaplanır.
     - `0x004d3a6b`: `fsubr QWORD PTR [esp+0x18]` ile $\beta = P_1 - P_2 = F_{t, df, \delta}(+t_{\text{crit}}) - F_{t, df, \delta}(-t_{\text{crit}})$ hesaplanır.
     - `0x004d3a70`–`0x004d3a72`: `fld1; fsubrp st(1), st` buyruklarıyla `1.0`'dan çıkarılır:
       $$\text{Power}_{2\text{-kuyruk}} = 1.0 - \left(F_{t, df, \delta}(+t_{\text{crit}}) - F_{t, df, \delta}(-t_{\text{crit}})\right)$$
- **`[REA]`** **Merkezi Olmayan $t$ CDF Alt Rutini (`0x004fa7e0` $\rightarrow$ `0x004f9fa0`):**
  - `0x004fa83d` adresinde $|\delta| < 10^{-100}$ (`0x005c3f38`) ise merkezi $t$ CDF (`0x004514f0`), $|\delta| \ge 10^{-100}$ ise `0x004f9fa0` çağrılır.
  - `0x004f9fa0` (`ann_disasm_4f9900.txt` satır 467–785), $df > 10^7$ (`0x005cd220` = `10000000.0` @ `0x004fa014`) olduğunda normal yaklaşıklama (`0x004fa170`), $df \le 10^7$ olduğunda ise Lenth (1989) / Benton & Krishnamoorthy eksik beta (incomplete beta `0x00455120` / gamma `0x004551d0`) seri açılımını (`0x004fa290`) kullanır. Seri yakınsama toleransı `1e-12` (`0x005cd1f8` @ `0x004fa422`) ve maksimum terim sayısı `5000` (`0x1388` @ `0x004fa63a`) olarak kodlanmıştır.

---

## 6. Kritik Davranış 3: A-Priori Modunda $N$ Kök Bulma Algoritması, Tolerans, Döngü Sınırları ve `ceil` Yuvarlama Kuralı

### 6.1. Hedef Fonksiyon ($f(N) = 0$)
- **`[REA]`** **Fonksiyon Adresleri:** `0x00496aa0` (`vtable[+0x048]`, indeks 18) $\rightarrow$ `0x00496830` (`vtable[+0x004]`, indeks 1) $\rightarrow$ `0x004968d0` (`vtable[+0x11c]`, indeks 71).
- **`[REA]`** `0x004968d0` rutini, aday örneklem büyüklüğü $N$ (sürekli/reel `double` olarak) için `vtable[+0x030]` (`0x004bdee0`) üzerinden $\text{Power}(|dz|, \alpha, N)$ değerini hesaplar ve `0x00496904` (`fsub QWORD PTR [esi+0xb8]`) buyruğuyla hedef gücü (`power_input`) çıkarır:
  $$f(N) = \text{Power}(|dz|, \alpha, N) - \text{power}_{\text{input}}$$

### 6.2. Başlangıç Aralığı Belirleme (Bracketing — `0x0049a210` ve `0x004962d0`)
- **`[REA]`** `0x00496aa0` içinde `0x00496ae0` (`call DWORD PTR [eax+0x64]`) buyruğu `0x0049a210` metodunu çağırır.
- **`[REA]`** `0x0049a210`, `.rdata` `0x005c6f00` adresindeki 16 baytlık çift `double` sabiti `(2.0, 100.0)` (`x_min = 2.0`, `x_init = 100.0`) yükleyerek `0x004962d0` rutinini çağırır:
  1. İlk olarak $x_{\text{init}} = 100.0$ noktasında $f(100.0)$ hesaplanır (`0x004962ee`).
  2. **Durum A — $f(100.0) < 0.0$ (`0x00496303`–`0x00496377`, aranan $N > 100.0$):**
     - $x_{\text{low}} = \text{[esi+0x68]} = 100.0$ atanır.
     - $x_{\text{high}} = \text{[esi+0x70]} = 100.0 \times 1.6 = 160.0$ (`mulsd xmm0, QWORD PTR ds:0x5c4ad8`, `0x005c4ad8` = `1.6` / `0x3ff999999999999a`) atanır.
     - $f(x_{\text{high}}) < 0.0$ olduğu sürece (`0x00496340`–`0x00496375` döngüsü):
       $$x_{\text{low}} \leftarrow x_{\text{high}}, \quad x_{\text{high}} \leftarrow 1.6 \cdot x_{\text{high}}$$
       adımlarıyla üst sınır geometrik olarak genişletilir.
  3. **Durum B — $f(100.0) \ge 0.0$ (`0x0049638f`–`0x00496407`, aranan $N \le 100.0$):**
     - $x_{\text{high}} = \text{[esi+0x70]} = 100.0$ ve $x_{\text{low}} = \text{[esi+0x68]} = 0.5 \cdot (2.0 + 100.0) = 51.0$ (`mulsd xmm0, QWORD PTR ds:0x5c29a8` = `0.5`) atanır.
     - $x_{\text{low}} \ge 2.0$ ve $f(x_{\text{low}}) > 0.0$ olduğu sürece (`0x004963b8`–`0x00496405` döngüsü):
       $$x_{\text{high}} \leftarrow x_{\text{low}}, \quad x_{\text{low}} \leftarrow 0.5 \cdot (x_{\text{low}} + 2.0) - 2.0$$
       adımıyla alt sınır $2.0$'a doğru daraltılır ve `0x0049637c`–`0x00496383` adresinde $x_{\text{low}} = \max(x_{\text{low}}, 2.0)$ olarak sınırlandırılır.

### 6.3. Kök Bulma Algoritması: Brent Yöntemi (`0x004f9bb0`), Tolerans ve Döngü Sınırları
- **`[REA]`** **Çağrı Noktası (`0x00496ae3`–`0x00496b03`):**
  ```assembly
  496ae3: movsd  xmm0, QWORD PTR ds:0x5c3f48   ; tol = 1e-10 (0x3ddb7cdfd9d7bdbb)
  496aeb: lea    ecx, [esp+0x14]               ; Brent çözücü nesnesi
  496aed: push   0x12c                         ; max_iter = 300 (0x12c)
  496af2: sub    esp, 0x18
  496af5: movsd  QWORD PTR [esp+0x10], xmm0    ; arg4: tol = 1e-10
  496afb: movsd  xmm0, QWORD PTR [esi+0x70]
  496b00: movsd  QWORD PTR [esp+0x8], xmm0     ; arg3: x_high = [this+0x70]
  496b06: movsd  xmm0, QWORD PTR [esi+0x68]
  496b0b: movsd  QWORD PTR [esp], xmm0         ; arg2: x_low  = [this+0x68]
  496b10: push   esi                           ; arg1: callback_obj = this
  496b11: call   0x4f9bb0                      ; Brent kök bulucu
  ```
- **`[REA]`** **Algoritma Kimliği (`0x004f9bb0` — Brent's Method / `zbrent`):**
  - `0x004f9bb0` (`ann_disasm_4f9900.txt` satır 214–461) fonksiyonu; ikiye bölme (bisection), kiriş (secant) ve ters kuadratik interpolasyon (inverse quadratic interpolation — IQI) yöntemlerini birleştiren klasik **Brent kök bulma algoritmasıdır**:
  - **Parametre ve Sabitler:**
    - **Çağrı toleransı (`tol`):** `1e-10` (`.rdata` `0x005c3f48`, IEEE-754 `0x3ddb7cdfd9d7bdbb`), çözücü nesnesinin `[solver+0x08]` alanına kaydedilir (`0x004f9c33`).
    - **Makine epsilonu (`EPS`):** `1.1102230246251565e-16` ($2^{-53}$, `.rdata` `0x005c4390`, IEEE-754 `0x3ca0000000000000`), `0x004f9c9d` adresinde `[esp+0x60]` yerel değişkenine yüklenir.
    - **Maksimum döngü sınırı (`max_iter`):** `300` (`0x12c`), `[solver+0x50]` alanına kaydedilir (`0x004f9c2b`). Döngü sayacı `edi`, `0x004f9f37` (`inc edi; cmp edi, DWORD PTR [esi+0x50]; jge 0x4f9f7f`) buyruklarıyla denetlenir; 300 iterasyon aşılırsa `[solver+0x54] = 2` hata kodu atanır.
  - **Kök Kuşatma Ön Kontrolü (`0x004f9c3b`–`0x004f9c5c`):**
    - $f(x_{\text{low}}) \cdot f(x_{\text{high}}) > 0.0$ ise (`mulsd xmm0, xmm4; comisd xmm0, xmm3 [0.0]; jbe 0x4f9c6f`), kök aralıkta kuşatılmamıştır: `[solver+0x54] = 1` atanır ve `0.0` (`fldz` @ `0x004f9c63`) döndürülür.
  - **İterasyon İçi Durma Kriteri (`0x004f9d7d`–`0x004f9db1`):**
    - Her iterasyonda $|f(c)| < |f(b)|$ ise $a, b, c$ noktaları takas edilir (`0x004f9d33`–`0x004f9d7b`), böylece $b = \text{[solver+0x18]}$ her zaman en iyi kök tahminini tutar.
    - `0x004f9d81`–`0x004f9d98`: Etkin tolerans $\text{tol}_1 = \text{EPS} \cdot |b|$ (`mulsd xmm7, QWORD PTR [esp+0x60]`) ve yarı aralık adımı $x_m = 0.5 \cdot (c - b)$ (`mulsd xmm5, QWORD PTR ds:0x5c29a8`) hesaplanır.
    - `0x004f9da0`–`0x004f9db1`: $|x_m| \le \text{tol}_1$ (`comisd xmm7, xmm0; jae 0x4f9f73`) **veya** $f(b) = 0.0$ (`ucomisd xmm2, xmm3; jnp 0x4f9f73`) olduğunda döngü sonlanır ve sürekli kök $N_{\text{cont}} = b$ döndürülür (`0x004f9f73`: `fld QWORD PTR [esi+0x18]`).
  - **İnterpolasyon / Bisection Seçimi (`0x004f9db3`–`0x004f9ee2`):**
    - $|e| \ge \text{tol}_1$ ve $|f(b)| < |f(a)|$ ise:
      - $a == c$ olduğunda (`0x004f9e0b`) **Secant (Kiriş)** adımı ($s = f(b)/f(a)$, $p = 2 \cdot x_m \cdot s$, $q = 1 - s$),
      - $a \ne c$ olduğunda (`0x004f9e17`) **Inverse Quadratic Interpolation (Ters Kuadratik İnterpolasyon)** adımı ($q = f(a)/f(c)$, $r = f(b)/f(c)$, $s = f(b)/f(a)$) hesaplanır.
    - Kabul koşulu $2|p| < \min(3 \cdot x_m \cdot q - |\text{tol}_1 \cdot q|, |e \cdot q|)$ (`0x004f9e79`–`0x004f9eb3`) sağlanırsa $d = p / q$ (`divsd xmm1, xmm0` @ `0x004f9eb8`), sağlanmazsa **Bisection (İkiye Bölme)** adımı $d = e = x_m$ (`0x004f9ecb` / `0x004f9ede`) uygulanır.
- **`[DOK]`** Press et al., *Numerical Recipes in C*, Bölüm 9.3 (Van Wijngaarden–Dekker–Brent Method / `zbrent`).

### 6.4. $N$'nin Tam Sayıya Yuvarlanma Kuralı (İki Aşamalı `Snap-to-1e-10` + `ceil` — `0x00496a20`)
- **`[REA]`** **Fonksiyon Adresi:** `0x00496a20` (`PowerAnalysis::vtable[+0x074]`, indeks 29). `0x00496aa0` içinden `0x00496b30` ve `0x00496b62` adreslerinde çağrılır.
- **`[REA]`** **Makine Buyrukları (`0x00496a20`–`0x00496a9d`):**
  ```assembly
  496a2c: movsd  xmm0, QWORD PTR [ebp+0x8]       ; xmm0 = N_cont (sürekli kök)
  496a31: divsd  xmm0, QWORD PTR [esi+0xa8]      ; xmm0 = N_cont / [this+0xa8] (1.0000000000000009)
  496a39: mulsd  xmm0, QWORD PTR ds:0x5c4328     ; xmm0 = xmm0 * 10000000000.0 (1e10, 0x4202a05f20000000)
  496a41: addsd  xmm0, QWORD PTR ds:0x5c29a8     ; xmm0 = xmm0 + 0.5 (0x3fe0000000000000)
  496a53: call   0x5ac023                        ; floor(xmm0) -> _libm_sse2_floor_precise
  496a67: call   DWORD PTR ds:0x5be5a8           ; modf(floor_val, &intpart) -> MSVCR90.modf
  496a6f: movsd  xmm0, QWORD PTR [ebp-0x8]       ; xmm0 = intpart
  496a74: divsd  xmm0, QWORD PTR ds:0x5c4328     ; xmm0 = intpart / 10000000000.0 (1e10)
  496a8d: call   0x5ac047                        ; ceil(xmm0) -> _libm_sse2_ceil_precise
  496a92: mulsd  xmm0, QWORD PTR [esi+0xa8]      ; xmm0 = ceil_val * [this+0xa8]
  ```
  Ardından `0x004dc404` adresinde `cvttsd2si eax, xmm0` ile 32-bit işaretli tam sayıya (`int32`) dönüştürülür.
- **`[REA]`** **Matematiksel Karşılığı:** G\*Power, kayan nokta kök bulucudan dönen $N_{\text{cont}}$ değerini doğrudan `ceil(N_cont)` fonksiyonuna sokmaz! Örneğin gerçek kök tam olarak $N = 34.0$ iken sayısal hata nedeniyle $N_{\text{cont}} = 34.00000000001$ dönerse yanlışlıkla $35$'e yuvarlanmasını önlemek için önce **$10^{-10}$ basamağına en yakın yuvarlama (round-to-nearest $10^{-10}$)** uygular, ardından **`ceil` (yukarı yuvarlama)** alır:
  $$N_{\text{snap}} = \frac{\lfloor N_{\text{cont}} \cdot 10^{10} + 0.5 \rfloor}{10^{10}}, \qquad N_{\text{total}} = \lceil N_{\text{snap}} \rceil$$
- **`[REA]`** **Tam Sayı $N_{\text{total}}$ Üzerinden Çıktıların Yeniden Hesaplanması (`0x00496b6a`–`0x00496b9f` ve `0x004dc404`–`0x004dc42e`):**
  - `0x00496b6a`: Yuvarlanmış tam sayı $N_{\text{total}}$ (`[esi+0xe8]`) ile `vtable[+0x030]` (`0x004bdee0` $\rightarrow$ `0x004d38b0`) yeniden çağrılır!
  - Bu çağrı sonucunda:
    - `df` (`[this+0x80]`) = $N_{\text{total}} - 1$
    - `Critical t` (`[this+0x98]`) = $F_{t, N_{\text{total}}-1}^{-1}(1 - \alpha/k)$
    - `Noncentrality parameter` $\delta$ (`[this+0x90]`) = $|dz| \cdot \sqrt{N_{\text{total}}}$ (`0x004dc407` adresinde `vtable[+0x128]` = `0x004dc1b0` ile güncellenir)
    - `Actual power` (`[this+0x108]`) = $\text{Power}(|dz|, \alpha, N_{\text{total}}) \ge \text{power}_{\text{input}}$ (`0x00496b9f` ve `0x004dc42e` adreslerinde kaydedilir).

---

## 7. Kritik Davranış 4: Uç Değerlerdeki (Edge Cases) Davranışlar ve Girdi Doğrulama Sınırları

### 7.1. $\alpha$ ve $\text{Power}$ ($1-\beta$) Kabul Sınırları
- **`[REA]`** **$\alpha$ Doğrulama Rutini (`0x00487530`):**
  - `.rdata` `0x005c4398` (`1e-07`, `0x3e7ad7f29abcaf48`) ve `0x005c6860` (`0.9999999`, `0x3feffffde7210be9`) sabitleriyle kapalı aralığı denetler:
    $$\alpha \in [10^{-7},\; 0.9999999]$$
  - Aralık dışında hata dizesi (`0x005c6100`): `"Alpha is outside the admissible range (1e-07, 0.9999999)."`
- **`[REA]`** **$\text{Power}$ ($1-\beta$) Doğrulama Rutini (`0x00488110`):**
  - Aynı sınır sabitlerini (`0x005c4398` = `1e-07`, `0x005c6860` = `0.9999999`) kullanır:
    $$\text{power}_{\text{input}} \in [10^{-7},\; 0.9999999]$$
  - Aralık dışında hata dizesi (`0x005c60d8`): `"Power is outside the admissible range (1e-07, 0.9999999)."`

### 7.2. $\text{power} = \alpha$ ve $\text{power} < \alpha$ Uç Durumu (A-Priori)
- **`[REA]`** **Karşılaştırma Rutini (`0x004880e0`, A-priori modunda `0x004dc363` adresinden çağrılır):**
  - `0x004880e0`: `movsd xmm0, QWORD PTR [esp+0xc]` ($\text{power}$); `comisd xmm0, QWORD PTR [esp+0x4]` ($\alpha$); `jb 0x4880f3`.
  - **$\text{power} < \alpha$ durumu:** `jb` dallanması alınır ve `.rdata` `0x005c6220` adresindeki `"Power must be greater than or equal to alpha."` hatası döndürülür (`eax = 0`).
  - **$\text{power} = \alpha$ uç durumu:** `jb` dallanması **alınmaz**, doğrulama başarılı olur (`mov al, 0x1; ret` @ `0x004880ee`)!
  - **$\text{power} = \alpha$ olduğunda çözücü davranışı (`0x004962d0` + `0x004f9bb0` + `0x00496b38`):**
    - Herhangi bir $|dz| > 0$ ve $N \ge 2$ için $\text{Power}(|dz|, \alpha, N) > \alpha = \text{power}_{\text{input}}$ olduğundan $f(N) > 0$'dır.
    - `0x004962d0` alt sınırı $x_{\text{low}} = 2.0$ (`[esi+0x68]`) değerine indirir.
    - $f(x_{\text{low}}) > 0$ ve $f(x_{\text{high}}) > 0$ aynı işaretli olduğundan Brent çözücüsü (`0x004f9bb0`) `0x004f9c5c` adresinde `[solver+0x54] = 1` bayrağını set edip `0.0` döndürür.
    - `0x00496b38`–`0x00496b4b` adresindeki alt sınır kenetleme (clamping) bloğu:
      ```assembly
      496b38: movsd  xmm0, QWORD PTR [esi+0x68]   ; xmm0 = x_low = 2.0
      496b3d: movsd  xmm1, QWORD PTR [esi+0xe8]   ; xmm1 = 0.0
      496b45: comisd xmm0, xmm1                   ; 2.0 > 0.0
      496b49: jbe    0x496b6a
      496b4b: movsd  QWORD PTR [esi+0xe8], xmm0   ; [this+0xe8] = 2.0
      ```
      ile örneklem büyüklüğünü minimum geçerli sınır olan **$N_{\text{total}} = 2$** ($df = 1$) değerine kenetler ve $N = 2$ için `Actual power`, `Critical t` ve $\delta = |dz| \cdot \sqrt{2}$ değerlerini hesaplar!

### 7.3. Etki Büyüklüğü ($dz$) Çok Küçük / Çok Büyük / Negatif Uç Durumları
- **`[REA]`** **$dz$ Doğrulama Rutini (`0x004db990`, `vtable[+0x104]`, indeks 65):**
  - `0x004db990`: `cmp DWORD PTR [esp+0x4], 0x0; jne 0x4db9f5` — İlk argüman analiz modudur (`0` = A-priori, `3` = Post-hoc).
  1. **A-Priori Modunda Çok Küçük $|dz|$ Sınırı (`0x004db999`–`0x004db9dc`):**
     - `0x004db99e`–`0x004db9b5`:
       ```assembly
       movsd  xmm1, QWORD PTR [esp+0xc]           ; xmm1 = dz
       movsd  xmm0, QWORD PTR ds:0x5c7ed8         ; xmm0 = 1e-05 (0.00001, 0x3ee4f8b588e368f1)
       andps  xmm1, XMMWORD PTR ds:0x5c1a20       ; xmm1 = |dz|
       comisd xmm0, xmm1                          ; 1e-05 ile |dz| karşılaştırması
       jbe    0x4db9de                            ; 1e-05 <= |dz| ise geçerli!
       ```
     - **Kesin eşitsizlik:** $|dz| < 10^{-5}$ olduğunda `.rdata` `0x005cb24c` + `0x005cb510` dizeleriyle `"In an a priori analysis, the absolute value of the\neffect size be greater than 0.00001."` hatası verilir. $|dz| = 10^{-5}$ (`0.00001`) değeri `jbe` nedeniyle **kabul edilir**.
  2. **Post-Hoc Modunda Çok Küçük $|dz|$ ve $dz = 0$ Davranışı (`0x004db997`):**
     - Post-hoc modunda (`mode == 3`), `jne 0x4db9f5` dallanmasıyla $10^{-5}$ alt sınır kontrolü **atlanır**!
     - Dolayısıyla Post-hoc modunda $|dz| < 10^{-5}$ ve hatta $dz = 0.0$ geçerlidir. $dz \to 0$ iken $\delta = |dz|\sqrt{N} \to 0$ olur ve `Actual power` değeri $\alpha$'ya yakınsar (ör. `paired_28`: $dz = 0.001, N = 10, \alpha = 0.05 \implies \delta = 0.0031623, \text{Power} = 0.0500825$).
  3. **Çok Büyük $|dz|$ Sınırı (`0x004db9de` / `0x004db9f5` $\rightarrow$ `0x00487b70`):**
     - Hem A-priori hem Post-hoc modlarında `.rdata` `0x005cb4b0` adresindeki `XMMWORD` `(-20.0, 20.0)` sınır çifti yüklenerek `0x00487b70` çağrılır:
       $$dz \in [-20.0,\; +20.0]$$
     - $|dz| > 20.0$ olduğunda `.rdata` `0x005c61b4` + `0x005c61d8` dizeleriyle `"Effect size dz is outside the admissible range (-20, 20)."` hatası döndürülür.
     - $dz$ çok büyük olduğunda (ör. `paired_29`: $dz = 2.0$, A-priori $\implies N = 4$, `Actual power` = `0.8035827`; veya Post-hoc $dz = 5.0, N = 50 \implies \delta = 35.355339$), A-priori modunda kök $N$ hızla alt sınıra ($N = 2, 3, 4$) yaklaşır; Post-hoc modunda ise $F_{t, df, \delta}(t_{\text{crit}}) \to 0$ olduğundan `Actual power` IEEE-754 çift duyarlılıkta `1.0000000` değerine doygunluğa ulaşır (saturate olur).
  4. **Negatif $dz$ Simetrisi (`0x004dc3cb` ve `0x004dc7c8`):**
     - `dz` $[-20.0, 0)$ aralığında negatif girildiğinde, hesaplama öncesi `andps xmm0, XMMWORD PTR ds:0x5c1a20` (`fabs`) uygulandığından tüm çıktılar ($\delta \ge 0$, `Critical t`, `df`, `N`, `Actual power`) pozitif $|dz|$ ile birebir aynıdır.

### 7.4. Örneklem Büyüklüğü ($N$) Alt ve Üst Sınırları
- **`[REA]`** **A-Priori Çıktı $N$ Doğrulaması (`0x004dc404` $\rightarrow$ `0x004d9310` `vtable[+0x0fc]` $\rightarrow$ `0x00488a10`):**
  - `0x004d9310` fonksiyonu `0x00488a10(N, 2, 0x7ffffffe)` çağrısı yapar:
    $$N_{\text{a-priori}} \in [2,\; 2147483646]$$
  - Çok küçük $|dz|$ değerlerinde hesaplanan $N > 2147483646$ olursa (veya `cvttsd2si` taşmasıyla `0x80000000` = `-2147483648` üretirse), `"Total sample size is outside the admissible range (2, 2147483646)."` (`0x005c6524`) hatası verilir.
- **`[REA]`** **Post-Hoc Girdi $N$ Doğrulaması (`0x004dc735` $\rightarrow$ `0x00488a10`):**
  - Post-hoc modunda `0x004dc735` adresinde `push 0x7ffffffe; push 0x3; push edi; call 0x00488a10` buyruklarıyla alt sınır `3` olarak denetlenir:
    $$N_{\text{post-hoc}} \in [3,\; 2147483646]$$
  - $N < 3$ veya $N > 2147483646$ girildiğinde `"Total sample size is outside the admissible range (3, 2147483646)."` hatası döndürülür.

---

## 8. Özet Fonksiyon ve Sabit Referans Tablosu (`[REA]`)

| Sembol / Kavram | Sanal Adres (VA) | Vtable / Ofset | Açıklama ve İkili Kanıt |
| :--- | :--- | :--- | :--- |
| `PowerTPairedMean::vtable` | `0x005cac60` | Dosya: `0x1c9c60` | 75 girişli sanal metod tablosu (`COL = 0x005ef6a0`, `TD = 0x0060ce88`) |
| `PowerTOneMean::vtable` | `0x005ca8d0` | Dosya: `0x1c98d0` | Doğrudan üst sınıf vtable (`COL = 0x005ef5a4`, `TD = 0x0060ce28`) |
| `TDistribution::vtable` | `0x005c4a20` | Dosya: `0x1c3a20` | Student $t$ dağılım sınıfı vtable (`COL = 0x005ee558`, `TD = 0x0060c7b4`) |
| `Calculate / Dispatch` | `0x004dc2a0` | `vtable[+0x008]` | A-priori (`case 0` @ `0x004dc2d1`) ve Post-hoc (`case 3` @ `0x004dc67c`) ana giriş |
| `CalcDf` ($df = N - 1$) | `0x004db950` | `vtable[+0x124]` | `mulsd xmm0, [ecx+0xe8]; subsd xmm0, ds:0x5c19a0 (1.0)` |
| `CalcNcp` ($\delta = dz\sqrt{N}$) | `0x004dc1b0` | `vtable[+0x128]` | `sqrtsd xmm0, xmm0; mulsd xmm0, [esi+0xd8]` |
| `CalcNcpInternal` | `0x004dbdc0` | `vtable[+0x050]` | `addsd xmm3, [esi+0xc8]; sqrtsd xmm0, xmm0; mulsd xmm0, [ebp+0x8]` |
| `PowerWrapper` | `0x004bdee0` | `vtable[+0x030]` | $N_1 = N_2 = 0.5 \cdot N$ atar ve `0x004d38b0` fonksiyonunu çağırır |
| `PowerTCore` (`Critical t` & `Power`) | `0x004d38b0` | `vtable[+0x034]` | $t_{\text{crit}} = F_{t,df}^{-1}(1-\alpha/k)$ ve merkezi olmayan $t$ CDF ile güç hesabı |
| `SolveSampleSizeAPriori` | `0x00496aa0` | `vtable[+0x048]` | A-priori $N$ çözücüsü (`0x0049a210` $\rightarrow$ `0x004f9bb0` $\rightarrow$ `0x00496a20`) |
| `ObjectiveFuncAPriori` | `0x004968d0` | `vtable[+0x11c]` | $f(N) = \text{Power}(|dz|, \alpha, N) - \text{power}_{\text{input}}$ |
| `InitBracketPaired` | `0x0049a210` | `vtable[+0x064]` | `0x005c6f00` `(2.0, 100.0)` yükler ve `0x004962d0` çağırır |
| `BracketSearch` | `0x004962d0` | — | $100.0$'dan yukarı $\times 1.6$ (`0x005c4ad8`) veya aşağı $2.0$'a doğru daraltma |
| `BrentSolver` (`zbrent`) | `0x004f9bb0` | — | Brent kök bulucu (`tol = 1e-10` @ `0x005c3f48`, `EPS = 2^-53` @ `0x005c4390`, `max_iter = 300`) |
| `RoundSampleSize` | `0x00496a20` | `vtable[+0x074]` | $\lceil \lfloor N \cdot 10^{10} + 0.5 \rfloor / 10^{10} \rceil$ (`1e10` @ `0x005c4328`) |
| `TDistribution::Cdf` | `0x004fa7e0` | `dist_vt[+0x04]` | $\|\delta\| < 10^{-100}$ ise `0x004514f0`, değilse `0x004f9fa0` (noncentral $t$ CDF) |
| `TDistribution::Quantile` | `0x004fb8c0` | `dist_vt[+0x08]` | $\|\delta\| < 10^{-100}$ ise `0x004514f0` (`cdft` `which=2`) |
| `ValidateEffectSize` | `0x004db990` | `vtable[+0x104]` | A-priori: $\|dz\| \ge 10^{-5}$ (`0x005c7ed8`) ve $dz \in [-20, 20]$ (`0x005cb4b0`) |
| `ValidateAlpha` | `0x00487530` | — | $\alpha \in [10^{-7}, 0.9999999]$ (`0x005c4398`, `0x005c6860`) |
| `ValidatePower` | `0x00488110` | — | $\text{power} \in [10^{-7}, 0.9999999]$ (`0x005c4398`, `0x005c6860`) |
| `ValidatePowerGeAlpha` | `0x004880e0` | — | $\text{power} \ge \alpha$ kontrolü (`comisd power, alpha; jb`) |
