from dataclasses import dataclass
from typing import List, Set, Tuple, Any, Dict
from collections import defaultdict

Key = Tuple[int, int, int]  # (u, v, time_bin)


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


@dataclass
class Container:
    container_id: int
    points: List[Point]
    tid_subid: str
    key_set: Set[Key]

    def rebuild_key_set(self):
        self.key_set = {(p.u, p.v, p.time_bin) for p in self.points}


# ---------------------------------------------------------------------
# Swap helpers
# ---------------------------------------------------------------------

def first_common_key(a: Container, b: Container) -> Key | None:
    common = a.key_set & b.key_set
    if not common:
        return None
    return next(iter(common))


def find_split_index(points: List[Point], key: Key) -> int:
    for i, p in enumerate(points):
        if (p.u, p.v, p.time_bin) == key:
            return i
    raise RuntimeError("Key not found in container points")


def swap_signature(a: Container, b: Container, key: Key) -> Tuple:
    cid1, cid2 = sorted([a.container_id, b.container_id])
    u, v, tb = key
    return (cid1, cid2, u, v, tb)


def try_swap(a: Container, b: Container, seen_swaps: Set[Tuple], swap_log: List[dict]) -> bool:
    key = first_common_key(a, b)
    if key is None:
        return False

    sig = swap_signature(a, b, key)
    if sig in seen_swaps:
        return False  # swap prevention memory

    # UID constraint
    if set(p.uid for p in a.points) & set(p.uid for p in b.points):
        return False

    ia = find_split_index(a.points, key)
    ib = find_split_index(b.points, key)

    tail_a = a.points[ia + 1 :]
    tail_b = b.points[ib + 1 :]

    if not tail_a and not tail_b:
        return False

    # Swap tails
    a.points = a.points[: ia + 1] + tail_b
    b.points = b.points[: ib + 1] + tail_a

    # rebuild key sets
    a.rebuild_key_set()
    b.rebuild_key_set()

    seen_swaps.add(sig)

    # Log the swap
    swap_log.append({
        "cid_a": a.container_id,
        "cid_b": b.container_id,
        "key": key,
        "points_moved_a": len(tail_a),
        "points_moved_b": len(tail_b),
    })

    return True


# ---------------------------------------------------------------------
# Key --> container mapping helpers
# ---------------------------------------------------------------------

def build_key_to_container(containers: List[Container]) -> Dict[Key, Set[int]]:
    key_to_container = defaultdict(set)
    for c in containers:
        for k in c.key_set:
            key_to_container[k].add(c.container_id)
    return key_to_container


def update_key_to_container(key_to_container: Dict[Key, Set[int]], c: Container):
    # remove previous entries
    for k, cid_set in key_to_container.items():
        cid_set.discard(c.container_id)
    # add current keys
    for k in c.key_set:
        key_to_container[k].add(c.container_id)
