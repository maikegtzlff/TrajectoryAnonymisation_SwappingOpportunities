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
    AND where time_bin is the same.
    Returns a randomly chosen one among them, or None if no match found.
    """
    # create a lookup dictionary: (u,v) -> list of time_bins in df2
    uv_time_lookup = {}
    for u, v, t in zip(df2['u'], df2['v'], df2['time_bin']):
        uv_time_lookup.setdefault((u, v), set()).add(t)
    
    matches = []
    
    for u, v, t in zip(df1['u'], df1['v'], df1['time_bin']):
        if (u, v) in uv_time_lookup and t in uv_time_lookup[(u, v)]:
            matches.append((u, v))
            if len(matches) == n:
                break  # stop after first n matches
    
    if not matches:
        print("find_first_n_common_uv: no matching (u,v) found with same time_bin")
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

import geopandas as gpd
import pandas as pd
import random

# --- Top-level helper function to track tid changes ---
def update_tid_history(df, new_tid):
    """
    Updates tid_subid for the entire df and tracks its history.

    - tid_subid: current value
    - tid_history: list of all tid_subid values assigned to each point
    - tid_change_count: number of changes from the original
    """
    # initialize tracking columns if they don't exist
    if 'tid_history' not in df.columns:
        df['tid_history'] = df['tid_subid'].apply(lambda x: [x])
    if 'tid_change_count' not in df.columns:
        df['tid_change_count'] = 0

    # append new_tid only if it's different from the last
    def append_if_new(history):
        if history[-1] != new_tid:
            history.append(new_tid)
        return history

    df['tid_history'] = df['tid_history'].apply(append_if_new)
    df['tid_change_count'] = df['tid_history'].apply(lambda h: len(h) - 1)
    df['tid_subid'] = new_tid

    return df


# --- Swap function ---
def swap_tails_inclhistory(df1, df2, n=3):
    """
    Swaps the tail of df1 and df2 at a common (u,v) point.
    Only swaps trajectories from different users.
    Tracks tid_subid history for all points.
    """
    # check that users are different
    source1 = set(df1['uid'].unique())
    source2 = set(df2['uid'].unique())
    if source1 & source2:
        print(f"Cannot swap: overlapping user {source1 & source2}")
        return df1.copy(), df2.copy()

    # find candidate swap point
    common_uv = find_first_n_common_uv(df1, df2, n=n)
    if common_uv is None:
        return df1.copy(), df2.copy()

    u_val, v_val = common_uv
    head1, tail1 = split_at_uv(df1, u_val, v_val)
    head2, tail2 = split_at_uv(df2, u_val, v_val)

    # debugging
    print('swap_tails_auto')
    print('points in head1:', len(head1))
    print('points in tail2:', len(tail2))
    print('points in head2:', len(head2))
    print('points in tail1:', len(tail1))

    # concatenate new trajectories
    new_df1 = pd.concat([head1, tail2], ignore_index=True)
    new_df2 = pd.concat([head2, tail1], ignore_index=True)

    # renumber points
    new_df1 = new_df1.reset_index(drop=True)
    new_df1['point_id_s'] = new_df1.index + 1
    new_df2 = new_df2.reset_index(drop=True)
    new_df2['point_id_s'] = new_df2.index + 1

    # determine new tid_subid from head
    unique_tid1 = head1.tid_subid.unique()
    assert len(unique_tid1) == 1, f"Expected 1 unique tid_subid in head1, got {len(unique_tid1)}"
    new_tid1 = unique_tid1[0]

    unique_tid2 = head2.tid_subid.unique()
    assert len(unique_tid2) == 1, f"Expected 1 unique tid_subid in head2, got {len(unique_tid2)}"
    new_tid2 = unique_tid2[0]

    # update tid_subid with history tracking
    new_df1 = update_tid_history(new_df1, new_tid1)
    new_df2 = update_tid_history(new_df2, new_tid2)

    # convert back to GeoDataFrame
    new_df1 = gpd.GeoDataFrame(new_df1, geometry='geometry', crs=df1.crs)
    new_df2 = gpd.GeoDataFrame(new_df2, geometry='geometry', crs=df2.crs)

    return new_df1, new_df2
