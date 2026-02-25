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

#%% half vecorised, ensuring sequential swapping,, still 4 hours processing time
import pandas as pd
from tqdm import tqdm
import numpy as np

# Make sure your assigned_helpers_df has these columns:
# ['main_row_uid', 'helper_tid', 'clkpassed']

# Add new columns to track swaps
t['tid_subid_after_swap'] = t['tid_subid']
t['swap_pair_id'] = pd.NA
t['head_end_flag'] = False
t['tail_start_flag'] = False

# Merge to get main trajectory info
assigned_helpers_df = assigned_helpers_df.merge(
    t[['row_uid', 'tid_subid', 'point_id_t']],
    left_on='main_row_uid',
    right_on='row_uid',
    how='left'
).rename(columns={'tid_subid':'main_tid','point_id_t':'main_point_id_t'})

# Sort by main trajectory and point order
assigned_helpers_df = assigned_helpers_df.sort_values(['main_tid','main_point_id_t']).reset_index(drop=True)
assigned_helpers_df['swap_pair_id'] = range(1, len(assigned_helpers_df)+1)

# --- Vectorized main trajectory split ---
# Create a map for fast lookup
main_split_map = assigned_helpers_df.set_index('main_row_uid')[['main_tid','main_point_id_t','swap_pair_id']]

for main_row_uid, row in tqdm(main_split_map.iterrows(), total=len(main_split_map), desc="Splitting main trajectories"):
    main_tid = row['main_tid']
    split_pid = row['main_point_id_t']
    swap_id = row['swap_pair_id']

    mask_head = (t.tid_subid == main_tid) & (t.point_id_t <= split_pid)
    mask_tail = (t.tid_subid == main_tid) & (t.point_id_t >  split_pid)

    t.loc[mask_head, 'head_end_flag'] = (t.point_id_t == split_pid)
    t.loc[mask_tail, 'tail_start_flag'] = (t.point_id_t == split_pid + 1)  # or next row_uid if preferred

# --- Helper trajectory splits (loop only over assigned swaps) ---
for _, swap in tqdm(assigned_helpers_df.iterrows(), total=len(assigned_helpers_df), desc="Splitting helper trajectories"):
    helper_tid = swap['helper_tid']
    clkpassed  = swap['clkpassed']
    swap_id    = swap['swap_pair_id']
    main_tid   = swap['main_tid']

    # Eligible helper points inside the assigned cloaking gap
    helper_points = t[(t.tid_subid == helper_tid) & (t.clkpassed == clkpassed)]
    if len(helper_points) == 0:
        continue

    # Randomly choose split point
    split_row = helper_points.sample(1).iloc[0]
    split_pid = split_row['point_id_t']

    mask_head = (t.tid_subid == helper_tid) & (t.point_id_t <= split_pid)
    mask_tail = (t.tid_subid == helper_tid) & (t.point_id_t >  split_pid)

    t.loc[mask_head, 'head_end_flag'] = (t.point_id_t == split_pid)
    t.loc[mask_tail, 'tail_start_flag'] = (t.point_id_t == split_pid + 1)

    # Update tail points after swap
    t.loc[mask_tail, 'tid_subid_after_swap'] = main_tid
    t.loc[mask_tail, 'swap_pair_id'] = swap_id

print("All assigned swaps processed successfully.")







#%% safe but slow version (8 hours run time)
from tqdm import tqdm
import pandas as pd

# Make sure your assigned_helpers_df has these columns:
# ['main_row_uid', 'helper_tid', 'clkpassed']

# Add new columns to the main dataframe to track swaps
t['tid_subid_after_swap'] = t['tid_subid']
t['swap_pair_id'] = pd.NA
t['head_end_flag'] = False   # True for the last point of a head
t['tail_start_flag'] = False # True for the first point of a tail

# Unique swap ID counter
swap_counter = 0

# Merge main_row point info and sort by trajectory + point order
assigned_helpers_df = assigned_helpers_df.merge(
    t[['row_uid', 'tid_subid', 'point_id_t']], 
    left_on='main_row_uid', right_on='row_uid', how='left'
)
assigned_helpers_df = assigned_helpers_df.sort_values(
    ['tid_subid', 'point_id_t']
)

# --- Loop over each assigned swap with tqdm progress bar ---
for _, swap in tqdm(assigned_helpers_df.iterrows(), 
                    total=len(assigned_helpers_df), 
                    desc="Processing swaps"):

    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid     = t.loc[t.row_uid == main_row_uid, 'tid_subid'].values[0]
    clkpassed    = swap['clkpassed']
    helper_tid   = swap['helper_tid']
    
    # --- Split main trajectory ---
    main_split_idx = t.loc[t.row_uid == main_row_uid, 'point_id_t'].values[0]
    main_mask_head = (t.tid_subid == main_tid) & (t.point_id_t <= main_split_idx)
    main_mask_tail = (t.tid_subid == main_tid) & (t.point_id_t >  main_split_idx)
    
    # Mark head_end and tail_start flags
    t.loc[main_mask_head, 'head_end_flag'] = (t.point_id_t == main_split_idx)
    t.loc[main_mask_tail, 'tail_start_flag'] = (t.point_id_t == main_split_idx + 1)
    
    # Update tid_subid_after_swap for main tail
    t.loc[main_mask_tail, 'tid_subid_after_swap'] = helper_tid
    t.loc[main_mask_tail, 'swap_pair_id'] = swap_counter
    
    # --- Split helper trajectory ---
    helper_candidates_points = t[
        (t.tid_subid == helper_tid) &
        (t.intersecting_cloaking_ids == clkpassed)
    ]
    if len(helper_candidates_points) == 0:
        continue  # safety check

    # Pick a random point for the split among eligible points
    helper_split_row = helper_candidates_points.sample(1).iloc[0]
    helper_split_idx = helper_split_row['point_id_t']
    
    helper_mask_head = (t.tid_subid == helper_tid) & (t.point_id_t <= helper_split_idx)
    helper_mask_tail = (t.tid_subid == helper_tid) & (t.point_id_t >  helper_split_idx)
    
    # Mark head_end and tail_start flags
    t.loc[helper_mask_head, 'head_end_flag'] = (t.point_id_t == helper_split_idx)
    t.loc[helper_mask_tail, 'tail_start_flag'] = (t.point_id_t == helper_split_idx + 1)
    
    # Update tid_subid_after_swap for helper tail
    t.loc[helper_mask_tail, 'tid_subid_after_swap'] = main_tid
    t.loc[helper_mask_tail, 'swap_pair_id'] = swap_counter

print("Swapping completed for all assigned pairs")