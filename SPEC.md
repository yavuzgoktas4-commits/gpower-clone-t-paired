# Kabul Kriterleri ve Davranış Spesifikasyonu (SPEC) — K2 Ailesi: `t-paired`

Bu belge, `GPowerNT.exe` (G\*Power 3.1.9.7) ikili dosyasından tersine mühendislik ile sökülen **K2 Ailesi: `t-paired` (`Means: Difference between two dependent means (matched pairs)`, RTTI: `PowerTPairedMean`, Test ID: `0xcc`)** hesaplama motorunun tüm matematiksel, algoritmik ve uç değer davranışlarını Gherkin (`Feature`, `Background`, `Scenario`, `Scenario Outline`, `Given`, `When`, `Then`, `Examples`) formatında tanımlar.

```gherkin
# language: en
Feature: G*Power K2 Family t-paired (Means: Difference between two dependent means - matched pairs) Power and Sample Size Calculation Engine
  As a statistical power analysis engine replicating G*Power 3.1.9.7 (PowerTPairedMean @ 0x005cac60)
  I want to compute A-priori sample size (N) and Post-hoc statistical power (1 - beta) for matched pairs t-tests
  So that all outputs (Noncentrality parameter delta, Critical t, Df, Total sample size, and Actual power) match G*Power's IEEE-754 double-precision (binary64) behavior and rounding rules exactly.

  Background:
    Given the statistical test family is "t tests" and the statistical test is "Means: Difference between two dependent means (matched pairs)" (Test ID 0xcc)
    And all floating-point arithmetic is performed in IEEE-754 double precision (binary64)
    And the input effect size "dz" is preprocessed by taking its absolute value "|dz|" via bitwise sign-masking (0x7fffffffffffffff) prior to core calculation

  # ============================================================================
  # 1. DEGREES OF FREEDOM (df = N - 1) & CRITICAL t CALCULATION
  # ============================================================================

  Scenario: Degrees of freedom calculation (df = N - 1)
    Given a total sample size "N" (where N >= 2)
    When the degrees of freedom routine (0x004db950) is invoked
    Then the degrees of freedom "df" must be computed as "1.0 * N - 1.0"
    And the resulting "df" must be stored in both the distribution parameter block and the output field "expected_df"

  Scenario: Critical t calculation for one-tailed test (tails = 1)
    Given a tail configuration of "1" (One-tailed, internal flag [this+0x2a9] = 1)
    And an error probability "alpha" in the admissible range [1e-07, 0.9999999]
    And degrees of freedom "df = N - 1"
    When the critical t calculation routine (0x004d38b0 -> 0x004fb8c0 -> 0x004514f0) is executed
    Then the central Student's t distribution (delta = 0.0) inverse CDF must be evaluated at probability "p = 1.0 - alpha" (complementary tail q = alpha)
    And the resulting quantile "F^{-1}_{t, df}(1.0 - alpha)" must be stored as "expected_critical_t"

  Scenario: Critical t calculation for two-tailed test (tails = 2)
    Given a tail configuration of "2" (Two-tailed, internal flag [this+0x2a9] = 0)
    And an error probability "alpha" in the admissible range [1e-07, 0.9999999]
    And degrees of freedom "df = N - 1"
    When the critical t calculation routine (0x004d38b0 -> 0x004fb8c0 -> 0x004514f0) is executed
    Then the tail divisor "k" must be set to "2.0"
    And the central Student's t distribution (delta = 0.0) inverse CDF must be evaluated at probability "p = 1.0 - (alpha / 2.0)" (complementary tail q = alpha / 2.0)
    And the resulting positive quantile "F^{-1}_{t, df}(1.0 - alpha / 2.0)" must be stored as "expected_critical_t"

  Scenario: Negative Critical t when alpha > 0.5 in a one-tailed test (Edge Case paired_27)
    Given the analysis mode is "a-priori"
    And the input parameters are tails = 1, dz = 0.3, alpha = 0.7, and power_input = 0.85
    When the calculation engine runs
    Then the upper-tail probability is computed as "p = 1.0 - 0.7 = 0.3 < 0.5"
    And the solved sample size is expected_n_total = 4 with expected_df = 3
    And expected_critical_t must be negative and equal to -0.5843897 (within 1e-6 tolerance)
    And expected_ncp must be 0.6000000 and expected_actual_power must be 0.8665738

  # ============================================================================
  # 2. NONCENTRALITY PARAMETER (delta = |dz| * sqrt(N))
  # ============================================================================

  Scenario: Noncentrality parameter binary-level formula
    Given a preprocessed effect size "|dz|" and a total sample size "N"
    When the noncentrality parameter routine (0x004dc1b0 / 0x004dbdc0) is executed
    Then the square root of "N" must be computed in IEEE-754 double precision ("sqrtsd(N)")
    And the noncentrality parameter "delta" must be computed as "sqrtsd(N) * |dz|"
    And in A-priori mode, "delta" must be recomputed using the final integer-rounded "expected_n_total"

  # ============================================================================
  # 3. POST-HOC STATISTICAL POWER CALCULATION
  # ============================================================================

  Scenario: Post-hoc power calculation for one-tailed test (tails = 1)
    Given the analysis mode is "post-hoc"
    And valid input parameters tails = 1, dz, alpha, and n_total_input = N
    When the post-hoc power routine (0x004dc67c -> 0x004bdee0 -> 0x004d38b0) is executed
    Then "df" is set to "N - 1"
    And "critical_t" is computed as "F^{-1}_{t, df}(1.0 - alpha)"
    And "delta" is computed as "|dz| * sqrt(N)"
    And "expected_actual_power" must be computed from the noncentral Student's t CDF (0x004fa7e0 -> 0x004f9fa0) as:
      """
      Power = 1.0 - F_{t, df, delta}(critical_t)
      """

  Scenario: Post-hoc power calculation for two-tailed test (tails = 2)
    Given the analysis mode is "post-hoc"
    And valid input parameters tails = 2, dz, alpha, and n_total_input = N
    When the post-hoc power routine (0x004dc67c -> 0x004bdee0 -> 0x004d38b0) is executed
    Then "df" is set to "N - 1"
    And "critical_t" is computed as "F^{-1}_{t, df}(1.0 - alpha / 2.0)"
    And "delta" is computed as "|dz| * sqrt(N)"
    And the noncentral Student's t CDF (0x004fa7e0 -> 0x004f9fa0) must be evaluated at both "+critical_t" and "-critical_t"
    And "expected_actual_power" must be computed as:
      """
      Power = 1.0 - (F_{t, df, delta}(+critical_t) - F_{t, df, delta}(-critical_t))
      """

  # ============================================================================
  # 4. A-PRIORI ROOT-FINDING (BRENT'S METHOD) & TWO-STAGE CEIL ROUNDING
  # ============================================================================

  Scenario: A-priori sample size root-finding bracket initialization (0x0049a210 -> 0x004962d0)
    Given the analysis mode is "a-priori"
    And the objective function (0x004968d0) is defined for continuous N >= 2.0 as "f(N) = Power(|dz|, alpha, N) - power_input"
    When the bracket initialization routine (0x0049a210) is invoked with initial bounds (x_min = 2.0, x_init = 100.0)
    Then "f(100.0)" is evaluated first
    And if "f(100.0) < 0.0", the bracket starts at "[x_low, x_high] = [100.0, 160.0]" and repeatedly updates "x_low = x_high, x_high = 1.6 * x_high" until "f(x_high) >= 0.0"
    And if "f(100.0) >= 0.0", the bracket starts at "[x_low, x_high] = [51.0, 100.0]" and repeatedly updates "x_high = x_low, x_low = 0.5 * (x_low + 2.0) - 2.0" while "x_low >= 2.0" and "f(x_low) > 0.0", clamping "x_low = max(x_low, 2.0)"

  Scenario: A-priori continuous root-finding via Brent's method (0x004f9bb0)
    Given a valid bracket "[x_low, x_high]" where "f(x_low) <= 0.0" and "f(x_high) >= 0.0"
    When Brent's root-finding algorithm (0x004f9bb0) is called with:
      | Parameter      | Value                    | Binary Address / Constant |
      | tol            | 1e-10                    | 0x005c3f48                |
      | EPS            | 1.1102230246251565e-16   | 0x005c4390 (2^-53)        |
      | max_iterations | 300                      | 0x12c (@ 0x00496aed)      |
    Then the solver iterates using secant / inverse quadratic interpolation with bisection fallback
    And the solver terminates when "f(b) == 0.0" or "0.5 * |c - b| <= EPS * |b|" within at most 300 iterations
    And returns the continuous sample size estimate "N_cont = b"

  Scenario: Two-stage integer rounding rule (Snap-to-1e-10 + Ceil @ 0x00496a20) and output recomputation
    Given the continuous root "N_cont" returned by the root-finder
    When the sample size rounding routine (0x00496a20) is executed
    Then "N_cont" must first be snapped to the nearest 1e-10 grid point to eliminate floating-point drift:
      """
      N_snap = floor(N_cont * 10000000000.0 + 0.5) / 10000000000.0
      """
    And the integer sample size "expected_n_total" must be obtained by applying upward ceiling rounding:
      """
      expected_n_total = ceil(N_snap)
      """
    And if "expected_n_total < 2", it must be clamped to "expected_n_total = 2"
    And "expected_df", "expected_critical_t", "expected_ncp", and "expected_actual_power" must all be recomputed at the integer value "expected_n_total"

  # ============================================================================
  # 5. EDGE CASES & INPUT VALIDATION BOUNDARIES
  # ============================================================================

  Scenario: Edge case where power_input equals alpha in A-priori mode (power = alpha)
    Given the analysis mode is "a-priori"
    And "power_input" is equal to "alpha" (e.g., alpha = 0.05, power_input = 0.05) with any valid "|dz| >= 0.00001"
    When the validation routine (0x004880e0) and solver (0x00496aa0) are executed
    Then the input must be accepted because "power_input >= alpha" holds
    And since "Power(|dz|, alpha, N) > alpha" for all N >= 2, the root-finder returns 0.0 (unbracketed positive objective) and the lower-bound clamp (0x00496b38) sets "expected_n_total = 2"
    And "expected_df" must be 1, "expected_ncp" must be "|dz| * sqrt(2)", and "expected_actual_power" must be computed at N = 2

  Scenario: Edge case where dz is very small in Post-hoc mode (paired_28)
    Given the analysis mode is "post-hoc"
    And the input parameters are tails = 1, dz = 0.001, alpha = 0.05, and n_total_input = 10
    When the calculation engine runs
    Then the 0.00001 lower-bound check on "|dz|" is bypassed in Post-hoc mode (0x004db997)
    And "expected_ncp" approaches zero (0.0031623)
    And "expected_actual_power" approaches "alpha" (0.0500825)

  Scenario: Edge case where dz is very large in A-priori mode (paired_29)
    Given the analysis mode is "a-priori"
    And the input parameters are tails = 2, dz = 2.0, alpha = 0.05, and power_input = 0.8
    When the calculation engine runs
    Then the required sample size converges near the lower boundary at expected_n_total = 4
    And expected_df = 3, expected_critical_t = 3.1824463, expected_ncp = 4.0, and expected_actual_power = 0.8035827

  Scenario: Edge case where negative dz is supplied
    Given any valid analysis mode ("a-priori" or "post-hoc")
    And a negative effect size "dz" in [-20.0, -0.00001] for A-priori or [-20.0, 0.0) for Post-hoc
    When the calculation engine runs
    Then "dz" is converted to "|dz|" at entry (0x004dc3cb / 0x004dc7c8)
    And all outputs must be identical to those produced for "+|dz|"

  Scenario Outline: Input validation rejection rules
    Given the analysis mode is "<mode>"
    And the input parameters are tails = <tails>, dz = <dz>, alpha = <alpha>, power_input = <power_input>, n_total_input = <n_input>
    When input validation is performed
    Then the calculation must be rejected with the error message "<error_message>"

    Examples:
      | mode     | tails | dz       | alpha     | power_input | n_input    | error_message                                                                     |
      | a-priori | 2     | 0.5      | 0.00000001| 0.80        | null       | Alpha is outside the admissible range (1e-07, 0.9999999).                         |
      | a-priori | 2     | 0.5      | 0.99999999| 0.99999999  | null       | Alpha is outside the admissible range (1e-07, 0.9999999).                         |
      | a-priori | 2     | 0.5      | 0.05      | 0.00000001  | null       | Power is outside the admissible range (1e-07, 0.9999999).                         |
      | a-priori | 2     | 0.5      | 0.05      | 0.99999999  | null       | Power is outside the admissible range (1e-07, 0.9999999).                         |
      | a-priori | 2     | 0.5      | 0.10      | 0.05        | null       | Power must be greater than or equal to alpha.                                     |
      | a-priori | 2     | 0.000009 | 0.05      | 0.80        | null       | In an a priori analysis, the absolute value of the effect size be greater than 0.00001. |
      | a-priori | 2     | 20.0001  | 0.05      | 0.80        | null       | Effect size dz is outside the admissible range (-20, 20).                         |
      | post-hoc | 2     | -20.0001 | 0.05      | null        | 30         | Effect size dz is outside the admissible range (-20, 20).                         |
      | post-hoc | 2     | 0.5      | 0.05      | null        | 2          | Total sample size is outside the admissible range (3, 2147483646).                |
      | post-hoc | 2     | 0.5      | 0.05      | null        | 2147483647 | Total sample size is outside the admissible range (3, 2147483646).                |

  # ============================================================================
  # 6. GROUND TRUTH VERIFICATION VECTORS (paired_01 .. paired_30)
  # ============================================================================

  Scenario Outline: Ground truth verification against G*Power 3.1.9.7 oracle vectors
    Given the analysis mode is "<mode>"
    And the input parameters are tails = <tails>, dz = <dz>, alpha = <alpha>, power_input = <power_input>, n_total_input = <n_total_input>
    When the calculation engine runs
    Then expected_ncp must be <expected_ncp> (within 1e-6 absolute tolerance)
    And expected_critical_t must be <expected_critical_t> (within 1e-6 absolute tolerance)
    And expected_df must be <expected_df>
    And expected_n_total must be <expected_n_total>
    And expected_actual_power must be <expected_actual_power> (within 1e-6 absolute tolerance)

    Examples:
      | id        | mode     | tails | dz   | alpha | power_input | n_total_input | expected_ncp | expected_critical_t | expected_df | expected_n_total | expected_actual_power |
      | paired_01 | a-priori | 1     | 0.5  | 0.05  | 0.95        | null          | 3.3541020    | 1.6802300           | 44          | 45               | 0.9512400             |
      | paired_02 | a-priori | 2     | 0.5  | 0.05  | 0.80        | null          | 2.9154759    | 2.0345153           | 33          | 34               | 0.8077775             |
      | paired_03 | a-priori | 2     | 0.5  | 0.05  | 0.90        | null          | 3.3166248    | 2.0166922           | 43          | 44               | 0.9000306             |
      | paired_04 | a-priori | 2     | 0.5  | 0.05  | 0.95        | null          | 3.6742346    | 2.0057460           | 53          | 54               | 0.9502120             |
      | paired_05 | a-priori | 1     | 0.2  | 0.05  | 0.80        | null          | 2.4979992    | 1.6547438           | 155         | 156              | 0.8001673             |
      | paired_06 | a-priori | 2     | 0.2  | 0.05  | 0.80        | null          | 2.8213472    | 1.9720175           | 198         | 199              | 0.8016910             |
      | paired_07 | a-priori | 1     | 0.2  | 0.01  | 0.90        | null          | 3.6276714    | 2.3377704           | 328         | 329              | 0.9008371             |
      | paired_08 | a-priori | 2     | 0.2  | 0.01  | 0.90        | null          | 3.8781439    | 2.5890032           | 375         | 376              | 0.9006277             |
      | paired_09 | a-priori | 2     | 0.2  | 0.05  | 0.90        | null          | 3.2557641    | 1.9689905           | 264         | 265              | 0.9004175             |
      | paired_10 | a-priori | 2     | 0.1  | 0.05  | 0.85        | null          | 3.0000000    | 1.9626063           | 899         | 900              | 0.8500927             |
      | paired_11 | a-priori | 1     | 0.3  | 0.07  | 0.91        | null          | 2.8460499    | 1.4890855           | 89          | 90               | 0.9119324             |
      | paired_12 | a-priori | 2     | 0.6  | 0.04  | 0.96        | null          | 3.9344631    | 2.1195151           | 42          | 43               | 0.9624908             |
      | paired_13 | a-priori | 2     | 0.5  | 0.10  | 0.90        | null          | 3.0000000    | 1.6895725           | 35          | 36               | 0.9025768             |
      | paired_14 | a-priori | 2     | 0.10 | 0.20  | 0.81        | null          | 2.1610183    | 1.2833709           | 466         | 467              | 0.8101992             |
      | paired_15 | a-priori | 1     | 0.10 | 0.20  | 0.81        | null          | 1.7233688    | 0.8428372           | 296         | 297              | 0.8107640             |
      | paired_16 | a-priori | 2     | 0.15 | 0.20  | 0.81        | null          | 2.1633308    | 1.2856547           | 207         | 208              | 0.8101774             |
      | paired_17 | a-priori | 1     | 0.12 | 0.14  | 0.80        | null          | 1.9274854    | 1.0826016           | 257         | 258              | 0.8009375             |
      | paired_18 | a-priori | 2     | 0.12 | 0.14  | 0.80        | null          | 2.3206896    | 1.4789413           | 373         | 374              | 0.8000426             |
      | paired_19 | a-priori | 2     | 0.15 | 0.15  | 0.80        | null          | 2.2896506    | 1.4443133           | 232         | 233              | 0.8010421             |
      | paired_20 | a-priori | 1     | 0.17 | 0.15  | 0.80        | null          | 1.8853912    | 1.0408575           | 122         | 123              | 0.8008876             |
      | paired_21 | a-priori | 2     | 0.20 | 0.15  | 0.80        | null          | 2.2978251    | 1.4480221           | 131         | 132              | 0.8022061             |
      | paired_22 | a-priori | 2     | 0.2  | 0.15  | 0.80        | null          | 2.2978251    | 1.4480221           | 131         | 132              | 0.8022061             |
      | paired_23 | a-priori | 1     | 0.3  | 0.16  | 0.80        | null          | 1.8493242    | 1.0080029           | 37          | 38               | 0.8002160             |
      | paired_24 | a-priori | 1     | 0.35 | 0.16  | 0.80        | null          | 1.8848077    | 1.0124340           | 28          | 29               | 0.8088042             |
      | paired_25 | a-priori | 2     | 0.34 | 0.17  | 0.85        | null          | 2.4517749    | 1.3918782           | 51          | 52               | 0.8547609             |
      | paired_26 | a-priori | 1     | 0.34 | 0.17  | 0.85        | null          | 2.0114671    | 0.9677565           | 34          | 35               | 0.8516849             |
      | paired_27 | a-priori | 1     | 0.3  | 0.7   | 0.85        | null          | 0.6000000    | -0.5843897          | 3           | 4                | 0.8665738             |
      | paired_28 | post-hoc | 1     | 0.11 | 0.18  | null        | 546           | 2.5703307    | 0.9161374           | 545         | 546              | 0.9509339             |
      | paired_29 | a-priori | 2     | 0.31 | 0.17  | 0.87        | null          | 2.5184519    | 1.3875926           | 65          | 66               | 0.8703704             |
      | paired_30 | post-hoc | 2     | 0.11 | 0.18  | null        | 546           | 2.5703307    | 1.3424779           | 545         | 546              | 0.8902204             |
```
