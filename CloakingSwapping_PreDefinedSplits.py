#%%
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\valid_assigned_helpers_df.parquet")

#%% have found the matching helper trajectory segment 
# but must actually identify a splitting point outside the swapping loop

#valid_assigned_helpers_df
# main_row_uid
# helper_tid
# clkpassed

# macthing columns in t_forSwapping (synthetic points of clk gaps qualified for swapping are removed)
# row_uid <-- main_row_uid
# tid_subid
# time_bin (time_bin_label)
# intersecting_cloaking_ids <-- clkpassed

#%% first: must add time bin to valid_assigned_helpers_df
t_timebins = t_forSwapping[['row_uid', 'time_bin', 'time_bin_label']].copy()
t_timebins = t_timebins.rename(columns={'row_uid': 'main_row_uid'})
print(len(valid_assigned_helpers_df))
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(t_timebins, on ='main_row_uid',how="left")
print(len(valid_assigned_helpers_df)) # nothing lost
valid_assigned_helpers_df.head() # added time bin to last point of heads


#%% now: find all potential swapping candidates according to valid_assigned_helpers_df
# must explode lists first to identified cklpassed more easily
# reduce to helpers to work with less data
print(valid_assigned_helpers_df.helper_tid.nunique()) # 7067
t_helper = t_forSwapping[t_forSwapping['tid_subid'].isin(valid_assigned_helpers_df.helper_tid.unique())].copy()
print(len(t_helper)) # 4,404,118
# now explode
t_helper = t_helper.explode('intersecting_cloaking_ids')
print(len(t_helper)) # 4,442,621
t_helper.head()



#%% find points where helper_tid, clpassed and time_bin matches valid_assigned_helpers_df
t_helper = t_helper.rename(columns={'row_uid': 'helper_row_uid', 'intersecting_cloaking_ids': 'clkpassed','tid_subid':'helper_tid'})
t_helper.head()

#%% make a unique id for each swapping pair
valid_assigned_helpers_df['assigned_swap_id'] = valid_assigned_helpers_df['helper_tid'].astype(str) + '_' + valid_assigned_helpers_df['clkpassed'].astype(str) + '_' + valid_assigned_helpers_df['time_bin'].astype(str)
print(len(valid_assigned_helpers_df))
print(valid_assigned_helpers_df['assigned_swap_id'].nunique()) # one id for each row
t_helper['assigned_swap_id'] = t_helper['helper_tid'].astype(str) + '_' + t_helper['clkpassed'].astype(str) + '_' + t_helper['time_bin'].astype(str)

# subset t_helper based on this id
print(len(t_helper))
t_helper = t_helper[t_helper['assigned_swap_id'].isin(valid_assigned_helpers_df['assigned_swap_id'].unique())].copy()
print(len(t_helper)) # 77920 potential split points for the 11549 cloaking based swap points
t_helper[['helper_row_uid', 'helper_tid', 'clkpassed', 'time_bin', 'assigned_swap_id']].head()

#%% look at the swapping opportunities by cloaking gaps
t_helper_count = t_helper.assigned_swap_id.value_counts().reset_index()
# average points to chose from when it comes to splitting a helper trajectory into heads and tails
print(t_helper_count['count'].min())
print(t_helper_count['count'].median()) # 2
print(t_helper_count['count'].std()) #32
print(t_helper_count['count'].max()) # 1818

#%% how often are helper trajectories reused?
unique_swaps_per_helper = t_helper.groupby('helper_tid')['assigned_swap_id'].nunique().reset_index(name='unique_swap_count')
print(unique_swaps_per_helper['unique_swap_count'].min())
print(unique_swaps_per_helper['unique_swap_count'].median()) # 1
print(unique_swaps_per_helper['unique_swap_count'].std()) #1
print(unique_swaps_per_helper['unique_swap_count'].max()) # 11
unique_swaps_per_helper

# 1 is good, 11 makes it more error prone but not bad
# if a tid is a helper more than once, make sure swaps happen in order of clk gaps long tid?

#%% how often is a helper treajecotry also a main trajectory
print(t_helper.helper_tid.nunique()) # 7067
print(t_forSwapping[t_forSwapping['row_uid'].isin(valid_assigned_helpers_df.main_row_uid.unique())]['tid_subid'].nunique()) # 5,948 - but ~11k main_row_uid, so main trajectroies also get swapped multiple times


#%% choose a random point to split helper trajectory at (double check that no point is chosen twice)
# must chose one random point per assigned_swap_id to be the swapping partner to main_row_uid from valid_assigned_helpers_df
# assigned_swap_id = main_row_uid because there is only one main_row_uid per assigned_swap_id
print(len(t_helper) == t_helper.helper_row_uid.nunique())
t_helper_random = t_helper.groupby('assigned_swap_id', group_keys=False).sample(n=1)
print(len(t_helper_random)) # 11549 same as 
print(t_helper_random.assigned_swap_id.nunique())
t_helper_random[['assigned_swap_id', 'helper_row_uid', 'helper_tid', 'clkpassed', 'time_bin']].head()



#%% final helper lookup and control cloaking gaps are the same
# add info on main to helper
t_main = t_forSwapping[t_forSwapping['row_uid'].isin(valid_assigned_helpers_df.main_row_uid.unique())][['row_uid', 'tid_subid','gap_label_pair_final_syn_fixed', 'Sensitive_CloakingAreaId', 'time_bin']].copy()
t_main = t_main.rename(columns={'row_uid': 'main_row_uid', 'tid_subid':'main_tid_subid' ,'time_bin': 'main_time_bin', 'Sensitive_CloakingAreaId':'main_clkpassed', 'main_GapLabel': 'gap_label_pair_final_syn_fixed'})
print(len(t_main))

# add ID to find helper
valid_assigned_helpers_df_mainID = valid_assigned_helpers_df[['main_row_uid', 'assigned_swap_id']].copy()
t_main = t_main.merge(valid_assigned_helpers_df_mainID, on="main_row_uid", how="inner")
print(len(t_main))

# control cloaking gaps are the same
t_helper_random = t_helper_random.rename(columns={'helper_tid':'helper_tid_subid' ,'time_bin': 'helper_time_bin', 'clkpassed':'helper_clkpassed'})
t_helper_random_r = t_helper_random[['assigned_swap_id', 'helper_row_uid', 'helper_tid_subid', 'helper_clkpassed', 'helper_time_bin']].copy()

print(len(t_main))
print(len(t_helper_random_r))
swap_pairs = t_main.merge(t_helper_random_r, on='assigned_swap_id', how='inner')
print(len(swap_pairs)) # 11549, merge worked

# time bin and clkpassed should be the same for each row
print((swap_pairs['main_clkpassed'] == swap_pairs['helper_clkpassed']).any())
print((swap_pairs['main_time_bin'] == swap_pairs['helper_time_bin']).any())

swap_pairs
#%% run swapping
# prep data

# (1) isolate the swapping pair from main df

# (2) split main and helper into heads and tail

# (3) swap by updating tid

# (4) update point_id (actually move points to new container, i.e., order by new point id)
# (4a) hierarchy for ordering:
# new tid_subid after swap
# head, then tail (h is before t in the alphabet)
# row_uid

# (5) return to main df

# (6) run swapping on the next pair