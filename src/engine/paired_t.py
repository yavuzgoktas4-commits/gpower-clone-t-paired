"""Clean-room statistical calculation engine for K2 family: t-paired.

Implements A-priori sample size determination and Post-hoc power calculation
for matched-pairs Student's t-tests according to SPEC.md and CONTRACT.md 1.0.0.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Optional

from scipy import stats

from src.engine.errors import NoSolutionError, ValidationError

# Admissible parameter boundaries defined in SPEC.md
ALPHA_MIN: float = 1e-7
ALPHA_MAX: float = 0.9999999
POWER_MIN: float = 1e-7
POWER_MAX: float = 0.9999999
DZ_APRIORI_ABS_MIN: float = 1e-5
DZ_ABS_MAX: float = 20.0
N_APRIORI_MIN: int = 2
N_POSTHOC_MIN: int = 3
N_MAX: int = 2147483646

# Root-finding and rounding constants defined in SPEC.md
BRENT_TOL: float = 1e-10
BRENT_EPS: float = 1.1102230246251565e-16  # 2^-53
BRENT_MAX_ITER: int = 300
BRACKET_X_MIN: float = 2.0
BRACKET_X_INIT: float = 100.0
BRACKET_GROWTH_FACTOR: float = 1.6
SNAP_GRID_SCALE: float = 10000000000.0  # 1e10
CENTRAL_T_NCP_THRESHOLD: float = 1e-100


@dataclass(frozen=True)
class PairedTResult:
    """Result container for t-paired calculations."""

    ncp: float
    critical_t: float
    df: int
    n_total: int
    actual_power: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "ncp": float(self.ncp),
            "critical_t": float(self.critical_t),
            "df": int(self.df),
            "n_total": int(self.n_total),
            "actual_power": float(self.actual_power),
        }


def compute_df(n: float) -> float:
    """Compute degrees of freedom df = 1.0 * N - 1.0 per SPEC.md."""
    return 1.0 * float(n) - 1.0


def compute_ncp(abs_dz: float, n: float) -> float:
    """Compute noncentrality parameter delta = sqrt(N) * |dz| per SPEC.md."""
    return math.sqrt(float(n)) * float(abs_dz)


def compute_critical_t(alpha: float, df: float, tails: int) -> float:
    """Compute central Student's t critical value F^{-1}_{t, df}(1 - alpha / k)."""
    k = 2.0 if tails == 2 else 1.0
    p = 1.0 - (float(alpha) / k)
    val = float(stats.t.ppf(p, float(df)))
    if math.isnan(val) or math.isinf(val):
        raise NoSolutionError("Failed to evaluate critical t quantile.", field="critical_t")
    return val


def _nct_cdf(x: float, df: float, ncp: float) -> float:
    """Evaluate noncentral (or central when |ncp| < 1e-100) Student's t CDF."""
    if abs(ncp) < CENTRAL_T_NCP_THRESHOLD:
        val = float(stats.t.cdf(x, df))
    else:
        val = float(stats.nct.cdf(x, df, ncp))
    if math.isnan(val):
        raise NoSolutionError("Noncentral t CDF evaluation returned NaN.", field="actual_power")
    return val


def evaluate_power_for_n(
    abs_dz: float,
    alpha: float,
    n: float,
    tails: int,
) -> tuple[float, float, float, float]:
    """Evaluate statistical power, critical_t, df, and ncp for continuous or integer N."""
    df = compute_df(n)
    critical_t = compute_critical_t(alpha, df, tails)
    ncp = compute_ncp(abs_dz, n)

    if tails == 1:
        cdf_upper = _nct_cdf(critical_t, df, ncp)
        power = 1.0 - cdf_upper
    else:
        cdf_pos = _nct_cdf(critical_t, df, ncp)
        cdf_neg = _nct_cdf(-critical_t, df, ncp)
        power = 1.0 - (cdf_pos - cdf_neg)

    return float(power), float(critical_t), float(df), float(ncp)


def round_sample_size(n_cont: float) -> int:
    """Apply SPEC.md two-stage rounding rule: snap to nearest 1e-10 then ceil."""
    n_snap = math.floor(float(n_cont) * SNAP_GRID_SCALE + 0.5) / SNAP_GRID_SCALE
    return int(math.ceil(n_snap))


def init_a_priori_bracket(
    objective_fn: Callable[[float], float],
    x_min: float = BRACKET_X_MIN,
    x_init: float = BRACKET_X_INIT,
) -> tuple[float, float]:
    """Initialize root-finding bracket [x_low, x_high] per SPEC.md."""
    f_init = objective_fn(x_init)
    if f_init < 0.0:
        x_low = x_init
        x_high = x_init * BRACKET_GROWTH_FACTOR
        steps = 0
        while objective_fn(x_high) < 0.0:
            x_low = x_high
            x_high = x_high * BRACKET_GROWTH_FACTOR
            steps += 1
            if x_high > float(N_MAX) * 2.0 or steps > BRENT_MAX_ITER:
                raise NoSolutionError(
                    "Required sample size exceeds maximum admissible search bound.",
                    field="n_total",
                )
        if x_low < x_min:
            x_low = x_min
    else:
        x_high = x_init
        x_low = 0.5 * (x_min + x_init)
        while x_low >= x_min and objective_fn(x_low) > 0.0:
            x_high = x_low
            x_low = 0.5 * (x_low + x_min) - x_min
        if x_low < x_min:
            x_low = x_min

    return x_low, x_high


def brent_solve(
    objective_fn: Callable[[float], float],
    x_low: float,
    x_high: float,
    tol: float = BRENT_TOL,
    max_iter: int = BRENT_MAX_ITER,
) -> tuple[float, int]:
    """Brent's root-finding algorithm (zbrent) matching SPEC.md parameters.

    Returns (root_estimate, status_code) where status_code is:
      0: converged
      1: root not bracketed (f(x_low) * f(x_high) > 0.0)
      2: exceeded max_iter
    """
    _ = tol  # Stored in solver configuration per SPEC.md
    a = float(x_low)
    b = float(x_high)
    c = float(x_high)
    fa = objective_fn(a)
    fb = objective_fn(b)

    if fa * fb > 0.0:
        return 0.0, 1

    fc = fb
    d = 0.0
    e = 0.0

    for _ in range(max_iter):
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
            d = b - a
            e = d

        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa

        tol1 = BRENT_EPS * abs(b)
        xm = 0.5 * (c - b)

        if abs(xm) <= tol1 or fb == 0.0:
            return b, 0

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)

            if p > 0.0:
                q = -q
            p = abs(p)

            min1 = 3.0 * xm * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < (min1 if min1 < min2 else min2):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d

        a = b
        fa = fb
        if abs(d) > tol1:
            b += d
        else:
            b += tol1 if xm >= 0.0 else -tol1
        fb = objective_fn(b)

    return b, 2


def validate_inputs(
    mode: str,
    tails: int,
    dz: float,
    alpha: float,
    power: Optional[float] = None,
    n_total: Optional[int] = None,
) -> str:
    """Validate all parameters against SPEC.md and CONTRACT.md 1.0.0 rules."""
    normalized_mode = mode.strip().lower().replace("_", "-")
    if normalized_mode not in ("a-priori", "post-hoc"):
        raise ValidationError(
            f"Unsupported analysis mode '{mode}'. Only 'a-priori' and 'post-hoc' are supported.",
            code="UNSUPPORTED",
            field="mode",
        )

    if not isinstance(tails, int) or isinstance(tails, bool) or tails not in (1, 2):
        raise ValidationError(
            "Tails must be 1 (one-tailed) or 2 (two-tailed).",
            code="OUT_OF_RANGE",
            field="tails",
        )

    if math.isnan(alpha) or math.isinf(alpha) or alpha < ALPHA_MIN or alpha > ALPHA_MAX:
        raise ValidationError(
            "Alpha is outside the admissible range (1e-07, 0.9999999).",
            code="OUT_OF_RANGE",
            field="alpha",
        )

    if math.isnan(dz) or math.isinf(dz):
        raise ValidationError(
            "Effect size dz must be a finite number.",
            code="OUT_OF_RANGE",
            field="dz",
        )

    if normalized_mode == "a-priori":
        if n_total is not None:
            raise ValidationError(
                "Parameter 'n_total' cannot be specified in a-priori mode.",
                code="INCONSISTENT",
                field="n_total",
            )
        if power is None:
            raise ValidationError(
                "Missing required parameter 'power' for a-priori mode.",
                code="MISSING_PARAM",
                field="power",
            )
        if math.isnan(power) or math.isinf(power) or power < POWER_MIN or power > POWER_MAX:
            raise ValidationError(
                "Power is outside the admissible range (1e-07, 0.9999999).",
                code="OUT_OF_RANGE",
                field="power",
            )
        if power < alpha:
            raise ValidationError(
                "Power must be greater than or equal to alpha.",
                code="INCONSISTENT",
                field="power",
            )
        if abs(dz) < DZ_APRIORI_ABS_MIN:
            raise ValidationError(
                "In an a priori analysis, the absolute value of the effect size be greater than 0.00001.",
                code="OUT_OF_RANGE",
                field="dz",
            )
        if dz < -DZ_ABS_MAX or dz > DZ_ABS_MAX:
            raise ValidationError(
                "Effect size dz is outside the admissible range (-20, 20).",
                code="OUT_OF_RANGE",
                field="dz",
            )
    else:
        if power is not None:
            raise ValidationError(
                "Parameter 'power' cannot be specified in post-hoc mode.",
                code="INCONSISTENT",
                field="power",
            )
        if n_total is None:
            raise ValidationError(
                "Missing required parameter 'n_total' for post-hoc mode.",
                code="MISSING_PARAM",
                field="n_total",
            )
        if dz < -DZ_ABS_MAX or dz > DZ_ABS_MAX:
            raise ValidationError(
                "Effect size dz is outside the admissible range (-20, 20).",
                code="OUT_OF_RANGE",
                field="dz",
            )
        if (
            not isinstance(n_total, int)
            or isinstance(n_total, bool)
            or n_total < N_POSTHOC_MIN
            or n_total > N_MAX
        ):
            raise ValidationError(
                "Total sample size is outside the admissible range (3, 2147483646).",
                code="OUT_OF_RANGE",
                field="n_total",
            )

    return normalized_mode


def solve_a_priori(dz: float, alpha: float, power: float, tails: int) -> PairedTResult:
    """Solve for total sample size N in A-priori mode per SPEC.md."""
    abs_dz = abs(float(dz))
    target_power = float(power)

    def objective(n_candidate: float) -> float:
        p_val, _, _, _ = evaluate_power_for_n(abs_dz, alpha, n_candidate, tails)
        return p_val - target_power

    x_low, x_high = init_a_priori_bracket(objective, BRACKET_X_MIN, BRACKET_X_INIT)
    n_cont, status = brent_solve(objective, x_low, x_high, tol=BRENT_TOL, max_iter=BRENT_MAX_ITER)

    if status == 2:
        raise NoSolutionError(
            "Brent root-finding failed to converge within 300 iterations.",
            field="n_total",
        )
    if status == 1 and objective(x_low) < 0.0:
        raise NoSolutionError(
            "Failed to bracket root for sample size determination.",
            field="n_total",
        )

    n_rounded = round_sample_size(n_cont)
    if float(n_rounded) < x_low:
        n_rounded = round_sample_size(x_low)

    if n_rounded < N_APRIORI_MIN or n_rounded > N_MAX:
        raise NoSolutionError(
            "Total sample size is outside the admissible range (2, 2147483646).",
            field="n_total",
        )

    actual_power, critical_t, df, ncp = evaluate_power_for_n(
        abs_dz, alpha, float(n_rounded), tails
    )
    return PairedTResult(
        ncp=ncp,
        critical_t=critical_t,
        df=int(round(df)),
        n_total=int(n_rounded),
        actual_power=actual_power,
    )


def calculate_post_hoc(dz: float, alpha: float, n_total: int, tails: int) -> PairedTResult:
    """Compute statistical power in Post-hoc mode per SPEC.md."""
    abs_dz = abs(float(dz))
    actual_power, critical_t, df, ncp = evaluate_power_for_n(
        abs_dz, alpha, float(n_total), tails
    )
    return PairedTResult(
        ncp=ncp,
        critical_t=critical_t,
        df=int(round(df)),
        n_total=int(n_total),
        actual_power=actual_power,
    )


def calculate_t_paired(
    mode: str,
    tails: int,
    dz: float,
    alpha: float,
    power: Optional[float] = None,
    n_total: Optional[int] = None,
) -> PairedTResult:
    """Validate inputs and execute A-priori or Post-hoc calculation for t-paired."""
    normalized_mode = validate_inputs(
        mode=mode,
        tails=tails,
        dz=dz,
        alpha=alpha,
        power=power,
        n_total=n_total,
    )
    if normalized_mode == "a-priori":
        assert power is not None
        return solve_a_priori(dz=dz, alpha=alpha, power=power, tails=tails)
    assert n_total is not None
    return calculate_post_hoc(dz=dz, alpha=alpha, n_total=n_total, tails=tails)
