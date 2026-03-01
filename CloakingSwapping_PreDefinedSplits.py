#%%
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\valid_assigned_helpers_df.parquet")

#%% have found the matching helper trajectory segment 
# but must actually identify a splitting point outside the swapping loop

#%% first: must add time bin to valid_assigned_helpers_df
t_timebins = t_forSwapping[['row_uid', 'time_bin', 'time_bin_label']].copy()
t_timebins = t_timebins.rename(columns={'row_uid': 'main_row_uid', 'time_bin':'main_time_bin'})
print(len(valid_assigned_helpers_df))
# adding time bin of main to df
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(t_timebins, on ='main_row_uid',how="left")
print(len(valid_assigned_helpers_df)) # nothing lost
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(columns={'clkpassed': 'helper_clkpassed', 'helper_tid':'helper_tid_subid'})
valid_assigned_helpers_df.head() # added time bin to last point of heads - that is the main time bin, the one it must align with!


#%% now: find all potential swapping candidates according to valid_assigned_helpers_df
# reduce to helpers to work with less data when exploding
print(valid_assigned_helpers_df.helper_tid_subid.nunique()) # 7067
t_helper = t_forSwapping[t_forSwapping['tid_subid'].isin(valid_assigned_helpers_df.helper_tid_subid.unique())].copy()
print(len(t_helper)) # 4,404,118
# now explode
t_helper = t_helper.explode('intersecting_cloaking_ids')
print(len(t_helper)) # 4,442,621

#%% find points where helper_tid, clpassed and time_bin matches valid_assigned_helpers_df
t_helper = t_helper.rename(columns={'row_uid': 'helper_row_uid', 'intersecting_cloaking_ids': 'helper_clkpassed', 'tid_subid':'helper_tid_subid', 'time_bin':'helper_time_bin'})
t_helper = t_helper[['helper_row_uid', 'helper_clkpassed', 'helper_tid_subid', 'helper_time_bin']].copy()

# filtering helper points for main cloaking gaps based on matching cloaking area and timestamp
# only intersted in potantial swap/splitting points at this stage, not the full tid anymore
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(columns={'main_time_bin': 'time_bin'})
t_helper = t_helper.rename(columns={'helper_time_bin':'time_bin'})

print(len(t_helper))
print(len(valid_assigned_helpers_df))
t_helper = t_helper.merge(valid_assigned_helpers_df, on= ['helper_clkpassed', 'helper_tid_subid', 'time_bin'], how='inner')
print(len(t_helper))

print(t_helper.columns) # main_row_uid with assigned helper_row_uid - because of inner merge only points with overlapping cloaking areas and time_bins and the pre-definsed helper_tid remain
# ['helper_row_uid', 'helper_clkpassed', 'helper_tid_subid', 'time_bin','main_row_uid', 'time_bin_label']
print((t_helper['helper_row_uid'] == t_helper['main_row_uid']).any(), 'expected False') # False
t_helper.head() 
# 77,920 helper pool, but helper and main row_uid cannot be the same! 

#%% how many potential helpers do we have per clk gap?
print(len(t_helper))
print(t_helper.main_row_uid.nunique())

t_helper_count = t_helper.groupby('main_row_uid')['helper_row_uid'].nunique().reset_index(name="n_helper")
print(t_helper_count.n_helper.min())
print(t_helper_count.n_helper.median()) # 2
print(t_helper_count.n_helper.max()) # 1818 <-- one cloaking gap has a lot of possible swapping partners 

Q1 = t_helper_count['n_helper'].quantile(0.25)
Q3 = t_helper_count['n_helper'].quantile(0.75)
IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

t_no_outliers = t_helper_count[(t_helper_count['n_helper'] >= lower) & (t_helper_count['n_helper'] <= upper)]
t_no_outliers.n_helper.hist()


#%% a main_row_uid can't be a helper
print(t_helper['helper_row_uid'].isin(t_helper.main_row_uid.unique()).any()) # True, can't be true!
#t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid']).to_csv(r"\\tsclient\R\paper3\fromVM_201\debugging/helperPointAssignment.csv")
t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid'])
# not all potential helpers for that main_row though
# shows the helpers where the helper is a main_row, does not chow the main_row_uid istels

# must figure out if these main_row_uids, the ones that would be served by a helper that IS a main row have alternative points 
# realsitically they won't as helper tid and cloaking area have been pre-filtered already...

#%% in that case: a trajectory would be swapped twice at the same cloaking geometry - maybe it is overlapping cloaking geometries? though I did remove those
print(t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])]['main_row_uid'].nunique())
mah_id = t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])]['main_row_uid'].unique()
mah_id_df = t_helper[t_helper['main_row_uid'].isin(mah_id)] # helpers which are also mains, or as the name suggests mains as helpers

# this would tell me how many helper tids each main_row_uid has assigned, but since these are pre-defined we know it is only 1
print(mah_id_df.groupby('main_row_uid')['helper_tid_subid'].nunique().reset_index(name='n_helper_tid')['n_helper_tid'].max()) # 1

# this tells me how many points each assigned helper tid has
mah_id_df_pts = mah_id_df.groupby('main_row_uid')['helper_tid_subid'].value_counts().reset_index() # cannot randolmy chose from these
print(mah_id_df_pts['count'].min()) # ideally not 1 (is 1)
print(mah_id_df_pts['count'].median()) # 2
print(mah_id_df_pts['count'].max()) # 740
# alternatively, drop these main_row_uids from being swapped - would have to add the synthetic trajectories back in
# decided to keep them (but swap them last)

#%% look at helper ckl and main clk area
print(valid_assigned_helpers_df.head(1)) 
# main_row_uid 5365117 will get a helper from tid_subid 20191108_7cf738514ffcb46516c2982ca9abf6b221c17...
# at the cloaking area 2_6ceae7098142cdba6ebd5c5927c31066f1505482 for any point with time_bin 0
# look at the potential helpers
ph_t = t_helper[t_helper['main_row_uid']==5365117].copy()
print('number of potential split points', ph_t.helper_row_uid.nunique())
print('ensuring it is the same clk area (2_6ceae7098142cdba6ebd5c5927c31066f1505482)', ph_t.helper_clkpassed.unique())
print(ph_t.time_bin.unique(), 'should be 0')
print(ph_t.helper_tid_subid.unique(), 'expected 20191108_7cf738514ffcb46516c2982ca9abf6b221c17...')

ph_t # all valid helper points, could pick any of these at random

#%% now do the same for a helper that has a main_row_uid as their helper
print(mah_id_df.head(1))
# helper 124095 - which must also be a main
# helps main 5306703
# time bin 3
# helper_tid_subid 20190905_7cf738514ffcb46516c2982ca9abf6b221c17...
# helper_clkpassed 1_6ceae7098142cdba6ebd5c5927c31066f1505482
ph_tm = t_helper[t_helper['main_row_uid']==5306703].copy()
print('number of potential split points', ph_tm.helper_row_uid.nunique())
print('ensuring it is the same clk area (1_6ceae7098142cdba6ebd5c5927c31066f1505482)', ph_tm.helper_clkpassed.unique())
print(ph_tm.time_bin.unique(), 'should be 0')
print(ph_tm.helper_tid_subid.unique(), 'expected 20190905_7cf738514ffcb46516c2982ca9abf6b221c17...')

ph_tm # only one point, that point is  helper 124095 - which must also be a main

#%% look at that main
t_forSwapping[t_forSwapping['row_uid'] == 124095][['row_uid', 'tid_subid', 'time_bin', 'Sensitive_CloakingAreaId', 'intersecting_cloaking_ids']]
# own clk area is 2_7cf738514ffcb46516c2982ca9abf6b221c17146
# but intersects with 1_6ceae7098142cdba6ebd5c5927c31066f1505482 - for which it becomes a helper!
# main is tid   20190905_7cf738514ffcb46516c2982ca9abf6b221c17

# what is the tid of the main it helps
#t_forSwapping[t_forSwapping['row_uid'] == 5306703][['row_uid', 'tid_subid']]#, 'time_bin', 'Sensitive_CloakingAreaId', 'intersecting_cloaking_ids']]
#               20200717_6ceae7098142cdba6ebd5c5927c31066f1505
# both come from different tids - good

#%% for those problematic "main helpers" look at the alternatives, do they also intersect with the main sensitive cloaking area? are there options that do not intersect with the main cloaking area
# mah_id_df mains (main_row_uid) with mains (helper_row_uid) as helpers

print(len(mah_id_df)) #1473
print(mah_id_df.helper_row_uid.nunique()) # 1473 potential helpers to mains where at least one helper is a main themselves
print(mah_id_df.main_row_uid.nunique()) # 61 mains have these main helper issues
# helper_clkpassed is the mains sensitive cloaking area
# must now if all helper options for that main have passed this cloaking area


#%% look at all options for mains that have a main as their helper
# from 'mains as helpers' get the 'problematic' mains to look for alterantives
# are all helpers mains?
mains_list = valid_assigned_helpers_df.main_row_uid.unique()
(set(mah_id_df.helper_row_uid.unique()).issubset(set(mains_list))) # False, not all the helpers are mains (good)

mah_id_df['helper_is_main'] = mah_id_df['helper_row_uid'].isin(mains_list)
# look at the alterantives per main_row_uid 
# must have passed the helper_clkpassed geometry, otherwise they wouldn't have been assigned
#%%I want to know which other clk they passed - i.e., did they pass the main clk area that has been assigned to be a helper
#mah_id_df'helper_main_clk_sen'
hm_list = mah_id_df[mah_id_df['helper_is_main'] == True]['helper_row_uid'].unique() #122 helpers are also mains
# for these main helpers, get their sensitive cloaking id
hm_clkid = t_forSwapping[t_forSwapping['row_uid'].isin(hm_list)][['row_uid', 'Sensitive_CloakingAreaId']]
hm_clkid = hm_clkid.rename(columns={'row_uid':'helper_row_uid'})
# add these back to df
mah_id_df = mah_id_df.merge(hm_clkid, on ="helper_row_uid", how='left')
#%% now, also add all intersecting clkPassed of helper point, to determine whether the point overlaps with the clk of main
mah_allcklpssd = t_forSwapping[t_forSwapping['row_uid'].isin(mah_id_df.helper_row_uid.unique())][['row_uid', 'intersecting_cloaking_ids']]
mah_allcklpssd = mah_allcklpssd.rename(columns={'row_uid':'helper_row_uid'})
mah_id_df = mah_id_df.merge(mah_allcklpssd, on ="helper_row_uid", how='left')
mah_id_df

#%%
agg_df = mah_id_df.groupby('helper_tid_subid')['Sensitive_CloakingAreaId'] \
           .apply(lambda x: list(x.dropna().unique())) \
           .reset_index() \
           .rename(columns={'Sensitive_CloakingAreaId': 'Sensitive_CloakingAreaId_OfHelperMain'})
#agg_df['num_values'] = agg_df['Sensitive_CloakingAreaId_OfHelperMain'].apply(len) # all 1
mah_id_df = mah_id_df.merge(agg_df, on='helper_tid_subid', how='left')
mah_id_df

#%%
mah_id_df['helper_intersectingMainhelperclk'] = mah_id_df.apply(
    lambda row: any(val in row['intersecting_cloaking_ids'] for val in row['Sensitive_CloakingAreaId_OfHelperMain']),
    axis=1
)
#%%
mah_id_df = mah_id_df.sort_values(['main_row_uid', 'helper_row_uid'])

#%% look at one of them
th = mah_id_df[mah_id_df['main_row_uid']==143114] # 35 helper options, one of them is a main itself
print(len(th))
th
# none overlap with the sensitive clk area of the main helper, but that is probably because the area is cloaked...
# there are gaps in helper_row_uid
# the main helper is helper_row_uid 5164107
# but helper_row_uid "segments" based on continous row_uid are
# 586
# 755
# 101 to 107 <-- helper is last point of this "segment" of potential helpers
# 128 to 153
# when chosing a helper to split at, pick one from the segments that the "main" helper is not part of

#%% segment helpers
th['segment_helper_row_uid'] = th.groupby('main_row_uid')['helper_row_uid'] \
                                 .transform(lambda x: (x.diff() > 1).cumsum() + 1)
th

#%% class segment as main helper or not
th['segment_helper_is_main'] = th.groupby('segment_helper_row_uid')['helper_is_main'] \
                                  .transform('any')
th

#%%
def pick_helper(group):
    # 1st prioroity: segment is not part of main as helper
    candidates = group[group['segment_helper_is_main'] == False]
    if len(candidates) > 0:
        return candidates.sample(1)['helper_row_uid'].iloc[0]
    # 2nd priority: segment can be part of main as helper, but point itself isnt
    fallback = group[group['segment_helper_is_main'] == True]
    preferred = fallback[fallback['helper_is_main'] == False]
    if len(preferred) > 0:
        return preferred.sample(1)['helper_row_uid'].iloc[0]
    # final pick: only helper_is_main == True available
    return fallback.sample(1)['helper_row_uid'].iloc[0]


selected_helpers = (
    th.groupby('main_row_uid', group_keys=False)
      .apply(pick_helper)
      .reset_index(name='selected_helper_row_uid')
)
selected_helpers

#%% apply this to all "problematic helpers"; IMPORTANT
# sorting is important 
mah_id_df = mah_id_df.sort_values(['main_row_uid', 'helper_row_uid'])

# segment helpers
mah_id_df['segment_helper_row_uid'] = mah_id_df.groupby('main_row_uid')['helper_row_uid'] \
                                 .transform(lambda x: (x.diff() > 1).cumsum() + 1)

# class segment as main helper or not
mah_id_df['segment_helper_is_main'] = mah_id_df.groupby('segment_helper_row_uid')['helper_is_main'] \
                                  .transform('any')

# pick helpers randomly 
selected_mahelpers = (
    mah_id_df.groupby('main_row_uid', group_keys=False)
      .apply(pick_helper)
      .reset_index(name='selected_helper_row_uid')
)
selected_mahelpers
#%% now pick a random point for the unproblematic helpers
# remove problematic helpers from sample

# pick unproblematic helpers

# reunite helper selection


#%% choose a random point to split helper trajectory at (double check that no point is chosen twice)
# must chose one random point per assigned_swap_id to be the swapping partner to main_row_uid from valid_assigned_helpers_df
# assigned_swap_id = main_row_uid because there is only one main_row_uid per assigned_swap_id
print(len(t_helper) == t_helper.helper_row_uid.nunique())
t_helper_random = t_helper.groupby('main_row_uid', group_keys=False).sample(n=1)
print(len(t_helper_random)) # 11549 same as number of cloaking gaps good
print(t_helper_random.main_row_uid.nunique()) # must allso be 11549
print(t_helper_random.helper_row_uid.nunique()) # must allso be 11549

t_helper_random[['main_row_uid', 'helper_row_uid', 'helper_clkpassed', 'time_bin', 'helper_tid_subid']].head()



#%% control cloaking gaps are the same
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

#%% prep swap pairs more - multiple cloaking gaps in the same trajectory are problematic
# row_uid comes from the same tid_subid
# want to know the number of times a tid_subid is used for swapping, regardless whether it acts as main or helper
# will never be swapped with itself, so can create one list of "swapping" row_uids, ignoring helper or main function
# get list of uids involved in swapping
swap_uid_list = swap_pairs.main_row_uid.unique() + swap_pairs.helper_row_uid.unique()
len(swap_uid_list) # 11549  - would've expected double?
# is it a problem that every helper uid is the same as a main uid? yes!
# did something get overwritten somehwere




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