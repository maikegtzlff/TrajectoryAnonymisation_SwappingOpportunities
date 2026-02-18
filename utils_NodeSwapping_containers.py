# --------------------------
# Imports
# --------------------------
from dataclasses import dataclass
from typing import List, Set, Tuple, Any, Dict
from collections import defaultdict, deque
import pandas as pd
import geopandas as gpd

# --------------------------
# TYPES
# --------------------------
EdgeKey = Tuple[int, int, int]      # (u, v, time_bin)
NodeKey = Tuple[int, int]           # (v_intersection_id_swap, time_bin)

# --------------------------
# POINT OBJECT
# --------------------------
@dataclass
class Point:
    point_id: int
    u: int
    v: int
    time_bin: int
    geometry: Any
    timestamp: Any
    uid: Any
    orig_tid: str
    v_intersection_id_swap: int = None
    is_node_arrival: bool = False

# --------------------------
# CONTAINER
# --------------------------
@dataclass
class Container:
    container_id: int
    points: List[Point]
    tid_subid: str
    key_set: Set[Any]   # EdgeKey or NodeKey
    swap_mode: str      # "edge" or "node"

    def rebuild_key_set(self):
        if self.swap_mode == "edge":
            self.key_set = {
                (p.u, p.v, p.time_bin) for p in self.points
            }
        elif self.swap_mode == "node":
            self.key_set = {
                (p.v_intersection_id_swap, p.time_bin)
                for p in self.points
                if p.v_intersection_id_swap is not None and p.is_node_arrival
            }
        else:
            raise ValueError("Unknown swap_mode")

# --------------------------
# SWAP HELPERS
# --------------------------
def first_common_key(a: Container, b: Container):
    common = a.key_set & b.key_set
    if not common:
        return None
    return next(iter(common))

def find_split_index(points: List[Point], key, swap_mode: str) -> int:
    if swap_mode == "edge":
        for i, p in enumerate(points):
            if (p.u, p.v, p.time_bin) == key:
                return i
    elif swap_mode == "node":
        for i, p in enumerate(points):
            if p.is_node_arrival and (p.v_intersection_id_swap, p.time_bin) == key:
                return i
    raise RuntimeError("Key not found in container points")

def swap_signature(a: Container, b: Container, key) -> Tuple:
    cid1, cid2 = sorted([a.container_id, b.container_id])
    return (cid1, cid2, *key)

def try_swap(a: Container, b: Container, seen_swaps: Set[Tuple], swap_log: List[dict]) -> bool:
    key = first_common_key(a, b)
    if key is None:
        return False
    sig = swap_signature(a, b, key)
    if sig in seen_swaps:
        return False

    # UID constraint: skip if any overlap
    if set(p.uid for p in a.points) & set(p.uid for p in b.points):
        return False

    ia = find_split_index(a.points, key, a.swap_mode)
    ib = find_split_index(b.points, key, b.swap_mode)

    tail_a = a.points[ia + 1 :]
    tail_b = b.points[ib + 1 :]

    if not tail_a and not tail_b:
        return False

    # Swap tails
    a.points = a.points[: ia + 1] + tail_b
    b.points = b.points[: ib + 1] + tail_a

    # Rebuild key sets
    a.rebuild_key_set()
    b.rebuild_key_set()

    seen_swaps.add(sig)

    swap_log.append({
        "cid_a": a.container_id,
        "cid_b": b.container_id,
        "key": key,
        "points_moved_a": len(tail_a),
        "points_moved_b": len(tail_b),
    })

    return True

# --------------------------
# KEY → CONTAINER MAPPING
# --------------------------
def build_key_to_container(containers: List[Container]) -> Dict[Any, Set[int]]:
    key_to_container = defaultdict(set)
    for c in containers:
        for k in c.key_set:
            key_to_container[k].add(c.container_id)
    return key_to_container

def update_key_to_container(key_to_container: Dict[Any, Set[int]], c: Container):
    for k, cid_set in key_to_container.items():
        cid_set.discard(c.container_id)
    for k in c.key_set:
        key_to_container[k].add(c.container_id)

# --------------------------
# NODE SWAPS LOOP (optimized, incremental)
# --------------------------
from collections import deque, defaultdict
from typing import List, Set

def run_node_swaps_queue_incremental(containers: List[Container], print_every: int = 500):
    """
    Queue-based node swapping with incremental key → container updates.
    Uses (v_intersection_id_swap, time_bin) as node key.
    Swaps propagate until no more swaps are possible.
    """

    swap_log = []
    seen_swaps: Set[tuple] = set()
    queue = deque(range(len(containers)))
    points_processed_so_far = 0
    swap_counter = 0

    # ----------------------------
    # Build initial key → container mapping
    # ----------------------------
    key_to_container = defaultdict(set)
    for c in containers:
        for k in c.key_set:
            key_to_container[k].add(c.container_id)

    # ----------------------------
    # Main queue loop
    # ----------------------------
    while queue:
        cid_a = queue.popleft()
        a = containers[cid_a]

        # Candidate containers sharing at least one key
        candidate_cids = set()
        for k in a.key_set:
            candidate_cids.update(key_to_container[k])
        candidate_cids.discard(cid_a)

        for cid_b in candidate_cids:
            b = containers[cid_b]

            # Skip if original UIDs overlap
            if set(p.uid for p in a.points) & set(p.uid for p in b.points):
                continue

            # Try swap
            key = first_common_key(a, b)
            if key is None:
                continue

            # Check if swap already done
            sig = swap_signature(a, b, key)
            if sig in seen_swaps:
                continue

            # Find split indices for tails
            ia = find_split_index(a.points, key, a.swap_mode)
            ib = find_split_index(b.points, key, b.swap_mode)

            tail_a = a.points[ia + 1 :]
            tail_b = b.points[ib + 1 :]

            if not tail_a and not tail_b:
                continue

            # ----------------------------
            # Perform the swap
            # ----------------------------
            a.points = a.points[: ia + 1] + tail_b
            b.points = b.points[: ib + 1] + tail_a

            # Rebuild keys
            old_keys_a = a.key_set.copy()
            old_keys_b = b.key_set.copy()
            a.rebuild_key_set()
            b.rebuild_key_set()

            # ----------------------------
            # Incremental mapping update
            # ----------------------------
            # Remove old keys
            for k in old_keys_a:
                key_to_container[k].discard(a.container_id)
            for k in old_keys_b:
                key_to_container[k].discard(b.container_id)

            # Add new keys
            for k in a.key_set:
                key_to_container[k].add(a.container_id)
            for k in b.key_set:
                key_to_container[k].add(b.container_id)

            # ----------------------------
            # Log swap
            # ----------------------------
            seen_swaps.add(sig)
            swap_log.append({
                "cid_a": a.container_id,
                "cid_b": b.container_id,
                "key": key,
                "points_moved_a": len(tail_a),
                "points_moved_b": len(tail_b),
            })

            swap_counter += 1
            points_processed_so_far += len(tail_a) + len(tail_b)

            # Re-add containers to queue for propagation
            if cid_a not in queue:
                queue.append(cid_a)
            if cid_b not in queue:
                queue.append(cid_b)

            # Optional: progress print
            if swap_counter % print_every == 0 or swap_counter == 1:
                print(f"[Swap {swap_counter}] Processed ~{points_processed_so_far} points")

    print(f"\nAll swaps completed! Total swaps: {swap_counter}")
    return swap_log


# --------------------------
# BUILD POINTS + CONTAINERS FROM GDF
# --------------------------
def build_containers_from_gdf(gdf: gpd.GeoDataFrame, swap_mode='node') -> List[Container]:
    containers = []
    points_by_tid = {}

    for tid, df_tid in gdf.groupby('tid_subid', sort=False):
        df_tid = df_tid.sort_values('time_bin')
        points_list = []
        for i, row in df_tid.iterrows():
            next_v = df_tid.iloc[i+1].v if i < len(df_tid)-1 else None
            v_swap = row.v if row.v != next_v else None
            p = Point(
                point_id=row.point_id,
                u=row.u,
                v=row.v,
                time_bin=int(row.time_bin),
                geometry=row.geometry,
                timestamp=row.unix_timestamp,
                uid=row.uid,
                orig_tid=row.tid_subid,
                v_intersection_id_swap=v_swap,
                is_node_arrival=(v_swap is not None)
            )
            points_list.append(p)

        container = Container(
            container_id=len(containers),
            points=points_list,
            tid_subid=tid,
            key_set=set(),
            swap_mode=swap_mode
        )
        container.rebuild_key_set()
        containers.append(container)

    return containers
