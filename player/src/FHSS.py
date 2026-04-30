import numpy as np
from const import *

HOP_ROOMS = [11000, 13000 , 15000, 17000, 19000]

np.random.seed(1414)

def generate_hop_pattern():
    hop_pattern = np.random.choice(HOP_ROOMS, size=10000, replace=True)
    return hop_pattern

hop_pattern = generate_hop_pattern()

def return_fhss(index: int) -> int:
	return hop_pattern[index]