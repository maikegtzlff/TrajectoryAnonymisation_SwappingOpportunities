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
print(t.tid_subid.nunique()) # 19,189 trajectories
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


#%% debugging 
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
t[t['tid_subid']=='20191126_7b7528151b18b954003452674cd3c425d97f92a1_2642'].to_parquet(r"D:\paper3\Data\tetsing\cloakedBasedtetsing/cloakinggeomOverlap_thelper.parquet")

# look at the other helpers with more than one cloaking geometry overlap
pairs[pairs['helper_tid_left'].isin(pairs_unique_o1.helper_tid_left.unique())].to_parquet(r"D:\paper3\Data\tetsing\cloakedBasedtetsing/cloakinggeomOverlap_over1_all.parquet")


#%% isolated vs connected overlaps
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

#%% export these!
valid_assigned_helpers_df.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/valid_assigned_helpers_df.parquet")
#%% can now run the swapping based on valid_assigned_helpers_df but must ensure that the "new_tid" column gets handeled correctly
# i.e., can't start out as the orig tid because than unhandled tid segments are assigned to "the new final tid" 
# when these are actually heads and tails that have been swapped

# must also look into the handing of synthtetic trajectory points
# if the cloaking gap is 
# actually, what does main_row_uid give me? Is that the targets trajectories end point?
# 

#%% split both main and helper trajectories into heads and tails
# prep the data

#(a) clean columns of t
t.drop(['tid_subid_after_swap', 'swap_pair_id', 'head_end_flag', 'tail_start_flag', 'tid_subid_orig'], axis=1, inplace=True)

#%%(b) remove synthetic points for cloaking gaps that will experience a gap (to make code below less complex)
t['CloakingGapSwap'] = np.where(t['row_uid'].isin(valid_assigned_helpers_df.main_row_uid.unique()), True, False)


t['gap_number'] = t['gap_label_pair_final_syn_fixed'].str.extract(r'(?:last_|first_)(\d+)')[0]
start_mask = t['gap_label_pair_final_syn_fixed'].str.startswith('last_', na=False) & t['CloakingGapSwap']
stop_mask = t['gap_label_pair_final_syn_fixed'].str.startswith('first_', na=False)
t['CloakingGapSwap_filled'] = False

# Forward fill for each gap_number
for gap_num in t.loc[start_mask, 'gap_number'].unique():
    # Get indices for last_ and first_ with this gap number
    last_idx = t[(start_mask) & (t['gap_number'] == gap_num)].index
    first_idx = t[(stop_mask) & (t['gap_number'] == gap_num)].index
    
    for l_idx, f_idx in zip(last_idx, first_idx):
        # Fill True from last_ to first_ (inclusive or exclusive depending on your needs)
        t.loc[l_idx:f_idx, 'CloakingGapSwap_filled'] = True

t.drop(columns='gap_number', inplace=True)

print(t[t['CloakingGapSwap_filled'] == True]['point_type'].unique()) # raw but they should mainly be synthetic
t[t['CloakingGapSwap_filled'] == True][['point_type', 'gap_label_pair_final_syn_fixed', 'CloakingGapSwap', 'CloakingGapSwap_filled']]


#%% drop CloakingGapSwap True from df as these gaps should not be filled
# but 'last' and 'first' are raw points and must remain, can only remove points where
# t['CloakingGapSwap_filled'] is True AND t['point_type'] is 'synthetic' 
# Create a new DataFrame without the filled synthetic rows
t_forSwapping = t[~((t['CloakingGapSwap_filled']) & (t['point_type'] == 'synthetic'))].copy()

# Optional: check counts
print("Original rows:", len(t))
print("Rows after dropping selected synthetic filled:", len(t_forSwapping))
print(t_forSwapping['point_type'].value_counts())
#Original rows: 7334941
#Rows after dropping selected synthetic filled: 7331578
#point_type
#raw          6811202
#synthetic     520376

#%%
t_forSwapping.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping.parquet")










#%% SWAPPING
# load data
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/valid_assigned_helpers_df.parquet")

#%%
from tqdm import tqdm
import numpy as np
import os
import pandas as pd

# --- STEP 0: Add columns to track swaps ---
t_forSwapping['tid_subid_orig'] = t_forSwapping['tid_subid']

# IMPORTANT: initialize current container as original
t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid']

t_forSwapping['swap_pair_id'] = pd.NA
t_forSwapping['head_end_flag'] = False
t_forSwapping['tail_start_flag'] = False

# Precompute row_uid → point_id_t mapping (original split reference)
row_uid_to_pid = t_forSwapping.set_index('row_uid')['point_id_t'].to_dict()

# Track helper rows already used
used_helper_rows = set()

swap_counter = 0

# --- STEP 1: Process swaps sequentially ---
for _, swap in tqdm(valid_assigned_helpers_df.iterrows(),
                    total=len(valid_assigned_helpers_df),
                    desc="Processing swaps"):

    main_row_uid = swap['main_row_uid']
    helper_tid_target = swap['helper_tid']
    clkpassed = swap['clkpassed']

    # -------------------------------------------------
    # 1️⃣ Get split position from ORIGINAL metadata
    # -------------------------------------------------
    main_split_pid = row_uid_to_pid[main_row_uid]

    # -------------------------------------------------
    # 2️⃣ Get CURRENT container of main row
    # -------------------------------------------------
    main_container = t_forSwapping.loc[
        t_forSwapping.row_uid == main_row_uid,
        'tid_subid_after_swap'
    ].values[0]

    # -------------------------------------------------
    # 3️⃣ Identify helper split row (still original logic)
    # -------------------------------------------------
    helper_candidates = t_forSwapping[
        (t_forSwapping['tid_subid_after_swap'] == helper_tid_target) &
        (t_forSwapping['intersects_cloaking'] == clkpassed) &
        (~t_forSwapping['row_uid'].isin(used_helper_rows))
    ]

    if len(helper_candidates) == 0:
        continue

    helper_split_row = helper_candidates.sample(1).iloc[0]
    helper_row_uid = helper_split_row['row_uid']
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_row_uid)

    # -------------------------------------------------
    # 4️⃣ Get CURRENT container of helper row
    # -------------------------------------------------
    helper_container = t_forSwapping.loc[
        t_forSwapping.row_uid == helper_row_uid,
        'tid_subid_after_swap'
    ].values[0]

    # -------------------------------------------------
    # 🚨 Prevent swapping within same container
    # -------------------------------------------------
    if main_container == helper_container:
        continue

    swap_counter += 1

    # -------------------------------------------------
    # 5️⃣ Extract FULL current containers
    # -------------------------------------------------
    main_box = t_forSwapping[
        t_forSwapping['tid_subid_after_swap'] == main_container
    ]

    helper_box = t_forSwapping[
        t_forSwapping['tid_subid_after_swap'] == helper_container
    ]

    # -------------------------------------------------
    # 6️⃣ Split using ORIGINAL split position
    # -------------------------------------------------
    main_head = main_box[main_box['point_id_t'] <= main_split_pid]
    main_tail = main_box[main_box['point_id_t'] >  main_split_pid]

    helper_head = helper_box[helper_box['point_id_t'] <= helper_split_pid]
    helper_tail = helper_box[helper_box['point_id_t'] >  helper_split_pid]

    # -------------------------------------------------
    # 7️⃣ Flag boundaries
    # -------------------------------------------------
    t_forSwapping.loc[main_head.index, 'head_end_flag'] = \
        t_forSwapping.loc[main_head.index, 'point_id_t'] == main_split_pid

    t_forSwapping.loc[main_tail.index, 'tail_start_flag'] = \
        t_forSwapping.loc[main_tail.index, 'point_id_t'] == main_split_pid + 1

    t_forSwapping.loc[helper_head.index, 'head_end_flag'] = \
        t_forSwapping.loc[helper_head.index, 'point_id_t'] == helper_split_pid

    t_forSwapping.loc[helper_tail.index, 'tail_start_flag'] = \
        t_forSwapping.loc[helper_tail.index, 'point_id_t'] == helper_split_pid + 1

    # -------------------------------------------------
    # 8️⃣ Perform the swap (swap tails)
    # -------------------------------------------------
    t_forSwapping.loc[main_tail.index, 'tid_subid_after_swap'] = helper_container
    t_forSwapping.loc[main_tail.index, 'swap_pair_id'] = swap_counter

    t_forSwapping.loc[helper_tail.index, 'tid_subid_after_swap'] = main_container
    t_forSwapping.loc[helper_tail.index, 'swap_pair_id'] = swap_counter


print(f"Swapping completed for {swap_counter} assigned pairs.")
t_forSwapping.head()

#%% compare to ouput from 131 -must also update github
t_forSwapping.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_swapped_201.parquet")

#%%
import geopandas as gpd
t_forSwapping = gpd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_swapped_201.parquet")
# and from 131
import pandas as pd
t_forSwapping_swapped_hypridCloaked =  gpd.read_parquet(r"d:\paper3\output_hybrid_cloakedSwapping\t_forSwapping_swapped_hypridCloaked.parquet")
t_forSwapping_swapped_hypridCloaked_swap_log_df = pd.read_parquet(r"d:\paper3\output_hybrid_cloakedSwapping\t_forSwapping_swapped_hypridCloaked_swap_log_df.parquet")
t_forSwapping_swapped_hypridCloaked_container_summary_df = pd.read_parquet(r"d:\paper3\output_hybrid_cloakedSwapping\t_forSwapping_swapped_hypridCloaked_container_summary_df.parquet")





#%% looking at results from 131
print(t_forSwapping_swapped_hypridCloaked_swap_log_df.swap_id.max()) 
# 11,549 swaps total between main an helper trajectory 
#- this is dictated by the number of valid swaps assigned to cloaking gaps 
t_forSwapping_swapped_hypridCloaked_swap_log_df.head()
# records how many points are in head and tail

#%%
print(len(t_forSwapping_swapped_hypridCloaked_container_summary_df)) # 19,189 - same as original number of tid_subid
t_forSwapping_swapped_hypridCloaked_container_summary_df.head() 
# number of points per container_id
# how many head and tail segments are in container (good), 
# as well as median and max swap count
# and the number of original tid per container! - n_unique_orig_tid

#%%
print(t_forSwapping_swapped_hypridCloaked.tid_subid.nunique()) # 19,189
print(t_forSwapping_swapped_hypridCloaked.tid_subid_after_swap.nunique()) # 19,189
print(t_forSwapping_swapped_hypridCloaked.tid_subid_after_swap.isna().any()) # because I intialised t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid']  
# rows that never swapped kept the original tid_subid

print(t_forSwapping_swapped_hypridCloaked.swap_pair_id.unique())
print(t_forSwapping_swapped_hypridCloaked.swap_pair_id.value_counts()) # some 1, some up to 4k --> one swap affected 4k rows

print(t_forSwapping_swapped_hypridCloaked.head_end_flag.unique()) # [False  True]
print(t_forSwapping_swapped_hypridCloaked.tail_start_flag.unique()) # [False  True] - question, are they at the correct rows

print(t_forSwapping_swapped_hypridCloaked.swap_count.min()) # 0 
print(t_forSwapping_swapped_hypridCloaked.swap_count.median()) # 0 --> half of my points were never swapped
print(t_forSwapping_swapped_hypridCloaked.swap_count.max()) # 66

print(t_forSwapping_swapped_hypridCloaked['visited_containers'].str.len().eq(0).value_counts())
#visited_containers
#True     3,707,369 --> empty list --> points never swapped
#False    3,624,209 --> non-empty list

t_forSwapping_swapped_hypridCloaked.head()

#%% did any container loose all points? No because False
original_sizes = t_forSwapping.groupby('tid_subid').size()
new_sizes = t_forSwapping_swapped_hypridCloaked.groupby('tid_subid_after_swap').size()

print((original_sizes == 0).any())
print((new_sizes == 0).any())

#%% growth of containers (i.e., points associtaed with new_tid_subid compared to oirg tid_subid)
container_growth = (
    new_sizes - original_sizes.reindex(new_sizes.index).fillna(0)
).sort_values(ascending=False)

container_growth.head(10)

#%% did points revisit the same container - should be 0, one of the constraints is to not swap back
t_forSwapping_swapped_hypridCloaked[
    t_forSwapping_swapped_hypridCloaked.visited_containers
        .apply(lambda x: len(x) != len(set(x)))
]


#%% is tehre a container that never swapped
# Per container: did anything swap?
container_swap_stats = (
    t_forSwapping_swapped_hypridCloaked
    .groupby('tid_subid_after_swap')
    .agg(
        max_swap_count=('swap_count', 'max'),
        any_head=('head_end_flag', 'any'),
        any_tail=('tail_start_flag', 'any')
    )
)

# Containers that never swapped
never_swapped_containers = container_swap_stats[
    (container_swap_stats.max_swap_count == 0) &
    (~container_swap_stats.any_head) &
    (~container_swap_stats.any_tail)
]

print(len(never_swapped_containers)) # 9,585 - just under 50%
#%%
pct_never_swapped = (
    len(never_swapped_containers) /
    container_swap_stats.shape[0]
) * 100

print(f"{pct_never_swapped:.2f}%") # 49.95%

#%% look at head and tail flags
df = t_forSwapping_swapped_hypridCloaked.sort_values(
    ['tid_subid_after_swap', 'row_uid']

)

# Get previous row within same container
df['prev_tid'] = df['tid_subid_after_swap'].shift()
df['prev_pid'] = df['row_uid'].shift()

head_errors = df[
    (df.head_end_flag) &
    (df.tid_subid_after_swap == df.prev_tid) &
    (df.row_uid != df.prev_pid + 1)
]

print("Head alignment errors:", len(head_errors)) # 53
# %%
df['prev_head'] = df['head_end_flag'].shift()

tail_errors = df[
    (df.tail_start_flag) &
    (~df.prev_head)
]

print("Tail alignment errors:", len(tail_errors))

#%%
total_heads = df.head_end_flag.sum()
total_tails = df.tail_start_flag.sum()

print(total_heads, total_tails) #12768 8422 - not good

# %%
double_heads = df[df.head_end_flag].duplicated(
    subset=['tid_subid_after_swap', 'row_uid']
).sum()

print("Duplicate head locations:", double_heads) # 0

#%%
#Head alignment errors: 53
#Tail alignment errors: (nonzero)
#total_heads = 12768
#total_tails = 8422 
# --> 4,346 heads have no corresponding tail
#Duplicate head locations: 0

# flagging heads and tails too early

#%% entropy change
# exact 1 original traj = entropy -
# mix trajectories in container= entropy 0
# higher entrpy = stronger anoymity mixing
import numpy as np

def shannon_entropy(counts):
    probs = counts / counts.sum()
    return -(probs * np.log2(probs)).sum()

container_entropy = (
    t_forSwapping_swapped_hypridCloaked
    .groupby('tid_subid_after_swap')['tid_subid_orig']
    .value_counts()
    .groupby(level=0)
    .apply(lambda x: shannon_entropy(x.values))
)

print(container_entropy.describe())
#count    19189.000000
#mean         0.440910 --> moderate mixing
#std          0.614636
#min         -0.000000
#25%          0.000000
#50%          0.000000 --> half of the containers remain unswapped
#75%          0.890492 --> log2(1.85) --> top 25% of containers mix about two trajectories --> overall, 25% of trajectories are lighly mixed
# log because Shannon entropy is H=E-pilog2(pi) and a container with k trajectories evenly mixed is pi = 1/k
# H = log2(k)
# max entropy is 4.7 --> k = 2^4.7 = 2^4 (16) * 2^0.7 (0.16) = 26 --> most mixed container behaves like ~26 evenly mixed trajectories combined (strong anonymisation)
#max          4.705298 --> a few very high-anonymity hotspots?
# light mixing for many, heavy mixing for few

# high-anonymity hotpsots (expected)
# swapping concentrated at cloaking lcoations - only 177 cloaking locations, ~30k gaps but only ~12k gaps have valid swapping partners
# swaps are spatially clustered
# only intersecting trajectories within the cloaking area participate