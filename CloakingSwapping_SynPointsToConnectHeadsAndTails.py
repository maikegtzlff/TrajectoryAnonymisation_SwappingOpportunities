#%% 
import geopandas as gpd
import pandas as pd
import numpy as np
#%% shortest path connecting head and tails
#sp_t_cswappingl_origsynf_OD_odid_final.to_parquet(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/headtailOD_shortestPath.parquet")
sp_headtail = gpd.read_parquet("d:\paper3\Data\synPointsForHeadTailConnection\headtailOD_shortestPath_origTimebins.parquet")
wayids = sp_headtail.id.unique() 


#%% get speed data
tid_osmid_speed = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\traj_osmid_shortestpath_speed_allColumns_speedkmh_5to150kmh_4Dec.parquet")
tid_osmid_speed.head()

#%% get median speed by user (and updated time bins) on each road segment, ignoring seasons
tid_osmid_speed["time_bin"] = np.where(
    (tid_osmid_speed["hour"] >= 7) & (tid_osmid_speed["hour"] < 9),
    "morning peak",
    np.where(
        (tid_osmid_speed["hour"] >= 9) & (tid_osmid_speed["hour"] < 16),
        "flat peak",
        np.where(
            (tid_osmid_speed["hour"] >= 16) & (tid_osmid_speed["hour"] < 20),
            "evening peak",
            "night time"
        )
    )
)

tid_osmid_speed.head()

#%% get median speed for all users by time_bin
median_speed_alluid = tid_osmid_speed.groupby(['id', 'time_bin'])['speed_kmh'].median().reset_index() # median speed by time bin for each osmid, based on all users
median_speed_alluid

#%% only keep the speed data for the osmid of interest
print(len(median_speed_alluid))
median_speed_alluid_wayids = median_speed_alluid[median_speed_alluid['id'].isin(wayids)]
print(len(median_speed_alluid_wayids))
median_speed_alluid_wayids

#%% time bin must also match
median_speed_alluid_wayids = median_speed_alluid_wayids.rename(columns={'time_bin': 'time_bin_label'})
sp_headtail_speed = sp_headtail.merge(median_speed_alluid_wayids, on =['id', 'time_bin_label'], how='left')
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 55430
sp_headtail_speed
#%% add overall time, not time bin
median_speed_alluid_allday = tid_osmid_speed.groupby(['id'])['speed_kmh'].median().reset_index()
#%%
median_speed_alluid_allday = median_speed_alluid_allday.rename(columns={'speed_kmh': 'speed_kmh_noHour'})
sp_headtail_speed = sp_headtail_speed.merge(median_speed_alluid_allday, on =['id'], how='left')
sp_headtail_speed.head()

#%% fill na of speed_kmh
sp_headtail_speed['speed_kmh'] = sp_headtail_speed['speed_kmh'].fillna(
    sp_headtail_speed['speed_kmh_noHour']
)
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 38955, before55430

#%% fill the remaining na with maxspeed
edges = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\edges.parquet")
edges = edges[['id', 'maxspeed']]
edges = edges.drop_duplicates(subset=['id'])
edges = edges.dropna(subset=['maxspeed'])
edges.head()

#%% add maxspeed to shortest path
sp_headtail_speed = sp_headtail_speed.merge(edges, on =['id'], how='left')

sp_headtail_speed['speed_kmh'] = sp_headtail_speed['speed_kmh'].fillna(
    sp_headtail_speed['maxspeed']
)

if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 23989 (1.9%), before 38955, before 55430


#%% calculate synthetic points
