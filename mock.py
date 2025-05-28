# this file contains the logic for running a grid search on the backtest-v2.py module
# to determine which parameters work the best, however the real data was deleted
# from the internet so we have mocked some fake scenarios in this file to test the logic.
# The values are not realistic, but the logic does work.
# Ideally most of this file can be replaced with real data (when the data is avalable again),
# and then we can run the grid search on the real data to get the best parameters.
# But until then this is just a mock for testing purposes.

import pathlib
import importlib.util
from datetime import datetime, timedelta

# dynamically loading backtest-v2.py as its not recognizing it as a module
spec = importlib.util.spec_from_file_location(
    "backtest_v2",
    pathlib.Path(__file__).parent / "backtest-v2.py"
)
backtest_v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backtest_v2)

N_DAYS   = 30
THRESHOLDS = range(0, 11)
MIX_WEIGHTS = [0.0, 0.5, 1.0]

# Extract whats usefull
compute_prediction    = backtest_v2.compute_prediction
Extent                = backtest_v2.Extent
Resolution            = backtest_v2.Resolution
ProvinceType          = backtest_v2.ProvinceType
DIBIEventStore        = backtest_v2.DIBIEventStore
GADMLocationManager   = backtest_v2.GADMLocationManager


def _fake_compute_prediction(run_dt, extent, resolution, params):
    key = run_dt.date()
    hits = POS_BY_DATE.get(key, set())

    # apply a “threshold”: only keep a hit if we have at least that many on this date
    # (just an example of how you might use th)
    th = params["hazard_index_threshold"]
    if len(hits) < th:
        return set()

    # simulate “mix_weight” by dropping a fraction of hits when w<1.0
    w = params["mix_weight"]
    if w < 1.0:
        # e.g. only keep the first int(len(hits)*w) GID2s
        hits = set(list(hits)[: int(len(hits)*w) ])
    return hits
compute_prediction = _fake_compute_prediction

# Provinces & GID2 list from backtest-v2
PROVINCES = [
    ProvinceType.BANTEN,
    ProvinceType.BALI,
    ProvinceType.DKI_JAKARTA,
    ProvinceType.JAWA_BARAT,
    ProvinceType.JAWA_TENGAH,
    ProvinceType.JAWA_TIMUR,
    ProvinceType.DIY_YOGYAKARTA,
]

# 2) choose 7 “districts” for our fake floods
GIDS = [
    "IDN.11.8.28_1",  # Tanggul
    "IDN.11.8.25_1",  # Sumber Baru
    "IDN.11.30.10_1"  # Krucil
]

# --------------- Grid search function ---------------
def run_grid_search(store, dates, gids, extent, res, thresholds, weights):
    results = []
    for th in thresholds:
        for w in weights:
            tp=fp=fn=tn=0
            for dt in dates:
                predicted = compute_prediction(
                    dt, extent, res,
                    {"hazard_index_threshold": th,
                     "mix_weight":             w}
                )
                actual = store.get_events_on_date_gid2s(dt)
                for gid in gids:
                    hit  = gid in predicted
                    real = gid in actual
                    if   real and   hit: tp+=1
                    elif real and not hit: fn+=1
                    elif not real and hit: fp+=1
                    else:                  tn+=1
            prec = tp/(tp+fp+1e-9)
            rec  = tp/(tp+fn+1e-9)
            f1   = 2*prec*rec/(prec+rec+1e-9)
            results.append(((th, w), (tp,fp,fn,tn,prec,rec,f1)))
    return results

# 1-month date range
DATE_START = datetime(2025, 5, 1)
DATES = [datetime(2025,5,1) + timedelta(days=i) for i in range(N_DAYS)]

# fake events on dates and provinces
POS_BY_DATE = {
    DATES[0].date():  {GIDS[0], GIDS[1]}, 
    DATES[3].date():  {GIDS[1]},   
    DATES[7].date():  {GIDS[2]},    
    DATES[10].date(): {GIDS[0]},      
    DATES[14].date(): {GIDS[1]},      
    DATES[20].date(): {GIDS[2]},      
    DATES[25].date(): {GIDS[0]},     
}

EXT = Extent(104.5, 120.0, -10.0, -4.75)
RES = Resolution(lat=128, lon=256)

# Mock events for testing
class FakeEvent:
    def __init__(self, date, gid2):
        self.date = date
        self.gid2 = gid2

class FakeStore:
    def __init__(self, events):
        self._events = events
    def get_events_on_date_gid2s(self, date):
        return list(POS_BY_DATE.get(date.date(), []))


# --------------- Run grid search ---------------

results = run_grid_search(
    store      = FakeStore(POS_BY_DATE),
    dates      = DATES,
    gids       = GIDS,
    extent     = EXT,
    res        = RES,
    thresholds = THRESHOLDS,
    weights    = MIX_WEIGHTS,
)

# Pick best by F1
best = max(results, key=lambda e: e[1][6])
(th,w),(tp,fp,fn,tn,prec,rec,f1) = best

print("=== GRID SEARCH RESULTS ===")
print(f" Best threshold  = {th}")
print(f" Best mix weight = {w}")
print(f"  → TP={tp} FP={fp} FN={fn} TN={tn}")
print(f" Precision={prec:.3f} Recall={rec:.3f} F1={f1:.3f}\n")
print("=== ALL RESULTS ===")
for (t,wt),(tp,fp,fn,tn,prec,rec,f1) in results:
    print(f" th={t:>2}, w={wt:.2f} → F1={f1:.3f}")