"""
Shared test helpers
"""


def remove_test_deps(deps):
    """If running with pytest coverage enabled, these deps will show up. We
    don't want run-env-dependent tests, so we just pop them out.
    """
    for test_dep in ["pytest_cov", "coverage"]:
        try:
            deps.remove(test_dep)
        except ValueError:
            continue
    return deps
