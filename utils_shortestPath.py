#%% COMMENT 12 Jan
# this is the final shortest path code
# things to improve on:
# key, attr = list(edge_dicts.items())[0] - problematic if there are multiple parallel edges between u and v (e.g., opposite directions), as only picking the first one!
# instead find the shortest edge:
# key, attr = min(edge_dicts.items(), key=lambda item: item[1].get("length", float("inf")))


#%% load packages
import os
import pandas as pd
import geopandas as gpd

from shapely.geometry import LineString

from tqdm import tqdm

import networkx as nx
import osmnx as ox

import pickle
from pathlib import Path



#%% final code, writing to parquet in chunks
def process_od_rows(df, G, output_dir, chunk_size=500):
    """
    Process OD pairs in chunks, create segmented shortest paths,
    save each chunk to parquet to avoid memory issues.
    """
    os.makedirs(output_dir, exist_ok=True)

    all_segments = []
    failed_routes = []
    chunk_counter = 0

    for start in range(0, len(df), chunk_size):
        end = start + chunk_size
        chunk = df.iloc[start:end]

        for row in tqdm(chunk.itertuples(), total=len(chunk), desc=f"Processing rows {start}-{end}"):
            try:
                orig = row.orig
                dest = row.dest
                odid = row.odid
                uid  = row.uid

                # Find nearest nodes
                #u_node = ox.distance.nearest_nodes(G, orig.x, orig.y)
                #v_node = ox.distance.nearest_nodes(G, dest.x, dest.y)
                # precomputed nearest nodes in input df (faster)
                u_node = row.u_node
                v_node = row.v_node

                if u_node == v_node:
                    # origin and destination snap to same node
                    failed_routes.append({
                        "status": "same_node",
                        "reason": "Origin and destination snap to the same node",
                        "odid": odid,
                        "uid": uid,
                        "orig_x": orig.x,
                        "orig_y": orig.y,
                        "dest_x": dest.x,
                        "dest_y": dest.y
                    })
                    continue

                # Compute shortest path
                path_nodes = nx.shortest_path(G, u_node, v_node, weight="length")

                # Stitch edges
                segments = []
                for u, v in zip(path_nodes[:-1], path_nodes[1:]):
                    edge_dicts = G.get_edge_data(u, v)
                    if edge_dicts is None:
                        failed_routes.append({
                            "status": "fail",
                            "reason": f"Missing edge {u}->{v}",
                            "odid": odid,
                            "uid": uid,
                            "orig_x": orig.x,
                            "orig_y": orig.y,
                            "dest_x": dest.x,
                            "dest_y": dest.y
                        })
                        segments = []
                        break  # skip to next row

                    key, attr = list(edge_dicts.items())[0]

                    if "geometry" in attr:
                        geom = attr["geometry"]
                        geom_type = "osm_edge"
                    else:
                        geom = LineString([
                            (G.nodes[u]["x"], G.nodes[u]["y"]),
                            (G.nodes[v]["x"], G.nodes[v]["y"])
                        ])
                        geom_type = "straight_line"

                    segments.append({
                        "u": u,
                        "v": v,
                        "id": attr.get("id") or attr.get("osmid"),
                        "length": attr.get("length"),
                        "highway": attr.get("highway"),
                        "oneway": attr.get("oneway"),
                        "geometry": geom,
                        "edge_type": geom_type,
                        "odid": odid,
                        "uid": uid,
                        "orig_x": orig.x,
                        "orig_y": orig.y,
                        "dest_x": dest.x,
                        "dest_y": dest.y
                    })

                if segments:
                    all_segments.extend(segments)

            except Exception as e:
                failed_routes.append({
                    "status": "fail",
                    "reason": str(e),
                    "odid": row.odid,
                    "uid": row.uid,
                    "orig_x": orig.x,
                    "orig_y": orig.y,
                    "dest_x": dest.x,
                    "dest_y": dest.y
                })

        # Write the current chunk to parquet
        chunk_counter += 1

        if all_segments:
            edges_gdf = gpd.GeoDataFrame(all_segments, geometry="geometry", crs="EPSG:4326")
            edges_gdf.to_parquet(
                os.path.join(output_dir, f"segments_chunk_{chunk_counter}.parquet"),
                index=False
            )
            all_segments = []  # clear memory

        if failed_routes:
            failed_df = pd.DataFrame(failed_routes)
            failed_df.to_parquet(
                os.path.join(output_dir, f"failed_routes_chunk_{chunk_counter}.parquet"),
                index=False
            )
            failed_routes = []  # clear memory









