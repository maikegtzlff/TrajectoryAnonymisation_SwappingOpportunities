# function for clustering
# based on 
# https://anitagraser.com/2020/01/12/movement-data-in-gis-27-extracting-trip-origin-clusters-from-movingpandas-trajectories/
# based on https://geoffboeing.com/2014/08/clustering-to-reduce-spatial-data-set-size/
# https://scikit-learn.org/stable/auto_examples/cluster/plot_dbscan.html#sphx-glr-auto-examples-cluster-plot-dbscan-py

import geopandas as gpd
import pandas as pd

import numpy as np
from sklearn.cluster import DBSCAN
from geopy.distance import great_circle
from shapely.geometry import MultiPoint

def get_cluster(gdf, radius, min_points): # radius in km
    # (a) control input fulfills requirements
    # crs must be epsg 4326
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS defined.")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    
    # must have lat and lng columns
    gdf["lat"] = gdf.geometry.y
    gdf["lng"] = gdf.geometry.x

    # radius must be in correct format (i.e., km not m)
    if radius > 1:  
        print(f"Radius interpreted as meters ({radius} m) → converting to km")
        radius = radius / 1000

    
    # (b) clustering
    matrix = gdf[['lat', 'lng']].to_numpy()

    kms_per_radian = 6371.0088
    epsilon = radius / kms_per_radian

    db = DBSCAN(eps=epsilon, min_samples=min_points, algorithm='ball_tree', metric='haversine').fit(np.radians(matrix))
    cluster_labels = db.labels_
    num_clusters = len(set(cluster_labels))
    n_noise_ = list(cluster_labels).count(-1)
    #clusters_DBSCAN = pd.Series([matrix[cluster_labels == n] for n in range(num_clusters)])
    print('Number of clusters: {}'.format(num_clusters))
    print('Estimated number of noise points: %d' % n_noise_)

    # adding cluster labels to gdf
    cluster_gdf = gdf
    cluster_gdf['cluster'] = cluster_labels

    # removing noisy clusters
    cluster_gdf_nn = cluster_gdf[cluster_gdf.cluster != -1]


    return(cluster_gdf_nn)







# get cluster by user
def get_cluster_by_user(gdf, cluster_km, cluster_min_pts):

    # set crs
    # get_cluster function requires lat lng columns IN DEGREES (4326)

    # haversine requires co-ordinate pairs to be specified in radians, not degrees - https://towardsdatascience.com/lets-do-spatial-clustering-with-dbscan-c3dbfd9fc4d2
    if gdf.crs is None:
        gdf = gdf.set_crs('epsg:4326')
        print(gdf.crs)

    # cluster by uid
    emptylist = []

    grouped = gdf.groupby(['uid'])  
    n= 1

    for u, g in grouped:
        print('loop count:', n)
        print('uid:' + str(u))
        #print(type(g)) # gdf
        print('number of trajecory points by user', len(g))
        #print(g)

        emptylist.append(get_cluster(g, cluster_km, cluster_min_pts)) 
        n=n+1 
    #list to df
    stops_clustered = gpd.GeoDataFrame(pd.concat(emptylist, ignore_index=True), crs=emptylist[0].crs)
    stops_clustered.head()

    # add cluster id, unique for each user
    stops_clustered['cluster_id'] = stops_clustered['uid'] + '_' + stops_clustered['cluster'].astype('str')

    return(stops_clustered)


#%% ranking 
#%% ################# rank clusters #################
# we are looking at locations as stop, i.e., not the number of stay segments building a cluster, but the unique stop_ids in a cluster
# as we are interested in the frequency of visits to a location and the time spent
# one point represents a stop

# ranking: total time spent at cluster*0.5 + frequency of stops to cluster*0.5

#%%
def ranking_clusters(gdf):
    # A get ratio of time spent at cluster
    # get time spent at each cluster
    totaltime_cluster = gdf.groupby(['uid', 'cluster_id'])['duration_s'].sum().to_frame().reset_index() 
    totaltime_cluster.rename(columns={'duration_s': 'sum_time_cluster_sec'}, inplace=True)   
    # get total time spent at any cluster by user
    totaltime_allclusters = gdf.groupby(['uid'])['duration_s'].sum().to_frame().reset_index() 
    totaltime_allclusters.rename(columns={'duration_s': 'sum_time_allclusters_sec'}, inplace=True)   
    # join total duration by user to duration at cluster
    TimeSpentAtLoc = totaltime_cluster.merge(totaltime_allclusters, on= 'uid')
    TimeSpentAtLoc['ratio_duration_cluster'] = TimeSpentAtLoc['sum_time_cluster_sec']/TimeSpentAtLoc['sum_time_allclusters_sec']
    # column for weighted average TimeSpentAtLoc['ratio_duration_cluster']

    # B get frequency of visits ratio
    totalvisits_u = gdf.groupby(['uid'])['duration_s'].count().to_frame().reset_index() 
    totalvisits_u.rename(columns={'duration_s': 'n_visits_total_u'}, inplace=True)
    # to cluster
    totalvisits_cluster = gdf.groupby(['uid', 'cluster_id'])['duration_s'].count().to_frame().reset_index() 
    totalvisits_cluster.rename(columns={'duration_s': 'n_visits_total_cluster'}, inplace=True)
    # get ratio of frequencies
    FreqVisitToLoc = totalvisits_cluster.merge(totalvisits_u, on= 'uid')
    FreqVisitToLoc['ratio_freq_cluster'] = FreqVisitToLoc['n_visits_total_cluster']/FreqVisitToLoc['n_visits_total_u']
    # column for average FreqVisitToLoc['ratio_freq_cluster'] 

    # C add visitation frequency to time spent at cluster
    clusters_ratio = TimeSpentAtLoc.merge(FreqVisitToLoc, on=['uid', 'cluster_id'])

    # D rank clusters
    # calculate weighted average
    clusters_ratio['w_average'] = (clusters_ratio['ratio_duration_cluster']*0.5 + clusters_ratio['ratio_freq_cluster']*0.5)
    # rank by uid
    clusters_ratio['rank'] = clusters_ratio.groupby(['uid'])['w_average'].rank('dense', ascending=False)
    
    return(clusters_ratio)

#%%
def get_ranked_clusters(gdf, cluster_km, cluster_min_pts):
    # get clustered stops
    stops_clustered = get_cluster_by_user(gdf, cluster_km, cluster_min_pts)
    # rank clusters
    ranked_clustered = ranking_clusters(stops_clustered)
    # add ranking to clustered stops
    #cluster_id_centroid_1 = stops_clustered_centroid.drop_duplicates(subset=['cluster_id'])
    #cluster_id_centroid_2 = cluster_id_centroid_1[['cluster_id','centroid', 'centroid_lng', 'centroid_lat', 'geometry']].copy()
   
    ranked_stps_clustered = stops_clustered.merge(ranked_clustered, on=['uid', 'cluster_id'])
    print(len(stops_clustered)== len(ranked_stps_clustered), 'expected True')
 
    return(ranked_stps_clustered, ranked_clustered)



#%% # get_cluster_centroid(stops_clustered)
def get_cluster_centroid(stops_clustered_gdf, lcl_cart_crs):
 
    # centroid is based on mean, therefore crs must be cartesian
    # 2193 for NZ
    if stops_clustered_gdf.crs != lcl_cart_crs:
        stops_clustered_gdf = stops_clustered_gdf.to_crs(lcl_cart_crs)
        print(stops_clustered_gdf.crs)
    # get lat lng in 2193
    stops_clustered_gdf[f'lng_{lcl_cart_crs}'] = stops_clustered_gdf.geometry.x
    stops_clustered_gdf[f'lat_{lcl_cart_crs}'] = stops_clustered_gdf.geometry.y
    
    # find centroid
    cluster_centroids = stops_clustered_gdf.groupby(['uid', 'cluster_id'])[[f'lat_{lcl_cart_crs}', f'lng_{lcl_cart_crs}']].mean().reset_index()
    cluster_centroids.rename(columns={f'lat_{lcl_cart_crs}':f'centroid_lat_{lcl_cart_crs}', f'lng_{lcl_cart_crs}':f'centroid_lng_{lcl_cart_crs}'}, errors='raise', inplace=True)
    cluster_centroids = gpd.GeoDataFrame(cluster_centroids, geometry=gpd.points_from_xy(cluster_centroids[f'centroid_lng_{lcl_cart_crs}'], cluster_centroids[f'centroid_lat_{lcl_cart_crs}']), crs=lcl_cart_crs)
    cluster_centroids.rename_geometry('geometry_centroid', inplace=True)


    return(cluster_centroids)