"""ShipOrSkip: a small, tested toolkit that turns A/B experiment data into a ship-or-skip decision."""
from .analyze import analyze
from .cuped import cuped_adjust, cuped_pooled, cuped_theta
from .power import mde_mean, n_per_arm_mean, n_per_arm_proportion
from .sequential import obrien_fleming_bounds, peeking_false_positive_rate
from .srm import srm_drilldown, srm_test
from .stats import (benjamini_hochberg, bootstrap_diff_ci, delta_method_ratio, naive_ratio_test,
                    two_proportion_ztest, welch_ttest)

__all__ = ["analyze", "cuped_adjust", "cuped_pooled", "cuped_theta", "mde_mean", "n_per_arm_mean",
           "n_per_arm_proportion", "obrien_fleming_bounds", "peeking_false_positive_rate", "srm_drilldown",
           "srm_test", "benjamini_hochberg", "bootstrap_diff_ci", "delta_method_ratio", "naive_ratio_test",
           "two_proportion_ztest", "welch_ttest"]
__version__ = "0.1.0"
