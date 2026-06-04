# gf256.py

GF_EXP = [0] * 512
GF_LOG = [0] * 256

def init_gf256():
    x = 1

    for i in range(255):
        GF_EXP[i] = x
        GF_LOG[x] = i

        x <<= 1
        if x & 0x100:
            x ^= 0x11D

    for i in range(255, 512):
        GF_EXP[i] = GF_EXP[i - 255]

    GF_LOG[0] = 255


init_gf256()


def mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]
