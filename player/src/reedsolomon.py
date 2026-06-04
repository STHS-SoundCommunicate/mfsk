# reedsolomon.py

from gf256 import GF_EXP, mul


def poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)

    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= mul(a, b)

    return r


def generator_poly(nsym):
    g = [1]

    for i in range(nsym):
        g = poly_mul(g, [1, GF_EXP[i]])

    return g


def encode(msg, nsym=8):
    gen = generator_poly(nsym)
    parity = [0] * nsym

    for byte in msg:
        fb = byte ^ parity[0]
        parity = parity[1:] + [0]

        for i in range(nsym):
            parity[i] ^= mul(fb, gen[i + 1])

    return msg + parity
