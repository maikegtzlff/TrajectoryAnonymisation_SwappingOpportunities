from dataclasses import dataclass
from typing import List, Set, Tuple, Any, Dict
from collections import defaultdict



# TYPE DEFINITION
# Edge key (unchanged)
EdgeKey = Tuple[int, int, int]        # (u, v, time_bin)

# Node key (new)
NodeKey = Tuple[int, int]             # (node_id, time_bin)




# BUILDING POINT OBJECTS
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

    v_is_intersection: bool
    is_node_arrival: bool



# CONTAINTER supporting edge or node keys
@dataclass
class Container:
    container_id: int
    points: List[Point]
    tid_subid: str
    key_set: Set[Any]   # can be EdgeKey or NodeKey
    swap_mode: str      # "edge" or "node"

    def rebuild_key_set(self):

        if self.swap_mode == "edge":
            self.key_set = {
                (p.u, p.v, p.time_bin)
                for p in self.points
            }

        elif self.swap_mode == "node":
            self.key_set = {
                (p.v, p.time_bin)
                for p in self.points
                if p.v_is_intersection and p.is_node_arrival
            }

        else:
            raise ValueError("Unknown swap_mode")


# SWAP HELPERS
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
            if (
                p.v_is_intersection
                and p.is_node_arrival
                and (p.v, p.time_bin) == key
            ):
                return i

    raise RuntimeError("Key not found in container points")


def swap_signature(a: Container, b: Container, key) -> Tuple:
    cid1, cid2 = sorted([a.container_id, b.container_id])
    return (cid1, cid2, *key)


# SWAPPING FUNCTION
def try_swap(a: Container, b: Container, seen_swaps: Set[Tuple], swap_log: List[dict]) -> bool:

    key = first_common_key(a, b)
    if key is None:
        return False

    sig = swap_signature(a, b, key)
    if sig in seen_swaps:
        return False

    # UID constraint
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

    # Rebuild keys (important)
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


# KEY to CONTAINER MAPPING
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


# Queue-based node swapping - swaps properagte until no more swaps are possible
from collections import deque, defaultdict
from typing import List, Set

def run_node_swaps_queue(containers: List[Container]):
    """
    Queue-based node swapping until convergence.
    Works with node keys (v, time_bin) where is_node_arrival and v_is_intersection are True.
    """

    swap_log = []
    seen_swaps = set()

    # Initialize queue with all container indices
    queue = deque(range(len(containers)))
    points_processed_so_far = 0
    swap_counter = 0

    while queue:
        cid_a = queue.popleft()
        a = containers[cid_a]

        # Build current key → container mapping
        key_to_container = defaultdict(set)
        for c in containers:
            for k in c.key_set:
                key_to_container[k].add(c.container_id)

        # Candidate containers sharing at least one key
        candidate_cids = set()
        for k in a.key_set:
            candidate_cids.update(key_to_container[k])
        candidate_cids.discard(cid_a)

        for cid_b in candidate_cids:
            b = containers[cid_b]

            if set(p.uid for p in a.points) & set(p.uid for p in b.points):
                continue  # skip if same original UID

            # Try swap
            if try_swap(a, b, seen_swaps, swap_log):
                swap_counter += 1

                # Re-add to queue to allow propagation
                if cid_a not in queue:
                    queue.append(cid_a)
                if cid_b not in queue:
                    queue.append(cid_b)

                # Track points processed (optional)
                ia = find_split_index(a.points, first_common_key(a,b), 'node')
                ib = find_split_index(b.points, first_common_key(a,b), 'node')
                points_processed_so_far += len(a.points[ia+1:]) + len(b.points[ib+1:])

        # Optional: print progress every 500 swaps
        if swap_counter == 1 or swap_counter % 500 == 0:
            print(f"[Swap {swap_counter}] Processed ~{points_processed_so_far} points")

    print("\nAll swaps completed!")
    return swap_log
