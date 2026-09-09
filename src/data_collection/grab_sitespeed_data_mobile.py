"""Mobile entry point for the shared PageSpeed batch collector."""
from functools import partial

if __package__:
    from .grab_sitespeed_data_desktop import run_batch as collect_batch
else:
    from grab_sitespeed_data_desktop import run_batch as collect_batch

run_batch = partial(collect_batch, strategy="mobile")


if __name__ == "__main__":
    key = dbutils.secrets.get(scope="site_speed_project", key="google_psi_api_key") if "dbutils" in globals() else None
    run_batch(api_key=key)
