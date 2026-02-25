#%% load data
import geopandas as gpd
import numpy as np

t = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
# columns for cloaking based swapping
# intersecting_cloaking_ids - cloaking areas passing only
# HeadEndCloakingAreaId - upcoming cloaking area
# HeadTail - point to split tid before cloaking area
# then delete all syntithic points until first raw point
# this is the first point of the tail

# it's actually better to have empty list rather than nan
# Ensure every cell is a proper list
t['intersecting_cloaking_ids'] = t['intersecting_cloaking_ids'].apply(
    lambda x: list(x) if isinstance(x, (list, np.ndarray)) else []
)

t.head()
#%%
t.HeadEndCloakingAreaId.value_counts().sum() #31,272

#%% flag trajectory ids that have been cloaked
tids_to_swap = t.loc[t['HeadEndCloakingAreaId'].notna(), 'tid_subid'].unique()
print(f"mumber of tid_subid requiring swapping: {len(tids_to_swap)}")
print(f"number of tid_subids in sample (total): {t.tid_subid.nunique()}")

t['tid_needs_swap'] = t['tid_subid'].isin(tids_to_swap)

print(t.tid_needs_swap.value_counts())
# points belonging to tids that must be swapped 
#True     5,655,069
#False    1,679,872

#%%
num_targets = len(tids_to_swap)
num_total = t.tid_subid.nunique()

percentage = (num_targets / num_total) * 100

print(f"{percentage:.2f}% of trajectories require swapping because of cloaking")

#%% look at intersecting_cloaking_ids
import numpy as np

def is_non_empty(x):
    if x is None:
        return False
    elif isinstance(x, list):
        return len(x) > 0
    elif isinstance(x, np.ndarray):
        return len(x) > 0
    else:
        return False

non_empty_mask = t['intersecting_cloaking_ids'].apply(is_non_empty)

print("Number of non-empty lists/arrays:", non_empty_mask.sum())
print("Any non-empty?", non_empty_mask.any())
print(t.loc[non_empty_mask, 'intersecting_cloaking_ids'].head())






#%% precompute trajectory level information: finding matches
# approach: 11,791 target trajectories (the ones that are cloaked)
# for each target trajectory, all others become "helper" trajectories (must be a different uid)
# find 3 matches, then stop looking for matches. matches must be same cloaking area and same time bin.
# pick one of the 3 matches for swapping 

print(len(t[t['HeadEndCloakingAreaId'].notna()])) # these are all the cloaking gaps that need a swapping partner
# 31,272 rows!
print(t[t['HeadEndCloakingAreaId'].notna()]['tid_subid'].nunique()) # 11,791 different trajectories




#%% FIND SWAPPING CANDIDATES (points)
#%% cloaking gaps that need matches
sensitiveC = t[t['HeadEndCloakingAreaId'].notna()]

#%% find matches for the cloaking gaps
# Only keep points that are passing at least one cloaking geometry,
# i.e., intersecting cloaking  id list must not be empty 
helper_candidates = t[t['intersecting_cloaking_ids'].notna()].copy()
print(len(helper_candidates))                           # 7,334,941 points pass at least one cloaking area

# must explode lists so that each cloaking geom has one row per passing point
helper_candidates = helper_candidates.explode('intersecting_cloaking_ids')
helper_candidates.rename(columns={'intersecting_cloaking_ids': 'clkpassed'}, inplace=True)
print(len(helper_candidates))                           # 7,377,573 points after exploding, i.e. one row per point and cloaking area passed
print(len(helper_candidates) -len(helper_candidates))   # 42,632 rows extra

#%%
print(len(t) == t.row_uid.nunique()) # true, and 7334941
# we can use this id as unique point id

main_rows = sensitiveC[['row_uid', 'tid_subid', 'uid', 'HeadEndCloakingAreaId', 'time_bin']].copy()

def find_candidates(row):
    cands = helper_candidates[
        (helper_candidates['clkpassed'] == row['HeadEndCloakingAreaId']) &
        (helper_candidates['time_bin'] == row['time_bin']) &
        (helper_candidates['uid'] != row['uid'])  # different trajectory
    ].copy()
    cands['main_row_uid'] = row['row_uid']  # track which main row this is for
    return cands

# Example for first row
cands_first = find_candidates(main_rows.iloc[0])
print(len(cands_first))
cands_first

#%% look at matches
print('the point loctaing the cloaking gap')
print(main_rows.head(1).row_uid.unique())
print('target uid', main_rows.head(1).uid.unique())
print('target cloaking area', main_rows.head(1).HeadEndCloakingAreaId.unique())
print('target time bin in cloaking area', main_rows.head(1).time_bin.unique())


print('\n swapping candidates')
print('number of eligible swapping candidates', len(cands_first)) # 
print('candidate cloaking geom', cands_first.clkpassed.unique()) # should only be one, the same as main_rows.ilow[0]
print('candidate time bin', cands_first.time_bin.unique())  # comment from above applies
print('candidate uids', cands_first.uid.unique()) # can be many, but cant be the same as uid of main_rows.ilow[0]
print('candidate unique point ids', cands_first.row_uid.unique()) # unique identifiers to these points - these will not change during swapping either
print('kept track of lcoaking gap', cands_first.main_row_uid.notna().any()) 

print('\n ensuring constraints are met')
main_clk = main_rows.head(1)['HeadEndCloakingAreaId'].iloc[0]
main_time = main_rows.head(1)['time_bin'].iloc[0]
main_uid = main_rows.head(1)['uid'].iloc[0]
print('found matching cloaking geom', all(cands_first['clkpassed'].unique() == main_clk))
print('time bin is the same', all(cands_first['time_bin'].unique() == main_time))
print('target uid not in list of candidate uids', main_uid not in cands_first['uid'].unique())


#%% find swapping candidates for all ~30k cloaking gaps
import pandas as pd

# List to collect all candidate DataFrames
all_candidates_list = []

from tqdm import tqdm
for row in tqdm(main_rows.itertuples(index=False), total=len(main_rows), desc="Finding candidates"):
    cands = helper_candidates[
        (helper_candidates['clkpassed'] == row.HeadEndCloakingAreaId) &
        (helper_candidates['time_bin'] == row.time_bin) &
        (helper_candidates['uid'] != row.uid)
    ].copy()
    cands['main_row_uid'] = row.row_uid
    if len(cands) > 0:
        all_candidates_list.append(cands)

# Combine all candidate rows into one DataFrame
all_candidates = pd.concat(all_candidates_list, ignore_index=True)
print(f"Total candidate rows: {len(all_candidates)}")
print(f"Unique main rows with candidates: {all_candidates['main_row_uid'].nunique()}")
print(f"Unique candidate points: {all_candidates['row_uid'].nunique()}")

#Finding candidates: 100%|██████████| 31272/31272 [6:45:30<00:00,  1.29it/s]  
#Total candidate rows: 23909882
#Unique main rows with candidates: 27609
#Unique candidate points: 245681
#%%
all_candidates.head()

#%%
all_candidates.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/AllSwappingCandidates_cloaking.parquet")

#%%
import pickle
with open(r"D:\paper3\Data\output\CloakingBasedSwapping/all_candidates_list.pkl", "wb") as f:
    pickle.dump(all_candidates_list, f)

#%% ensure I can load the pickle back in 
with open(r"D:\paper3\Data\output\CloakingBasedSwapping/all_candidates_list.pkl", "rb") as f:
    all_candidates_list_reloead = pickle.load(f)
len(all_candidates_list_reloead)

#%%
sensitiveC.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/main_rows_allcolumns.parquet")
main_rows.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/main_rows.parquet")





#%% explore swapping candidates more
helper_traj_per_main = (
    all_candidates
    .groupby('main_row_uid')['tid_subid']
    .nunique()
    .rename('n_helper_traj')
    .reset_index()
)
print("Main rows with ONLY ONE helper trajectory:",
      (helper_traj_per_main.n_helper_traj == 1).sum())

print("Main rows with <= 2 helper trajectories:",
      (helper_traj_per_main.n_helper_traj <= 2).sum())

helper_traj_per_main.describe()
#%%
helper_traj_per_main.n_helper_traj.value_counts().sort_index().head(20)




#%% (1) main_row  → helper trajectory options
main_to_helpers = (
    all_candidates[['main_row_uid','tid_subid']]
    .drop_duplicates()
)

helper_to_mains = (
    main_to_helpers
    .groupby('tid_subid')['main_row_uid']
    .nunique()
    .rename('n_mains_this_helper_can_serve')
    .reset_index()
)
helper_to_mains.describe()

#%%
main_priority = helper_traj_per_main.copy()

main_priority['n_candidate_points'] = (
    all_candidates.groupby('main_row_uid')
    .size()
    .values
)

main_priority = main_priority.sort_values('n_helper_traj')


#%%
all_candidates.groupby('clkpassed')['tid_subid'].nunique().describe()

#%%
all_candidates[['clkpassed','tid_subid']].drop_duplicates() \
    .groupby('clkpassed').size().sort_values().head(20)


#%% (2) count options per main_row
main_supply = (
    main_to_helpers
    .groupby('main_row_uid')['tid_subid']
    .nunique()
    .rename('n_helper_traj')
)

#%% (3) sort mains by scarcity (hardest first)
main_order = (
    main_supply
    .sort_values()          # fewest options first
    .index
)
#main_order[0] = main with only ONE possible helper trajectory - 5365117

#%% (4) track usage constraint: a helper trajectory can only be used ONCE per cloaking area
from collections import defaultdict
used_helpers_per_clk = defaultdict(set)


# (5) scarcity-aware assignment loop
assigned = []

for m in tqdm(main_order, desc="Scarcity-aware assignment"):

    # get cloaking area of this main_row
    clk = main_rows.loc[
        main_rows.row_uid == m,
        'HeadEndCloakingAreaId'
    ].values[0]

    # all candidate helper trajectories for this main
    cands = main_to_helpers[
        (main_to_helpers.main_row_uid == m) &
        (~main_to_helpers.tid_subid.isin(used_helpers_per_clk[clk]))
    ]

    if len(cands) == 0:
        continue

    # choose helper trajectory
    chosen_tid = cands.tid_subid.sample(1).iloc[0]

    assigned.append((m, chosen_tid, clk))

    # mark helper trajectory as used at this cloaking area
    used_helpers_per_clk[clk].add(chosen_tid)


#%% export dict
import pickle

# Convert defaultdict to dict
used_helpers_dict = dict(used_helpers_per_clk)

# Export
with open(r"D:\paper3\Data\output\CloakingBasedSwapping/used_helpers_per_clk.pkl", "wb") as f:
    pickle.dump(used_helpers_dict, f)

# --- To load back ---
#with open(r"D:\paper3\Data\output\CloakingBasedSwapping/used_helpers_per_clk.pkl", "rb") as f:
#    loaded_dict = pickle.load(f)
#loaded_dict

#%%  could have made it run fster (didn't)
# pre-buil lookup
clk_lookup = (
    main_rows
    .set_index('row_uid')['HeadEndCloakingAreaId']
    .to_dict()
)
helper_lookup = (
    main_to_helpers
    .groupby('main_row_uid')['tid_subid']
    .apply(set)
    .to_dict()
)
# 
from collections import defaultdict
used_helpers_per_clk = defaultdict(set)

assigned = []

for m in main_order:

    clk = clk_lookup[m]

    possible_helpers = helper_lookup.get(m, set())
    available = possible_helpers - used_helpers_per_clk[clk]

    if not available:
        continue

    chosen_tid = np.random.choice(list(available))

    assigned.append((m, chosen_tid, clk))
    used_helpers_per_clk[clk].add(chosen_tid)




#%% look at used_helpers_per_clk
from collections import Counter

# 1️⃣ Number of cloaking areas
n_clks = len(used_helpers_per_clk)
print("Number of cloaking areas used:", n_clks) #177

# 2️⃣ Number of helper trajectories per cloaking area
helpers_per_clk = [len(v) for v in used_helpers_per_clk.values()]
import numpy as np
print("Mean helpers per cloaking area:", np.mean(helpers_per_clk))      #66
print("Median helpers per cloaking area:", np.median(helpers_per_clk))  #30
print("Max helpers per cloaking area:", np.max(helpers_per_clk))        #789
print("Min helpers per cloaking area:", np.min(helpers_per_clk))        #1

# 3️⃣ Distribution (optional)
import pandas as pd
pd.Series(helpers_per_clk).describe()
#count    177.000000
#mean      66.327684
#std       98.924070
#min        1.000000
#25%        7.000000
#50%       30.000000
#75%       89.000000
#max      789.000000
#%%
import matplotlib.pyplot as plt

plt.hist(helpers_per_clk, bins=50)
plt.xlabel("Number of helpers per cloaking area")
plt.ylabel("Count of cloaking areas")
plt.show()



#%% and now by cloaking gap
# Count number of assigned helpers per main_row
assigned_df = pd.DataFrame(assigned, columns=['main_row_uid', 'helper_tid', 'clkpassed'])

# Merge with main_rows to get full info
main_rows_with_helpers = main_rows.merge(assigned_df, left_on='row_uid', right_on='main_row_uid', how='left')

# Stats per main_row (cloaking gap)
gap_stats = main_rows_with_helpers.groupby('row_uid').agg(
    n_helpers_assigned=('helper_tid','count')  # usually 0 or 1
)

print(gap_stats.describe())

#       n_helpers_assigned
#count        31272.000000
#mean             0.375416
#std              0.484238
#min              0.000000
#25%              0.000000
#50%              0.000000
#75%              1.000000
#max              1.000000

main_rows_per_area = main_rows.groupby('HeadEndCloakingAreaId').size()
print(main_rows_per_area.describe())
#count     186.000000
#mean      168.129032
#std       180.508005
#min         1.000000
#25%        31.750000
#50%       111.000000
#75%       256.500000
#max      1039.000000

#%% start swapping based on used_helpers_per_clk