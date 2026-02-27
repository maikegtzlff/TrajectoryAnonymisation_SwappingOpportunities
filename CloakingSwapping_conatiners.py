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

print(helper_candidates.row_uid.nunique()) # 7334941
duplicates = helper_candidates['row_uid'].value_counts()
duplicates = duplicates[duplicates > 1]
print("before exploding: number of row_uid values appearing multiple times:", len(duplicates)) # 0
print(duplicates.reset_index()['count'].median())
print(duplicates.reset_index()['count'].max()) # nan

# must explode lists so that each cloaking geom has one row per passing point
helper_candidates = helper_candidates.explode('intersecting_cloaking_ids')
helper_candidates.rename(columns={'intersecting_cloaking_ids': 'clkpassed'}, inplace=True)
print(len(helper_candidates))                           # 7,377,573 points after exploding, i.e. one row per point and cloaking area passed
print(len(helper_candidates) -len(helper_candidates))   # 42,632 rows extra


print(helper_candidates.row_uid.nunique()) # 7334941
duplicates = helper_candidates['row_uid'].value_counts()
duplicates = duplicates[duplicates > 1]
print("after exploding: number of row_uid values appearing multiple times:", len(duplicates)) # 0
print(duplicates.reset_index()['count'].median())
print(duplicates.reset_index()['count'].max()) # nan

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
#Total candidate rows: 23,909,882
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



#%% ############################################################
####       new approach to assigning swapping candidates    ####
#################################################################




#################################################################






















































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

#%%
with open(r"D:\paper3\Data\output\CloakingBasedSwapping/assigned.pkl", "wb") as f:
    pickle.dump(assigned, f)

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

#       n_helpers_assigned - number of helper trajectories assigned to cloaking gap for swapping
#count        31272.000000
#mean             0.375416
#std              0.484238
#min              0.000000
#25%              0.000000
#50%              0.000000 --> no helper assigned to cloaking gap --> cannot swap
#75%              1.000000 --> we never assign more than one helper because the algorithm is scarcity-aware, we are looking for the most optimal match
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

#%% number of main_rows (cloaking gaps) with a helper assigned
assigned_helpers_df = pd.DataFrame(assigned, columns=['main_row_uid', 'helper_tid', 'clkpassed'])
# each row is one cloaling gap that succefully got a helper trajectory 
n_assigned = assigned_helpers_df['main_row_uid'].nunique()
n_total = len(main_rows)
pct_assigned = n_assigned / n_total * 100

print(f"Assigned helpers: {n_assigned} / {n_total} ({pct_assigned:.2f}%)")
assigned_helpers_df.head()


#%% split both main and helper trajectories into heads and tails
# this runs in 6misns 30 but is it correct?
import pandas as pd
from collections import defaultdict
from tqdm import tqdm
import numpy as np

# Make sure your assigned_helpers_df has columns: 
# ['main_row_uid', 'helper_tid', 'clkpassed']

# Add columns to track swaps
t['tid_subid_after_swap'] = t['tid_subid']
t['swap_pair_id'] = pd.NA
t['head_end_flag'] = False
t['tail_start_flag'] = False

# Precompute trajectory indices to speed up slicing
tid_index_map = t.groupby('tid_subid').groups 
# Precompute row_uid → point_id_t mapping
row_uid_to_pid = t.set_index('row_uid')['point_id_t'].to_dict()

# Unique swap counter
swap_counter = 0

# Process swaps in order of main trajectory and point_id_t
assigned_helpers_df = assigned_helpers_df.merge(
    t[['row_uid', 'tid_subid', 'point_id_t']],
    left_on='main_row_uid', right_on='row_uid', how='left'
).sort_values(['tid_subid', 'point_id_t'])

# Track which helper split rows have been used
used_helper_rows = set()

for _, swap in tqdm(assigned_helpers_df.iterrows(), total=len(assigned_helpers_df), desc="Processing swaps"):

    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid     = t.loc[t.row_uid == main_row_uid, 'tid_subid'].values[0]
    clkpassed    = swap['clkpassed']
    helper_tid   = swap['helper_tid']

    # --- Split main trajectory ---
    main_pid = row_uid_to_pid[main_row_uid]
    main_idx  = tid_index_map[main_tid]

    main_mask_head = main_idx[ t.loc[main_idx, 'point_id_t'] <= main_pid ]
    main_mask_tail = main_idx[ t.loc[main_idx, 'point_id_t'] >  main_pid ]

    # Head/tail flags
    t.loc[main_mask_head, 'head_end_flag'] = t.loc[main_mask_head, 'point_id_t'] == main_pid
    t.loc[main_mask_tail, 'tail_start_flag'] = t.loc[main_mask_tail, 'point_id_t'] == main_pid + 1

    # Update tails with helper_tid
    t.loc[main_mask_tail, 'tid_subid_after_swap'] = helper_tid
    t.loc[main_mask_tail, 'swap_pair_id'] = swap_counter

    # --- Split helper trajectory ---
    helper_idx = tid_index_map[helper_tid]

    # Eligible helper points: same cloaking area, same time_bin
    helper_points = t.loc[helper_idx]
    helper_points = helper_points[helper_points['intersects_cloaking'] == clkpassed]
    if len(helper_points) == 0:
        continue  # safety

    # Exclude rows already used for other swaps
    helper_points = helper_points[~helper_points['row_uid'].isin(used_helper_rows)]

    # Randomly choose a split point
    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_split_row['row_uid'])

    helper_mask_head = helper_idx[ t.loc[helper_idx, 'point_id_t'] <= helper_split_pid ]
    helper_mask_tail = helper_idx[ t.loc[helper_idx, 'point_id_t'] >  helper_split_pid ]

    t.loc[helper_mask_head, 'head_end_flag'] = t.loc[helper_mask_head, 'point_id_t'] == helper_split_pid
    t.loc[helper_mask_tail, 'tail_start_flag'] = t.loc[helper_mask_tail, 'point_id_t'] == helper_split_pid + 1

    # Update tails with main_tid
    t.loc[helper_mask_tail, 'tid_subid_after_swap'] = main_tid
    t.loc[helper_mask_tail, 'swap_pair_id'] = swap_counter

print(f"Swapping completed for {swap_counter} assigned pairs.")

#%% look at swapping outcome
swap_counter

#%% 
t.head()


#%% 
print(t.head_end_flag.unique())
print(t.tail_start_flag.unique())
print(t.swap_pair_id.unique())

#%%
t.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_swapped_cloakinggaps.parquet")
#%% export individal trajectories that have been swapped
import os

output_folder = r"D:\paper3\Data\output\CloakingBasedSwapping\tid_subid_after_swap_parquets2"
os.makedirs(output_folder, exist_ok=True)

# Only trajectories that were modified by swapping
swapped_tids = t.loc[t['tid_subid_after_swap'] != t['tid_subid'], 'tid_subid_after_swap'].unique()

for tid_after in swapped_tids:
    subset = t[t['tid_subid_after_swap'] == tid_after]
    
    filename = f"{tid_after}.parquet"
    filepath = os.path.join(output_folder, filename)
    
    subset.to_parquet(filepath, index=False)


#%% something seemed to be of about the swapps 
assigned_helpers_df = pd.DataFrame(assigned, columns=['main_row_uid', 'helper_tid', 'clkpassed'])


import pandas as pd
from tqdm import tqdm
import numpy as np
import os


# --- STEP 0: Add columns to track swaps ---
t['tid_subid_orig'] = t['tid_subid']        # original trajectory ID
t['tid_subid_after_swap'] = t['tid_subid']  # updated trajectory after swaps
t['swap_pair_id'] = pd.NA
t['head_end_flag'] = False
t['tail_start_flag'] = False

# Precompute row_uid → point_id_t mapping
row_uid_to_pid = t.set_index('row_uid')['point_id_t'].to_dict()

# Precompute trajectory indices for faster slicing
tid_index_map = t.groupby('tid_subid').groups

# Track helper rows that have already been used for splitting
used_helper_rows = set()

# Initialize swap counter
swap_counter = 0

# Merge main_row info (point_id_t) for sorting by trajectory and order
assigned_helpers_df = assigned_helpers_df.merge(
    t[['row_uid', 'tid_subid', 'point_id_t']],
    left_on='main_row_uid', right_on='row_uid', how='left'
).sort_values(['tid_subid', 'point_id_t'])

# --- STEP 1: Process swaps sequentially ---
for _, swap in tqdm(assigned_helpers_df.iterrows(), total=len(assigned_helpers_df), desc="Processing swaps"):

    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid_orig = t.loc[t.row_uid == main_row_uid, 'tid_subid_orig'].values[0]
    helper_tid = swap['helper_tid']
    clkpassed = swap['clkpassed']

    # --- Split main trajectory ---
    main_pid = row_uid_to_pid[main_row_uid]
    main_idx = tid_index_map[main_tid_orig]

    main_mask_head = main_idx[t.loc[main_idx, 'point_id_t'] <= main_pid]
    main_mask_tail = main_idx[t.loc[main_idx, 'point_id_t'] > main_pid]

    # Head/tail flags
    t.loc[main_mask_head, 'head_end_flag'] = t.loc[main_mask_head, 'point_id_t'] == main_pid
    t.loc[main_mask_tail, 'tail_start_flag'] = t.loc[main_mask_tail, 'point_id_t'] == main_pid + 1

    # Update main tail with helper trajectory
    t.loc[main_mask_tail, 'tid_subid_after_swap'] = helper_tid
    t.loc[main_mask_tail, 'swap_pair_id'] = swap_counter

    # --- Split helper trajectory ---
    helper_idx = tid_index_map[helper_tid]

    # Eligible helper points: same cloaking gap (clkpassed)
    helper_points = t.loc[helper_idx]
    helper_points = helper_points[helper_points['intersects_cloaking'] == clkpassed]

    # Exclude points already used in another swap
    helper_points = helper_points[~helper_points['row_uid'].isin(used_helper_rows)]
    if len(helper_points) == 0:
        continue  # safety check

    # Pick a random split point
    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_split_row['row_uid'])

    helper_mask_head = helper_idx[t.loc[helper_idx, 'point_id_t'] <= helper_split_pid]
    helper_mask_tail = helper_idx[t.loc[helper_idx, 'point_id_t'] > helper_split_pid]

    # Head/tail flags
    t.loc[helper_mask_head, 'head_end_flag'] = t.loc[helper_mask_head, 'point_id_t'] == helper_split_pid
    t.loc[helper_mask_tail, 'tail_start_flag'] = t.loc[helper_mask_tail, 'point_id_t'] == helper_split_pid + 1

    # Update helper tail with main trajectory
    t.loc[helper_mask_tail, 'tid_subid_after_swap'] = main_tid_orig
    t.loc[helper_mask_tail, 'swap_pair_id'] = swap_counter

print(f"Swapping completed for {swap_counter} assigned pairs.")
t.head()


#%% debugging - this must all be linked 
# inspect helper assignment
assigned_helpers_df = pd.DataFrame(assigned, columns=['main_row_uid', 'helper_tid', 'clkpassed'])
assigned_helpers_df.head()
# all this tells me is the last point before a cloaking gap - essentially identifying the cloaking gap
# and the helper trajectory and the cloking geometry 

# does not provide info on time bin or points that qualify the helper tid to be a helper/ the points on which the split will be based on

#%% what this does tell us: location in sensitive df and helping trajectory to swap with
print(len(assigned_helpers_df))                 # 11,740 cloaking gaps
print(assigned_helpers_df.clkpassed.nunique())  # caused by 177 cloaking gaps
                                                # covered by 
print(assigned_helpers_df.helper_tid.nunique()) # 7,069 helper trajectories
                                                # some helper trajectories are used multiple times

# would it help to know from how many tid the 11,740 cloaking gaps are coming from 
print(main_rows[main_rows['row_uid'].isin(assigned_helpers_df.main_row_uid.unique())].tid_subid.nunique()) # 6,003

#%% do main and helper trajectories overlap?
main_tids = set(
    main_rows.loc[
        main_rows['row_uid'].isin(assigned_helpers_df.main_row_uid),
        'tid_subid'
    ]
)
helper_tids = set(assigned_helpers_df.helper_tid)
overlap = main_tids.intersection(helper_tids)
print("Number of overlapping trajectories:", len(overlap)) # 3,022

#%% actually: must assigne swapping point, not simplt helper trajectory 
print(main_rows_with_helpers.columns)

# drop the rows that have not been assigned a trajectory helper
cg_whelpers = main_rows_with_helpers[main_rows_with_helpers['helper_tid'].notna()]
cg_whelpers = main_rows_with_helpers[main_rows_with_helpers['helper_tid'].notna()]
print(len(cg_whelpers)) # 11740 - the ones that have been assigned a helper trajeorty
cg_whelpers.head()

#%% ensure cloking geometries are the same
print('have cloaking geometries been assigned correctly?', (cg_whelpers['clkpassed'] == cg_whelpers['HeadEndCloakingAreaId']).any())

#%% now actually assign a swpaping point in the helper trajectory
# randomly pick one of the helper_tid points as the swapping points
# however, must make sure that the point is within same timebin, as the identified tid might pass the matching cloaking area multiple times in different time bins
# pre-filter the helping trajectory df to the selected tid_subid and clkpssed so that we only need to filter for matching time bins

# In cg_whelpers
cg_whelpers['matching_candidate_id'] = (
    cg_whelpers['clkpassed'].astype(str) + '_' +
    cg_whelpers['time_bin'].astype(str) + '_' +
    cg_whelpers['helper_tid'].astype(str)
)

# In helper_candidates
helper_candidates['matching_candidate_id'] = (
    helper_candidates['clkpassed'].astype(str) + '_' +
    helper_candidates['time_bin'].astype(str) + '_' +
    helper_candidates['tid_subid'].astype(str)
)
# I think we can reduce the columns of helper_candidates as we are only interested in the point id
helper_candidates_r = helper_candidates[['matching_candidate_id', 'row_uid']].copy()
helper_candidates_r = helper_candidates_r.rename(columns={'row_uid': 'helper_row_uid'})

# Merge the two
print(len(cg_whelpers)) # 11740
helper_candidates_pool = cg_whelpers.merge(helper_candidates_r, on='matching_candidate_id', how='left', suffixes=('_cg', '_t'))
print(len(helper_candidates_pool))                          # 79,882 - number of points to choose from
print(helper_candidates_pool.helper_row_uid.nunique())      # 78,696 - not every point is unique! some points can be used for different trajectories to swap at?
print(helper_candidates_pool.matching_candidate_id.nunique()) 
# are there nan?
print(helper_candidates_pool.helper_row_uid.isna().any()) # False, good
helper_candidates_pool.head()



#%%%
helper_candidates_pool[helper_candidates_pool.helper_row_uid.duplicated()]


#%% why are there duplicate helper_row_uid values
# Find which helper_row_uid values appear more than once
duplicates = helper_candidates_pool['helper_row_uid'].value_counts()
duplicates = duplicates[duplicates > 1]

print("Number of helper_row_uid values appearing multiple times:", len(duplicates)) # 1186
print(duplicates.reset_index()['count'].median())
print(duplicates.reset_index()['count'].max()) # max duplicate is 2

# Get the actual rows for these duplicated helper_row_uid values
dup_rows = helper_candidates_pool[
    helper_candidates_pool['helper_row_uid'].isin(duplicates.index)
]

dup_rows # but they are not full row duplicates




#%% this must be an issue in the helper_candidates df already
print(helper_candidates.row_uid.nunique()) # 7334941
print(len(helper_candidates)) # 7377573
duplicates = helper_candidates['row_uid'].value_counts()
duplicates = duplicates[duplicates > 1]

print("Number of row_uid values appearing multiple times:", len(duplicates)) # 33235 - even more
print(duplicates.reset_index()['count'].median())
print(duplicates.reset_index()['count'].max()) # max duplicate is 3

#%% they should not be duplicates in t
print(t.row_uid.nunique()) # 7334941
print(len(t)) # 7334941
duplicates = t['row_uid'].value_counts()
duplicates = duplicates[duplicates > 1]

print("Number of row_uid values appearing multiple times:", len(duplicates)) # 0
print(duplicates.reset_index()['count'].median())
print(duplicates.reset_index()['count'].max()) # nan







#%% Decision: drop one of the duplicate assignments
# inspect helper assignment
assigned_helpers_df = pd.DataFrame(assigned, columns=['main_row_uid', 'helper_tid', 'clkpassed'])
assigned_helpers_df.head()

#%% issue: some tid_subid are assigned to multiple cloaking geom (fine)
# BUT those cloaking geom overlap (spatially)
# identify these duplicates at intersecting cloaking areas and drop one of them from being an assigned helper

print('number of active clk areas assigned to a helper trajectory to actively help at')
print('max: ', assigned_helpers_df.groupby('helper_tid')['clkpassed'].nunique().reset_index()['clkpassed'].max()) # 12
print('median: ', assigned_helpers_df.groupby('helper_tid')['clkpassed'].nunique().reset_index()['clkpassed'].median()) # 1 - good
print('min: ', assigned_helpers_df.groupby('helper_tid')['clkpassed'].nunique().reset_index()['clkpassed'].min()) # 1 - expected

prop = (assigned_helpers_df.groupby('helper_tid')['clkpassed'].nunique() > 1).mean()
print('% of helper_tid assigned to more than one cloaking gap:', f'{prop:.2%}')

print(assigned_helpers_df.helper_tid.nunique())
assigned_helpers_df_duplicates = assigned_helpers_df.groupby('helper_tid')['clkpassed'].nunique().loc[lambda x: x > 1].index.tolist()
print(len(assigned_helpers_df_duplicates))# 2725


#%% identify overlapping cloaking geom
print(len(assigned_helpers_df))                         # 11,740 tid assigned to cloaking gaps
print(assigned_helpers_df.main_row_uid.nunique())       # 11,740 cloaking gaps
print(assigned_helpers_df.helper_tid.nunique())         # 7,069 tid to cover these cloaking gaps
print(assigned_helpers_df.clkpassed.nunique())          # at 177 different cloaking geometries
print(len(assigned_helpers_df_duplicates))
assigned_helpers_df_multi = assigned_helpers_df[assigned_helpers_df['helper_tid'].isin(assigned_helpers_df_duplicates)]
print(len(assigned_helpers_df_multi))                   # 7,396
print(assigned_helpers_df_multi.helper_tid.nunique())   # 2,725 - number of helper tid assigned more than one cloaking gap

#%% (0) must add geometry of clkpassed
cloakinggeom = gpd.read_parquet(r"d:\paper3\Data\trajectories\cloakingGeom_2sigLoc_100150m.parquet")
# only a few columns of interest here
# cloakingArea_id and cloaking_geometry
cloakinggeom = cloakinggeom[['cloakingArea_id', 'cloaking_geometry']]
print(cloakinggeom.crs)
cloakinggeom.rename(columns={'cloakingArea_id': 'clkpassed'}, inplace=True)
# add geom to df
assigned_helpers_df_multi = assigned_helpers_df_multi.merge(cloakinggeom, on = 'clkpassed', how='left')
# ensure df is now a gdf
assigned_helpers_df_multi = gpd.GeoDataFrame(
    assigned_helpers_df_multi,
    geometry='cloaking_geometry',  
    crs=cloakinggeom.crs  
)
print(type(assigned_helpers_df_multi))
assigned_helpers_df_multi.head()



#%% (1) identify overlapping cloaking geom
pairs = assigned_helpers_df_multi.sjoin(
    assigned_helpers_df_multi,
    predicate='intersects',
    how='inner'
) # includes different helpers intersecting with each other and self-intersection  - not of interestes here
pairs = pairs[pairs.index != pairs.index_right]
pairs = pairs[pairs['helper_tid_left'] == pairs['helper_tid_right']] # only interested in overlaps of cloaking geometries for the same tid

# which two gaps overlap?
pairs[['helper_tid_left', 
        'main_row_uid_left', 'clkpassed_left',  
        'main_row_uid_right', 'clkpassed_right']]  

# helper_tid_left and _right are the same
# ckpassed and main_tid are fidderent

# one row is one (potential?) conflict
# but I need to know wheter a helper tid is experienceing more than one conflict

#%% overlaps are recorded both as left to right and right to left, drop the same overlaps
print(len(pairs)) # 406
pairs['pair'] = pairs.apply(
    lambda row: tuple(sorted([row['clkpassed_left'], row['clkpassed_right']])),
    axis=1
)
# look at one example helper
print(pairs[pairs['helper_tid_left'] == pairs.helper_tid_left.unique()[3]]['pair'].nunique()) # 1
print(pairs[pairs['helper_tid_left'] == pairs.helper_tid_left.unique()[3]]['pair'].unique())
pairs[pairs['helper_tid_left'] == pairs.helper_tid_left.unique()[3]][['helper_tid_left', 'main_row_uid_left', 'clkpassed_left', 'main_row_uid_right', 'clkpassed_right', 'pair']]
# the same overlap is idenfified twice

#%% how many "duplicate assignments" overlap?
# drop duplicates **per helper**
pairs_unique = pairs.drop_duplicates(subset=['helper_tid_left', 'pair'])
print(len(pairs_unique)) # 203 --> 1.6% out of the 11k assigned cloaking gaps


#%% now drop one of the duplicates
# two approaches, depending on how many overlaps the helper tid has
pair_counts = pairs_unique['helper_tid_left'].value_counts()
helpers_more_than_1 = pair_counts[pair_counts > 1]
len(helpers_more_than_1) # 18 trajectories have more than 1 overlap
proportion = len(helpers_more_than_1) / len(pair_counts)
print(f"{proportion:.2%}")

helpers_more_than_1 = helpers_more_than_1.reset_index().helper_tid_left.unique()
pairs_unique_1 = pairs_unique[~pairs_unique['helper_tid_left'].isin(helpers_more_than_1)]
pairs_unique_o1 = pairs_unique[pairs_unique['helper_tid_left'].isin(helpers_more_than_1)]
print(len(pairs_unique_o1)+len(pairs_unique_1) == len(pairs_unique))

# (a) one overlap only - randomly choose one to keep
# 1 - only one overlap, we can (randomly) chose one of the two main_row_uid (left or right) to drop/keep
# (this could be optimised by looking intot the target trajectories, have they been swapped at other cloaking locations etc)
# helpers with one overlapping pair only: randomly chose one cloaking gap (main_row_uid) to keep
# the cloaking gap to keep is stored in a new column
import numpy as np
# for each row, randomly pick either main_row_uid_left or main_row_uid_right to fill main_row_uid_noOverlap
# apply this to tid_s with only one overlap only 
pairs_unique_1['main_row_uid_noOverlap'] = pairs_unique_1.apply(
    lambda row: np.random.choice([row['main_row_uid_left'], row['main_row_uid_right']]),
    axis=1
)
pairs_unique_1[['main_row_uid_noOverlap', 'main_row_uid_left', 'main_row_uid_right']]
#pairs_unique_1.main_row_uid_noOverlap.unique() # these are the ones we keep (or drop, doesn't matter)

#%% (b) multiple overlaps - must pay more attention
pairs_unique_o1 = pairs_unique_o1.sort_values(by=['helper_tid_left', 'clkpassed_left'])
print(pairs_unique_o1.head(2)['pair'].unique())
pairs_unique_o1[['helper_tid_left', 'clkpassed_left', 'clkpassed_right', 'pair']].head(2) # here, first 2 are same helper tid
# and 

#%%
cloakinggeom[cloakinggeom['clkpassed'].isin(['2_488e488998d387ccd0ca374eb8c9cdd1be93ebae', '2_ba47b357de1d5aee4867b84fecce545f3d00aba0', 
                                             '2_975144d4e4fac3c5e7a0fd00ee6bc07fafe37548', '2_d8e1b548c25df0c24d8d8d493d4e6db0ad25c792'])].to_parquet(r"D:\paper3\Data\tetsing\cloakedBasedtetsing/cloakinggeomOverlap.parquet")


#%%
print(pairs_unique_o1[pairs_unique_o1['helper_tid_left']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642'].pair.unique())
print(pairs_unique_o1[pairs_unique_o1['helper_tid_left']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642'][['clkpassed_left', 'clkpassed_right']])

#%%
t[t['tid_subid']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642'].to_parquet(r"D:\paper3\Data\tetsing\cloakedBasedtetsing/cloakinggeomOverlap_thelper.parquet")


#%% look at the other helpers with more than one cloaking geometry overlap
pairs[pairs['helper_tid_left'].isin(pairs_unique_o1.helper_tid_left.unique())].to_parquet(r"D:\paper3\Data\tetsing\cloakedBasedtetsing/cloakinggeomOverlap_over1_all.parquet")


#%% isolated vs connected overlaps
# example of isolated overlap 20200715_800816e9960edd7e4bd41344a2f75141d99068f5_6339
print(pairs_unique_o1[pairs_unique_o1['helper_tid_left']=='20200715_800816e9960edd7e4bd41344a2f75141d99068f5_6339'].pair.unique())
pairs_unique_o1[pairs_unique_o1['helper_tid_left']=='20200715_800816e9960edd7e4bd41344a2f75141d99068f5_6339'][['clkpassed_left', 'clkpassed_right']]

#%%
problem_helpers = []

for helper, group in pairs_unique_o1.groupby('helper_tid_left'):
    
    # combine both columns into one list
    all_clk = pd.concat([
        group['clkpassed_left'],
        group['clkpassed_right']
    ])
    
    # count occurrences
    counts = all_clk.value_counts()
    
    # does any appear more than once?
    if (counts > 1).any():
        problem_helpers.append(helper)

pairs_unique_o1_connected = pairs_unique_o1[pairs_unique_o1['helper_tid_left'].isin(problem_helpers)]
pairs_unique_o1_isolated = pairs_unique_o1[~pairs_unique_o1['helper_tid_left'].isin(problem_helpers)]
print(len(pairs_unique_o1_connected)+ len(pairs_unique_o1_isolated)==len(pairs_unique_o1))

#%% handling isolated ones - same approach as to randomly chosing one out of two overlaps (pairs_unique_1)
print(len(pairs_unique_1)) # this affects 8 cloaking gaps (droped 160/ kept 160)

pairs_unique_o1_isolated['main_row_uid_noOverlap'] = pairs_unique_o1_isolated.apply(
    lambda row: np.random.choice([row['main_row_uid_left'], row['main_row_uid_right']]),
    axis=1
)
print(len(pairs_unique_o1_isolated)) # this affects 8 cloaking gaps (droped 8/ kept 8)
pairs_unique_o1_isolated[['main_row_uid_noOverlap', 'main_row_uid_left', 'main_row_uid_right']]


#%% handling connected ones
pairs_unique_o1_connected_long = (
    pairs_unique_o1_connected
    .melt(
        id_vars=['helper_tid_left'],
        value_vars=['clkpassed_left', 'clkpassed_right'],
        value_name='clkpassed'
    )
)

pairs_unique_o1_connected_counts = (
    pairs_unique_o1_connected_long
    .groupby(['helper_tid_left', 'clkpassed'])
    .size()
    .reset_index(name='clkpassed_usage_count')
)
pairs_unique_o1_connected_counts

# could add this back to the df
#pairs_unique_o1_connected = pairs_unique_o1_connected.merge(
#    pairs_unique_o1_connected_counts,
#    left_on=['helper_tid_left', 'clkpassed_left'],
#    right_on=['helper_tid_left', 'clkpassed'],
#    how='left'
#).rename(columns={'clkpassed_usage_count': 'clkpassed_left_count'}).drop(columns='clkpassed')

#pairs_unique_o1_connected = pairs_unique_o1_connected.merge(
#    pairs_unique_o1_connected_counts,
#    left_on=['helper_tid_left', 'clkpassed_right'],
#    right_on=['helper_tid_left', 'clkpassed'],
#    how='left'
#).rename(columns={'clkpassed_usage_count': 'clkpassed_right_count'}).drop(columns='clkpassed')

#%%
pairs_unique_o1_connected_counts[pairs_unique_o1_connected_counts['helper_tid_left']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642']

#%%
pairs_unique_o1_connected[pairs_unique_o1_connected['helper_tid_left']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642'][['main_row_uid_left', 'clkpassed_left', 'main_row_uid_right', 'clkpassed_right']]
#%% I want to keep and 
# both are cklpassed_right 
# that menas for tehse rows I have to take the value of main_row_uid_right for my 'chosen' colum
# and drop the last line where/ have na for the chosen column 
# could also take a uid approach. I do not chose the ones that have diplicates, but the ones that are unique\
print(len(pairs_unique_o1_connected))

import numpy as np
import pandas as pd

# Step 1 — build a long version just to compute counts
long_uid = (
    pairs_unique_o1_connected[['helper_tid_left', 'main_row_uid_left', 'main_row_uid_right']]
    .melt(
        id_vars='helper_tid_left',
        value_vars=['main_row_uid_left', 'main_row_uid_right'],
        value_name='main_row_uid'
    )
)

# Step 2 — compute counts per helper + uid
uid_counts = (
    long_uid
    .groupby(['helper_tid_left', 'main_row_uid'])
    .size()
)

# Step 3 — map counts back to left and right columns
pairs_unique_o1_connected['left_count'] = list(
    zip(pairs_unique_o1_connected['helper_tid_left'], pairs_unique_o1_connected['main_row_uid_left'])
)
pairs_unique_o1_connected['left_count'] = pairs_unique_o1_connected['left_count'].map(uid_counts)

pairs_unique_o1_connected['right_count'] = list(
    zip(pairs_unique_o1_connected['helper_tid_left'], pairs_unique_o1_connected['main_row_uid_right'])
)
pairs_unique_o1_connected['right_count'] = pairs_unique_o1_connected['right_count'].map(uid_counts)

# Step 4 — create final column
pairs_unique_o1_connected['main_row_uid_noOverlap'] = np.where(
    pairs_unique_o1_connected['left_count'] == 1,
    pairs_unique_o1_connected['main_row_uid_left'],
    np.where(
        pairs_unique_o1_connected['right_count'] == 1,
        pairs_unique_o1_connected['main_row_uid_right'],
        np.nan
    )
)

print(len(pairs_unique_o1_connected)) # nothing lost
print(pairs_unique_o1_connected.main_row_uid_noOverlap.nunique()) # 22 assigned - I think this should be integers for the final selection step
pairs_unique_o1_connected[['helper_tid_left', 'main_row_uid_left' ,'main_row_uid_right', 'main_row_uid_noOverlap']].head()
# multiple assigned per tid (good) but they should not be overlapping anymore. if they were overlapping they have been dropped (nan)




#%% (3) how do I update my assigned_helpers_df so that the overlaps are removed?
# because
print(assigned_helpers_df.main_row_uid.nunique())   # 11,740 cloaking gaps
print(len(assigned_helpers_df))                     # 11,740 
# i.e., each cloaking gap is only listed once
# we can safely remove the ones we want to drop because the tid used has been assigned to overlapping cloaking geometries

print(assigned_helpers_df.helper_tid.nunique())         # 7,069 tid to cover these cloaking gaps
print(assigned_helpers_df.clkpassed.nunique())          # at 177 different cloaking geometries
print(len(assigned_helpers_df_duplicates))
#assigned_helpers_df_multi = assigned_helpers_df[assigned_helpers_df['helper_tid'].isin(assigned_helpers_df_duplicates)]
print(len(assigned_helpers_df_multi))                   # 7,396
print(assigned_helpers_df_multi.helper_tid.nunique())   # 2,725 - number of helper tid assigned more than one cloaking gap

# assigned_helpers_df:          11,740 cloaking gaps have been assigned initially for swapping
# assigned_helpers_df_multi:    7,396 but assigned_helpers_df_multi of those gaps are covered by helper trajectories who help more than once
# multi assigment is generally ok, as long as the assigned gaps do not overlap
print(assigned_helpers_df_multi.main_row_uid.nunique()) # 7396
# pair: we than did a spatial join to find overlaps (and removed overlaps with itself)
# this join was set to inner, i.e., we dropped all other
# pairs = assigned_helpers_df_multi.sjoin(assigned_helpers_df_multi, predicate='intersects', how='inner')

# must find the main_row_uid of the helpers that are multi assigned, but do not overlap
overlap_unique_ids = pd.unique(pairs[['main_row_uid_left', 'main_row_uid_right']].values.ravel())
overlap_unique_ids = overlap_unique_ids.tolist()
print(assigned_helpers_df_multi.main_row_uid.nunique())
#381 out of the 7396 are problematic 
# remove these from the list and add back in the ones to keep later
assigned_helpers_df_mult_list = assigned_helpers_df_multi.main_row_uid.unique()

assigned_helpers_df_mult_list_noOverlaps = list(
    set(assigned_helpers_df_mult_list) - set(overlap_unique_ids)
)
print(len(assigned_helpers_df_mult_list_noOverlaps)) # 7015, which is exactly 7396-381

#%% now add the problematic ids that we decided to keep back
# the filtered problematic main_row_uids come from 3 dfs
#pairs_unique_1[['main_row_uid_noOverlap', 'main_row_uid_left', 'main_row_uid_right']]
#pairs_unique_o1_isolated[['main_row_uid_noOverlap', 'main_row_uid_left', 'main_row_uid_right']]
#pairs_unique_o1_connected[['main_row_uid_noOverlap', 'main_row_uid_left' ,'main_row_uid_right']].head()

# combined, main_row_uid_noOverlap is a list of problematic main_row_uids to keep
main_row_uid_noOverlap_list = pd.concat([
    pairs_unique_1['main_row_uid_noOverlap'],
    pairs_unique_o1_isolated['main_row_uid_noOverlap'],
    pairs_unique_o1_connected['main_row_uid_noOverlap']
]).dropna().astype(int).tolist()

print(len(main_row_uid_noOverlap_list)) # 190

assigned_helpers_df_mult_list_noOverlaps.extend(main_row_uid_noOverlap_list)
print(len(assigned_helpers_df_mult_list_noOverlaps)) # 7205 valid assigment of helpers to help multiple times
# (previously 7396, removed the problematic ones)

#%% update assigned helpers df
# remove the problematic main_row_uids
print(len(assigned_helpers_df_mult_list))
print(len(assigned_helpers_df_mult_list_noOverlaps))

assigned_helpers_clkg_toRemove = list(
    set(assigned_helpers_df_mult_list)
    - set(assigned_helpers_df_mult_list_noOverlaps)
)
len(assigned_helpers_clkg_toRemove) # 191 --> remove these from assigned_helpers_df




#%% updating assigned helpers df
valid_assigned_helpers_df = assigned_helpers_df[~assigned_helpers_df['main_row_uid'].isin(assigned_helpers_clkg_toRemove)]
valid_assigned_helpers_df


#%% now randomly select a "swapping point" for each helper

