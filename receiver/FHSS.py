import random

HOP_ROOMS = [11000, 13000, 15000, 17000]
HOP_SEED = 1414


def return_fhss(index: int, seed: int = HOP_SEED) -> int:
    if index < 0:
        raise ValueError("index must be >= 0")
    if not HOP_ROOMS:
        raise ValueError("HOP_ROOMS must not be empty")
    rng = random.Random(seed + index)
    return HOP_ROOMS[rng.randrange(len(HOP_ROOMS))]
