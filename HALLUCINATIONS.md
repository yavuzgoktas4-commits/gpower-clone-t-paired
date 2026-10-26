# Halüsinasyon ve Yanılgı Günlüğü (HALLUCINATIONS) — K2 Ailesi: `t-paired`

Bu belge, tersine mühendislik, spesifikasyon çıkarımı ve temiz oda geliştirme süreçlerinde ajanın ilk aşamada yaptığı hatalı varsayımları (halüsinasyonları), bu yanılgıların nasıl tespit edildiğini ve hangi diferansiyel test vektörleri tarafından yakalanıp düzeltildiğini kayıt altına alır.

---

## Halüsinasyon 1: Doğrudan `ceil(N_cont)` Yuvarlaması ve Sürekli Kökteki Çıktıların Korunması Varsayımı

### 1. İlk (Yanlış) Varsayım
A-priori örneklem büyüklüğü modunda (`--mode a-priori`), kök bulma algoritmasından dönen sürekli/kesirli kök $N_{\text{cont}}$ değerinin doğrudan standart `math.ceil(N_cont)` fonksiyonuyla yukarı yuvarlandığı; ayrıca çıktıdaki `ncp` ($\delta$), `critical_t` ve `actual_power` değerlerinin ya sürekli kök $N_{\text{cont}}$ noktasındaki değerler olduğu ya da doğrudan `ceil(N_cont)` uygulanırken kayan nokta taşmalarına (`floating-point drift`) karşı hiçbir ön işlem yapılmadığı varsayılmıştı.

### 2. Nasıl Fark Edildi ve Hangi Test Yakaladı?
Bu yanılgı iki aşamada yakalandı:
1. **`paired_02` (`dz = 0.5, alpha = 0.05, power = 0.80, tails = 2`) ve `paired_01` (`dz = 0.5, alpha = 0.05, power = 0.95, tails = 1`) diferansiyel testleri:**
   - Sürekli kök $N_{\text{cont}} \approx 33.3672$ noktasında $\text{Power}(N_{\text{cont}}) = 0.8000000$ ve $\delta = 0.5 \times \sqrt{33.3672} = 2.888217$ iken, G\*Power referans çıktısında (`oracle/ground_truth.csv` `paired_02`) `expected_n_total = 34`, `expected_df = 33`, `expected_ncp = 2.9154759` ($= 0.5 \times \sqrt{34}$) ve `expected_actual_power = 0.8077775` yer almaktaydı.
   - Bu fark, G\*Power'ın $N$ tam sayıya yuvarlandıktan sonra `df`, `critical_t`, `ncp` ve `actual_power` değerlerini **yuvarlanmış tam sayı $N_{\text{total}}$ üzerinden yeniden hesapladığını** (`0x00496b6a`) ortaya çıkardı.
2. **Tam sayı sınırına çok yakın kök üreten `paired_10` (`dz = 0.1, alpha = 0.05, power = 0.85, tails = 2 -> N = 900, ncp = 3.0000000`) ve `paired_13` (`dz = 0.5, alpha = 0.10, power = 0.90, tails = 2 -> N = 36, ncp = 3.0000000`) testleri:**
   - İkili dosyadaki `0x00496a20` (`vtable[+0x074]`) yuvarlama rutini söküldüğünde, doğrudan `ceil(N_cont)` çağrılmadığı; önce `.rdata` `0x005c4328` adresindeki `10000000000.0` ($10^{10}$) sabitiyle çarpılıp `0.5` (`0x005c29a8`) eklendiği, `floor` (`0x005ac023`) + `modf` (`0x005be5a8`) alınıp $10^{10}$'a bölündüğü ve **ancak bundan sonra `ceil` (`0x005ac047`) uygulandığı** tespit edildi:
     $$N_{\text{snap}} = \frac{\lfloor N_{\text{cont}} \cdot 10^{10} + 0.5 \rfloor}{10^{10}}, \qquad N_{\text{total}} = \lceil N_{\text{snap}} \rceil$$
   - Eğer bu $10^{-10}$ ızgara kenetlemesi (`snap-to-grid`) yapılmazsa, gerçek kök tam sayı olduğunda (ör. $N = 36.0$) nümerik iterasyondan $36.00000000002$ dönerse saf `math.ceil` bunu hatalı biçimde $37$'ye yuvarlamaktadır.

### 3. Düzeltme
`SPEC.md` ve `src/engine/paired_t.py` içindeki `round_sample_size` fonksiyonu iki aşamalı $\lceil \lfloor N_{\text{cont}} \cdot 10^{10} + 0.5 \rfloor / 10^{10} \rceil$ kuralıyla güncellendi ve `solve_a_priori` sonunda tüm çıktı parametrelerinin tam sayı `n_total` üzerinden yeniden hesaplanması sağlandı.

---

## Halüsinasyon 2: Tek Kuyruklu Testte Kritik $t$ (`critical_t`) Değerinin Her Zaman Pozitif Olduğu Varsayımı

### 1. İlk (Yanlış) Varsayım
İstatistik ders kitaplarındaki standart tablolardan hareketle, G\*Power'ın `Critical t` (`expected_critical_t`) çıktısını her zaman pozitif bir mutlak eşik değeri ($|t_{\text{crit}}| > 0$) olarak raporladığı veya $\alpha$ parametresinin tek kuyruklu testlerde $0.5$'i aşamayacağı varsayılmıştı.

### 2. Nasıl Fark Edildi ve Hangi Test Yakaladı?
- **`oracle/ground_truth.csv` içindeki `paired_27` (`mode = a-priori, tails = 1, dz = 0.3, alpha = 0.7, power_input = 0.85`) sınır testi (`test_ground_truth_csv_vector[paired_27]`):**
  - `paired_27.png` ekran görüntüsünde ve `ground_truth.csv` satırında G\*Power'ın $\alpha = 0.7$ girdi değerini kabul ettiği ve çıktı olarak **negatif bir kritik $t$ değeri (`expected_critical_t = -0.5843897`)** ile `expected_n_total = 4`, `expected_df = 3`, `expected_ncp = 0.6000000`, `expected_actual_power = 0.8665738` ürettiği görüldü.
- **İkili Kanıt Doğrulaması (`0x004d38b0`):**
  - `0x004d3960`–`0x004d3989` adreslerindeki SSE2 buyrukları incelendiğinde, $|dz| \ge 0$ için kuyruk böleni $k = 1.0$ (tek kuyruk) veya $k = 2.0$ (çift kuyruk) hesaplandıktan sonra üst kuyruk kantil olasılığının doğrudan:
    $$p = 1.0 - \frac{\alpha}{k}$$
    olarak merkezi Student-$t$ ters CDF fonksiyonuna (`0x004fb8c0` $\rightarrow$ `0x004514f0`) geçirildiği ve sonuç üzerinde hiçbir `fabs` / mutlak değer işlemi yapılmadığı kanıtlandı.
  - Tek kuyruklu testte ($k = 1$) $\alpha = 0.7 > 0.5$ olduğunda $p = 1.0 - 0.7 = 0.3 < 0.5$ olur ve merkezi $t$ dağılımı $0$ etrafında simetrik olduğundan $F_{t, 3}^{-1}(0.3) = -0.5843897 < 0$ değerini döndürür.

### 3. Düzeltme
`compute_critical_t` fonksiyonunda mutlak değer zorlaması kullanılmayarak doğrudan `scipy.stats.t.ppf(1.0 - alpha / k, df)` formülü korundu; `paired_27` vektörü `-0.5843897` değeriyle $2.74 \times 10^{-8}$ mutlak fark içinde tam eşleşti.

---

## Halüsinasyon 3: $|dz| \ge 10^{-5}$ Alt Sınırının ve $N_{\text{min}} = 2$ Sınırının A-Priori ve Post-Hoc Modlarında Özdeş Olduğu Varsayımı

### 1. İlk (Yanlış) Varsayım
Girdi doğrulama katmanında etki büyüklüğü alt sınırı $|dz| \ge 10^{-5}$ (`0.00001`) kuralının hem A-priori hem de Post-hoc modlarında uygulandığı; buna karşılık toplam örneklem büyüklüğü alt sınırının her iki modda da $N \ge 2$ olduğu varsayılmıştı.

### 2. Nasıl Fark Edildi ve Hangi Test Yakaladı?
- **`0x004db990` (`ValidateEffectSize`) ve `0x004dc735` (Post-hoc $N$ doğrulaması) ikili analizi ile sınır değeri doğrulama testleri:**
  - `0x004db990` fonksiyonunun hemen girişindeki `cmp DWORD PTR [esp+0x4], 0x0; jne 0x4db9f5` buyruğu, `1e-05` (`0x005c7ed8`) alt sınır kontrolünün **yalnızca `mode == 0` (A-priori)** için çalıştığını, Post-hoc (`mode == 3`) modunda ise doğrudan `0x004db9f5` adresine atlanarak yalnızca $dz \in [-20.0, 20.0]$ (`0x005cb4b0`) kontrolünün yapıldığını gösterdi. Nitekim hata mesajı da açıkça `"In an a priori analysis, the absolute value of the effect size be greater than 0.00001."` şeklindedir.
  - Örneklem büyüklüğü $N$ için ise A-priori çıkışında `0x004d9310` fonksiyonu `0x00488a10(N, 2, 0x7ffffffe)` ($N \in [2, 2147483646]$) çağrısı yaparken, Post-hoc girişinde `0x004dc735` adresi `0x00488a10(N, 3, 0x7ffffffe)` ($N \in [3, 2147483646]$) çağrısı yapmaktadır.

### 3. Düzeltme
`SPEC.md`, `CONTRACT.md` ve `src/engine/paired_t.py` (`validate_inputs`) içinde mod ayrımı birebir gerçeklendi:
- A-priori modunda $10^{-5} \le |dz| \le 20.0$ ve çıktı $N \in [2, 2147483646]$,
- Post-hoc modunda $-20.0 \le dz \le 20.0$ (çok küçük $|dz| < 10^{-5}$ dahil) ve girdi $N \in [3, 2147483646]$ kuralları doğrulama testleriyle güvence altına alındı.

---

## Özet Tablo

| # | Yanlış Varsayım (Halüsinasyon) | Yakalayan Test / Vektör | Gerçek G\*Power Davranışı (Kanıt) |
| :-: | :--- | :--- | :--- |
| **1** | Doğrudan `ceil(N_cont)` ve sürekli kökteki $\delta$/güç değerlerinin korunması | `paired_01`, `paired_02`, `paired_10`, `paired_13` (`test_differential.py`) | Önce $10^{-10}$ ızgarasına yuvarlama ($\lfloor N \cdot 10^{10} + 0.5 \rfloor / 10^{10}$), sonra `ceil` (`0x00496a20`) ve tam sayı $N$'de yeniden hesaplama (`0x00496b6a`) |
| **2** | `critical_t` değerinin her zaman pozitif ($>0$) olduğu varsayımı | `paired_27` ($\alpha = 0.7$, tek kuyruk $\implies t_{\text{crit}} = -0.5843897$) | $|dz| \ge 0$ için $t_{\text{crit}} = F_{t,df}^{-1}(1 - \alpha/k)$ (`0x004d3982`); tek kuyrukta $\alpha > 0.5$ iken $1-\alpha < 0.5$ olduğundan negatif kantil döner |
| **3** | $\|dz\| \ge 10^{-5}$ ve $N \ge 2$ sınırlarının her iki modda aynı olduğu varsayımı | CLI sınır değeri doğrulama testleri (`dz = 0.001` Post-hoc, `n_total = 2` Post-hoc) | $\|dz\| \ge 10^{-5}$ yalnızca A-priori'de zorunlu (`0x004db990`); Post-hoc girdi $N$ alt sınırı `3` (`0x004dc735`) |
