#%% load libaries
import geopandas as gpd
import pandas as pd
import numpy as np

import random

#%% load all trajectories
gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\filled_origPointId.parquet")
gdf['RawVsSyn'] = np.where(gdf['orig_point_id'].isna(), 'synthetic', 'raw')


#%% add columns
#%% find nodes to locate trajectory points
nodes = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/nodes.parquet")
edges = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/edges.parquet")
edges = edges.to_crs(gdf.crs)

edges['osmid_uv'] = edges['id'].astype('str') + '_' + edges['u'].astype('str')  + '_' + edges['v'].astype('str') 

# get all nodes on edge
#nodesOnEdge_dict = (
#    edges
#    .groupby("id", sort=False)
#    .apply(lambda g: list(map(int, g["u"].tolist() + [g["v"].iloc[-1]])))
#    .to_dict()
#)
#%%
# grouping by point_id later => must be unique
if len(gdf) != gdf.point_id.nunique():
    print('adding unique point_id')
    gdf = gdf.reset_index(drop=True)
    gdf['point_id_unique'] = gdf.index
else:
    gdf['point_id_unique'] = gdf['point_id']


# only interested in osmid_uv (and geometry)
lines_gdf = edges[['osmid_uv', 'geometry']].copy()
points_with_lines = gpd.sjoin_nearest(
    gdf,
    lines_gdf,
    how="left",
    distance_col="dist_to_edge"
) # creates duplicates - doesnt matter

# get u and v for each point
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines['osmid_uv'].str.split('_', expand=True)
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines[['osmid_uv_osmid', 'u', 'v']].astype(int)



# Group by point_id and combine u and v into lists
points_combined = points_with_lines.groupby('point_id_unique').agg({
    'u': lambda x: list(x),
    'v': lambda x: list(x),
    'osmid_uv': 'first',                 
    'dist_to_edge': 'first'              
}).reset_index()

# flatten v into the u list 
points_combined['u'] = points_combined.apply(lambda row: row['u'] + row['v'], axis=1)
points_combined = points_combined.drop(columns='v')

# join back to df
points_combined = points_combined.rename(columns={'u': 'point_nodes_inbetween'})
gdf = gdf.merge(points_combined, on='point_id_unique', how='left')

gdf[['osmid_edge', 'u', 'v']] = gdf['osmid_uv'].str.split('_', expand=True)
print(gdf.columns)


#%% prep data frame for segment swapping
# keep track or original tid value
gdf["orig_tid_subid"] = gdf["tid_subid"]
gdf["orig_final_point_id"] = gdf["point_id"]

# timebins
gdf["hour"] = (
    pd.to_datetime(gdf["unix_timestamp"], unit="s", utc=True)
      .dt.tz_convert("Pacific/Auckland")
      .dt.hour
)

gdf["time_bin"] = np.where(
    (gdf["hour"] >= 7) & (gdf["hour"] < 9),
    "morning peak",
    np.where(
        (gdf["hour"] >= 9) & (gdf["hour"] < 16),
        "flat peak",
        np.where(
            (gdf["hour"] >= 16) & (gdf["hour"] < 20),
            "evening peak",
            "night time"
        )
    )
)
# raw vs synthetyic (to acknowledge cloaking geometries)
gdf['RawVsSyn'] = np.where(gdf['orig_point_id'].isna(), 'synthetic', 'raw')

print(gdf.columns)
gdf.head()
#%%
# must keep track of original tid
gdf['source_tid_subid'] = gdf['tid_subid']
gdf['tid_history'] = gdf['tid_subid'].apply(lambda x: [x])  # start with current tid_subid
gdf['tid_change_count'] = 0

#%% "overlapping points" qualifiying the trajectories to swap are split into head and tail
# head keeps the quailfying point, tail starts with the next point of the tid
# therefore, make a copy of the previous point to quailty check swapping outcome
gdf[['prev_u', 'prev_v', 'prev_time_bin']] = (
    gdf
    .groupby('tid_subid')[['u', 'v', 'time_bin']]
    .shift(1)
)

#%% 
trajectories = [g for _, g in gdf.groupby('tid_subid')]
import joblib
# save
joblib.dump(trajectories, r'E:\paper3\data\trajectories_list/trajectories_filled.joblib')







#%% load trajectories
import joblib
trajectories = joblib.load(r'E:\paper3\data\trajectories_list/trajectories_filled.joblib')

#%% swap trajectories at edge 
import geopandas as gpd
import pandas as pd
import random

import importlib
import utils_SwappingTrajectories_HeadsAndTails as swht
importlib.reload(swht)

num_trajectories = len(trajectories)


num_passes = num_trajectories  
for _ in range(num_passes):
    indices = list(range(num_trajectories))
    random.shuffle(indices)   # random order for this pass
    
    for i in indices:
    #for i in range(num_trajectories):
        current = trajectories[i]
        others_indices = [j for j in range(num_trajectories) if j != i]
        
        updated_others = []
        for j in others_indices:
            current, df_swapped = swht.swap_tails_inclhistory(current, trajectories[j], n=3)
            updated_others.append(df_swapped)
        
        # Save updated current
        trajectories[i] = current
        
        # Save updated others back to their positions
        for idx, j in enumerate(others_indices):
            trajectories[j] = updated_others[idx]

#%% look at output, did swapping work?
for i in range(len(trajectories)):
    n_unique = trajectories[i].source_tid_subid.nunique()
    if n_unique > 1:
        print(f"Index {i}: {n_unique}") # swapping, inlcuding time constraint works

#%% export/look at output in q
trajectories[498].to_parquet(fr"E:\paper3\data\trajectories_list\swappingOutput\trialRuns/tswapped_498.parquet")

#%% export all trajectories



