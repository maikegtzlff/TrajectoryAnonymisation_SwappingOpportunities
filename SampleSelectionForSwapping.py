#%% load libraries
import pandas as pd
import geopandas as gpd
import movingpandas as mpd
import shapely as shp
#import hvplot.pandas

from geopandas import GeoDataFrame, read_file
from shapely.geometry import Point, LineString, Polygon
from datetime import datetime, timedelta
#from holoviews import opts

import warnings

warnings.filterwarnings("ignore")

mpd.show_versions()

#%% load data and create trajectories
#gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\traj_filled_baseline_ShiftedTimestamps_gapAware.parquet")
# look at other trajectory versions
# no distinction between syn and raw
#gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\traj_filled_RELEASE.parquet")
gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\filled_origPointId.parquet")
print(len(gdf))
gdf.head() 


# orig point id = id + unix timestamp
print(gdf.orig_point_id.isna().any()) # has na --> na = synthetic point
print(gdf.point_id.isna().any())


gdf[['orig_point_id','point_id', 'tid_subid', 'speed_source', 'osmid_best']].head()
#%%
print((gdf['orig_point_id'].notna() == gdf['speed_source'].isna()).all().all()) # whenever there is an original point id, there is not speed source (True, good)
print((gdf['orig_point_id'].isna() == gdf['speed_source'].notna()).all().all()) # and the other way round, when there is no orig point id (aka point is synthetic), there is always a speed source attribute (because the point is synthetic),good
#%%
gdf[['orig_point_id', 'speed_source']]

#%% add a new column to clearly distinguish raw from synthetic points 
import numpy as np
gdf['RawVsSyn'] = np.where(gdf['orig_point_id'].isna(), 'synthetic', 'raw')
gdf.head() 

#%% columns of interest
#tid_subid, osmid_best and RawVsSyn
# have a "segmented"tid, i.e. by osmid_best
# gdf['tid_subid'] is date plus uid plus a number
gdf['tid_segmented'] = gdf['tid_subid'] + '_edge_' + gdf['osmid_best'] # all tids on the same edge have the same tid
gdf.head() 


#%% create trajectories
#tc = mpd.TrajectoryCollection(gdf, "tid_segmented", t="unix_timestamp")
tc = mpd.TrajectoryCollection(gdf, "tid_subid", t="unix_timestamp")
tc # TrajectoryCollection with 1,091,756 trajectories
# silently droopping points unless:
# must have at least 2 >points per tid...
# must have valid timestamps
# non-empty geometries



#%% export as lines (easier to look at)
tc_lines = tc.to_line_gdf()
tc_lines.head()

#%%
print(len(tc_lines)) #              4,515,512
tc_lines.tid_segmented.nunique() #  1,091,756 --> multiple lines have the same tid
#%% export 
#tc_lines.to_parquet(r"E:\paper3\data/filled_origPointId_Lines_SegmentedByEdge.parquet")
tc_lines.to_parquet(r"E:\paper3\data/filled_origPointId_Lines.parquet")

#%% WHEN LOOKING AT LINES, ARE TRAJECTORIES STILL SGEMENTED BY OSM EDGE? 
# ARE ANY ATTRIBUTES LOST BY CREATING TRAJECTORIES?