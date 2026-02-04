
#%% define functions
import geopandas as gpd
import pandas as pd

import random

def split_at_uv(df, u_val, v_val):
    """
    Splits df into head (up to and including the row where u==u_val and v==v_val)
    and tail (after that row)
    """
    idx = df.index[(df['u'] == u_val) & (df['v'] == v_val)].tolist()
    
    if not idx:
        return df.copy(), pd.DataFrame(columns=df.columns)
    
    split_idx = idx[0]  # take first match 
    head = df.iloc[:split_idx + 1].copy()
    tail = df.iloc[split_idx + 1:].copy()

    #debugging
    print('split_at_uv')
    print(idx)
    print('points in head:', len(head))
    print('points in tail:', len(tail))

    return head, tail



def find_first_common_uv(df1, df2):
    """
    Finds the first (u, v) pair that exists in both df1 and df2.
    Returns a tuple (u_val, v_val) or None if no match found.
    """
    # Convert df2 u,v pairs to a set for fast lookup
    uv_set2 = set(zip(df2['u'], df2['v']))
    
    # Iterate through df1
    for u, v in zip(df1['u'], df1['v']):
        if (u, v) in uv_set2:
            return u, v
    
    return None  # no common point found


# instead randomly select one of the first 3 
def find_first_n_common_uv(df1, df2, n=3):
    """
    Finds the first `n` (u, v) pairs from df1 that also exist in df2.
    Returns a randomly chosen one among them, or None if no match found.
    """
    uv_set2 = set(zip(df2['u'], df2['v']))
    
    matches = []
    
    for u, v in zip(df1['u'], df1['v']):
        if (u, v) in uv_set2:
            matches.append((u, v))
            if len(matches) == n:
                break  # stop after first n matches
    
    if not matches:
        print("find_first_n_common_uv: no matching (u,v) found between the two trajectories")
        return None
    
    # pick one randomly
    choice_index = random.randrange(len(matches))
    
    # debugging: print which match was picked
    print(f"randomly picked match #{choice_index + 1} of the first {len(matches)} matches")
    
    return matches[choice_index]



def swap_tails_auto(df1, df2, n=3):
    # ensure tid has not been swapped before
    # actually, two users should never be swapped twice. eliminates the tid issue too
    # uid remains the same as input after swapping, so check can be based on uid
    # if i was to swap with the same tid again, it should recognise the uid being the same
    # Check for overlap in original sources
    source1 = set(df1['uid'].unique())
    source2 = set(df2['uid'].unique())
    if source1 & source2: # & to find elemens that exist in both sets
        print(f"Cannot swap: overlapping user {source1 & source2}")
        return df1.copy(), df2.copy()


    #common_uv = find_first_common_uv(df1, df2)
    common_uv = find_first_n_common_uv(df1, df2, n=n)

    if common_uv is None:
        # No common point to swap, return original dfs
        return df1.copy(), df2.copy()
    
    u_val, v_val = common_uv
    head1, tail1 = split_at_uv(df1, u_val, v_val)
    head2, tail2 = split_at_uv(df2, u_val, v_val)

    #debugging
    print('swap_tails_auto')
    print('points in head1:', len(head1))
    print('points in tail2:', len(tail2))
    print('points in head2:', len(head2))
    print('points in tail1:', len(tail1))

    new_df1 = pd.concat([head1, tail2], ignore_index=True)
    new_df2 = pd.concat([head2, tail1], ignore_index=True)

    # must renumber points after swapping
    new_df1 = new_df1.reset_index(drop=True)
    new_df1['point_id_s'] = new_df1.index + 1
    new_df2 = new_df2.reset_index(drop=True)
    new_df2['point_id_s'] = new_df2.index + 1

    # must update tid and keep track of original tid
    # tid is being carried over from head
    # actually not sure about this assert message. can swap whenever
    # check head1
    unique_tid1 = head1.tid_subid.unique()
    assert len(unique_tid1) == 1, f"Expected 1 unique tid_subid in head1, got {len(unique_tid1)}"
    new_df1['tid_subid'] = unique_tid1[0]
    # check head2
    unique_tid2 = head2.tid_subid.unique()
    assert len(unique_tid2) == 1, f"Expected 1 unique tid_subid in head2, got {len(unique_tid2)}"
    new_df2['tid_subid'] = unique_tid2[0]


    
    new_df1 = gpd.GeoDataFrame(new_df1, geometry='geometry', crs=df1.crs)
    new_df2 = gpd.GeoDataFrame(new_df2, geometry='geometry', crs=df2.crs)

    return new_df1, new_df2

#%% load data
#t_bckp = gpd.read_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\automaticalSwapping/t.parquet")
t = t_bckp.copy()

# must keep track of original tid
t['source_tid_subid'] = t['tid_subid']


for i, (_, df) in enumerate(t.groupby('tid_subid'), start=1):
    print(f"building t{i}")
    df = df.reset_index(drop=True)
    globals()[f"t{i}"] = df.copy()



# t_1 to t_6
print(t1.columns)
t2.head()

#t1.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t1_orig.parquet")
#t2.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t2_orig.parquet")
#t3.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t3_orig.parquet")
#t4.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t4_orig.parquet")
#t5.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t5_orig.parquet")
#t6.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t6_orig.parquet")


#%% swap
# First swap t1 <-> t2 
#t1_swapped, t2_swapped = swap_tails_auto(t1, t2)
t1_swapped, t3_swapped = swap_tails_auto(t1, t3, n=3) # no overlap with t2


# debugging ouput 
#split_at_uv
#[181]
#points in head: 182
#points in tail: 478
#split_at_uv
#[177]
#points in head: 178
#points in tail: 558
#swap_tails_auto
#points in head1: 182
#points in tail2: 558
#points in head2: 178
#points in tail1: 478


# Then swap the (new) t1 <-> t3 
#t1_swapped2nd, t3_swapped = swap_tails_auto(t1_swapped, t3)
#%%
print(t1_swapped.tid_subid.nunique()) # updated tid
print(t3_swapped.tid_subid.nunique()) 

print(t1_swapped.source_tid_subid.nunique()) # source tid
print(t3_swapped.source_tid_subid.nunique()) 

#%% look at these in Q
t1_swapped.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t1_swapped_t3_randomSwapPoint.parquet")
t3_swapped.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t3_swapped_t1_randomSwapPoint.parquet")

#%% see if not swapping the same user twice works
t1_swapped_2, t3_swapped_2 = swap_tails_auto(t1_swapped, t3, n=3) # error messaging works!
# Cannot swap: overlapping user {'f6f64a1846eb2f50552c23394c64a02663acadbc'}
# need more graceful handling of this scenario though, automatically look for the next trajectory instead

#%% what happens if two trajectories do not overlap
test1, test2 = swap_tails_auto(t1_swapped, t2, n=3) 
# error message, but still creates an output - though the output is just a copy of the df - doesn't really matter?
print(test1.equals(t1_swapped)) 
print(test2.equals(t2)) 
# n o valid swap = still retusn something --> code doesn't crash

#%% ok now swap t1 for the second  time
t1_swapped_2, t4_swapped = swap_tails_auto(t1_swapped, t4, n=3) 

#%%
print('input trajectories:')
print('number of trajectory identifiers')
print(t1_swapped.tid_subid.nunique(), t1_swapped_2.tid_subid.unique()) 
print(t4.tid_subid.nunique(), t4_swapped.tid_subid.unique()) 
print('number of source trajectories')
print(t1_swapped.source_tid_subid.nunique(), t1_swapped.source_tid_subid.unique()) 
print(t4.source_tid_subid.nunique(), t4.source_tid_subid.unique())  


print("\n\n\nswaped trajectories")
print('number of trajectory identifiers')
print(t1_swapped_2.tid_subid.nunique()) # 1, but has tid beedn updated succesfully?
print(t1_swapped_2.tid_subid.unique() == t1_swapped.tid_subid.unique())
print('tid before swapping', t1_swapped.tid_subid.unique())
print('tid after swapping', t1_swapped_2.tid_subid.unique())
print(t4_swapped.tid_subid.nunique()) 
print(t4_swapped.tid_subid.unique() == t4.tid_subid.unique())

print('number of source trajectories')
print(t1_swapped_2.source_tid_subid.nunique()) # # this has 2 - I think it "lost" the earlier swap becasue t4 can be swapped before t3 was
# or: has source_tid_subid be overwritten? I don't think so
print('t1: comparing the source tids before and after swapping directly')
print('before', t1_swapped.source_tid_subid.unique())
print('after', t1_swapped_2.source_tid_subid.unique())
print('t4')
print(t4_swapped.source_tid_subid.nunique())  # this has 3 - even though only swapped once: because segment that has been swapped had previousl been swapped already
print(t4_swapped.source_tid_subid.unique())
#['20200417_f6384b2a85a3248a47853cfbc554efdaac8fc9a2_5567' # this one is t4
# '20191214_fbe906873514e9223ef147d6b827dd559c378aa7_3031' # this one is t3 (from swapping with t1)
# '20200212_f6f64a1846eb2f50552c23394c64a02663acadbc_4362'] # this one is t1

#%% look at these in qgis
t1_swapped_2.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t1_swapped_t3_swapped_t4_randomSwapPoint.parquet")
t4_swapped.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory/t4_swapped_t1_prevSwapped_t3_randomSwapPoint.parquet")
