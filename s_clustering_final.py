#import geopandas as gpd
#import pandas as pd
#import numpy as np
#from sklearn.cluster import DBSCAN
#from tqdm import tqdm
#import os


#def cluster_user(gdf_user, radius_km, min_points):

#    coords = gdf_user[['lat_rad','lng_rad']].to_numpy()
#    epsilon = radius_km / 6371.0088  # km -> radians

#    db = DBSCAN(eps=epsilon, min_samples=min_points, algorithm='ball_tree', metric='haversine')
#    labels = db.fit_predict(coords)

#    gdf_user = gdf_user.copy()
#    gdf_user['cluster'] = labels
#    return gdf_user



#def cluster_users_to_parquet(
#        gdf, 
#        radius_km=0.06, 
#        min_points=4, 
#        output_dir="clustered_users"
#    ):
#    if gdf.crs is None:
#        gdf = gdf.set_crs(4326)
#    elif gdf.crs.to_epsg() != 4326:
#        gdf = gdf.to_crs(4326)

#    gdf['lat'] = gdf.geometry.y
#    gdf['lng'] = gdf.geometry.x
#    gdf['lat_rad'] = np.radians(gdf['lat'])
#    gdf['lng_rad'] = np.radians(gdf['lng'])

#    os.makedirs(output_dir, exist_ok=True)

#    uid_counts = gdf.groupby('uid').size().reset_index(name='n_points')
#    uids_ordered = uid_counts.sort_values('n_points')['uid'].tolist()

#    output_files = []

#    for uid in tqdm(uids_ordered, desc="Clustering users"):
#        gdf_user = gdf[gdf['uid'] == uid]

#        clustered_user = cluster_user(gdf_user, radius_km, min_points)
#        clustered_user = clustered_user[clustered_user['cluster'] != -1]
#        clustered_user['cluster_id'] = clustered_user['uid'].astype(str) + '_' + clustered_user['cluster'].astype(str)

#        file_path = os.path.join(output_dir, f"clustered_user_{uid}.parquet")
#        clustered_user.to_parquet(file_path)
#        output_files.append(file_path)

#        del gdf_user, clustered_user

#    return output_files


#def rank_clusters_from_gdf(clustered_gdf):
#    cluster_stats = (
#        clustered_gdf.groupby(['uid','cluster_id'])
#        .agg(sum_time_cluster_sec=('duration_s','sum'),
#             n_visits_total_cluster=('duration_s','count'))
#        .reset_index()
#    )

#    user_stats = (
#        clustered_gdf.groupby('uid')
#        .agg(sum_time_allclusters_sec=('duration_s','sum'),
#             n_visits_total_u=('duration_s','count'))
#        .reset_index()
#    )

#    clusters_ratio = cluster_stats.merge(user_stats, on='uid')
#    clusters_ratio['ratio_duration_cluster'] = clusters_ratio['sum_time_cluster_sec'] / clusters_ratio['sum_time_allclusters_sec']
#    clusters_ratio['ratio_freq_cluster'] = clusters_ratio['n_visits_total_cluster'] / clusters_ratio['n_visits_total_u']
#    clusters_ratio['w_average'] = (clusters_ratio['ratio_duration_cluster'] + clusters_ratio['ratio_freq_cluster']) / 2
#    clusters_ratio['rank'] = clusters_ratio.groupby('uid')['w_average'].rank(method='dense', ascending=False)
#    return clusters_ratio


# use threding for small users and process bigger ones sequentially
import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from tqdm import tqdm
from datetime import timedelta
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------
# Cluster a single user
# -------------------------
def cluster_user(gdf_user, radius_km, min_points):
    coords = gdf_user[['lat_rad', 'lng_rad']].to_numpy()
    epsilon = radius_km / 6371.0088  # km -> radians
    db = DBSCAN(eps=epsilon, min_samples=min_points, algorithm='ball_tree', metric='haversine')
    labels = db.fit_predict(coords)

    gdf_user = gdf_user.copy()
    gdf_user['cluster'] = labels
    gdf_user = gdf_user[gdf_user['cluster'] != -1]
    gdf_user['cluster_id'] = gdf_user['uid'].astype(str) + '_' + gdf_user['cluster'].astype(str)
    return gdf_user

# -------------------------
# Rank clusters (separate function)
# -------------------------
def rank_clusters(gdf):
    cluster_stats = (
        gdf.groupby(['uid','cluster_id'])
           .agg(sum_time_cluster_sec=('duration_s','sum'),
                n_visits_total_cluster=('duration_s','count'))
           .reset_index()
    )
    user_stats = (
        gdf.groupby('uid')
           .agg(sum_time_allclusters_sec=('duration_s','sum'),
                n_visits_total_u=('duration_s','count'))
           .reset_index()
    )
    clusters_ratio = cluster_stats.merge(user_stats, on='uid')
    clusters_ratio['ratio_duration_cluster'] = clusters_ratio['sum_time_cluster_sec'] / clusters_ratio['sum_time_allclusters_sec']
    clusters_ratio['ratio_freq_cluster'] = clusters_ratio['n_visits_total_cluster'] / clusters_ratio['n_visits_total_u']
    clusters_ratio['w_average'] = (clusters_ratio['ratio_duration_cluster'] + clusters_ratio['ratio_freq_cluster']) / 2
    clusters_ratio['rank'] = clusters_ratio.groupby('uid')['w_average'].rank(method='dense', ascending=False)
    return clusters_ratio

# -------------------------
# Main clustering function (3 categories + resume)
# -------------------------
def cluster_users_to_parquet_resumable(
        gdf,
        radius_km=0.06,
        min_points=4,
        output_dir="clustered_users"
    ):

    # Ensure CRS is degrees
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    gdf['lat'] = gdf.geometry.y
    gdf['lng'] = gdf.geometry.x
    gdf['lat_rad'] = np.radians(gdf['lat'])
    gdf['lng_rad'] = np.radians(gdf['lng'])

    os.makedirs(output_dir, exist_ok=True)

    # Get UID sizes
    uid_counts = gdf.groupby('uid').size().reset_index(name='n_points')
    uid_counts = uid_counts.sort_values('n_points')  # smallest -> largest
    uids = uid_counts['uid'].tolist()

    # Skip already processed users
    existing_files = {f.split(".parquet")[0] for f in os.listdir(output_dir) if f.endswith(".parquet")}
    uids = [uid for uid in uids if str(uid) not in existing_files]

    # record problematic users
    problematic_uids = []

    for uid in tqdm(uids, desc="Clustering users"):
        user_file = os.path.join(output_dir, f"{uid}.parquet")
        if os.path.exists(user_file):
            continue  # skip already processed

        gdf_user = gdf[gdf['uid'] == uid]

        #handle memory issue
        try:
            clustered_user = cluster_user(gdf_user, radius_km, min_points)
            clustered_user.to_parquet(user_file)
            del gdf_user, clustered_user  # free memory
        except MemoryError:
            print(f"MemoryError clustering uid {uid}, skipping")
            problematic_uids.append(uid)
    return(problematic_uids)
