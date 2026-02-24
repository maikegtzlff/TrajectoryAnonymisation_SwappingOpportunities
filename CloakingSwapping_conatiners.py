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