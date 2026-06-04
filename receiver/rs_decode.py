# rs_decode.py
# Reed-Solomon decoder (receiver side only, GF(256))

PRIMITIVE = 0x11d

gf_exp = [0] * 512
gf_log = [0] * 256


def init_gf():
    x = 1
    for i in range(255):
        gf_exp[i] = x
        gf_log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= PRIMITIVE

    for i in range(255, 512):
        gf_exp[i] = gf_exp[i - 255]


init_gf()


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return gf_exp[gf_log[a] + gf_log[b]]


def gf_div(a, b):
    if a == 0:
        return 0
    return gf_exp[(gf_log[a] - gf_log[b]) % 255]


# -----------------------------
# シンドローム計算
# -----------------------------
def calc_syndromes(codeword, nsym):
    syndromes = []
    for i in range(nsym):
        s = 0
        for j, c in enumerate(codeword):
            s ^= gf_mul(c, gf_exp[(i * j) % 255])
        syndromes.append(s)
    return syndromes


# -----------------------------
# Berlekamp–Massey（誤り位置多項式）
# -----------------------------
def berlekamp_massey(syndromes):
    n = len(syndromes)
    C = [1] + [0] * n
    B = [1] + [0] * n

    L = 0
    m = 1
    b = 1

    for n_i in range(n):
        d = syndromes[n_i]
        for i in range(1, L + 1):
            d ^= gf_mul(C[i], syndromes[n_i - i])

        if d == 0:
            m += 1
        else:
            T = C[:]
            coef = gf_div(d, b)

            for i in range(m, n + 1):
                if B[i - m]:
                    C[i] ^= gf_mul(coef, B[i - m])

            if 2 * L <= n_i:
                L = n_i + 1 - L
                B = T
                b = d
                m = 1
            else:
                m += 1

    return C[:L + 1]


# -----------------------------
# Chien search（誤り位置検出）
# -----------------------------
def chien_search(locator, length):
    error_pos = []

    for i in range(length):
        x = gf_exp[255 - i]
        val = 0

        for j, c in enumerate(locator):
            val ^= gf_mul(c, gf_exp[(j * gf_log[x]) % 255])

        if val == 0:
            error_pos.append(length - 1 - i)

    return error_pos


# -----------------------------
# Forney algorithm（誤り修正）
# -----------------------------
def forney_syndromes(syndromes, error_pos, nsym):
    fsynd = syndromes[:]
    for i in range(len(error_pos)):
        x = gf_exp[error_pos[i]]
        for j in range(len(fsynd) - 1):
            fsynd[j] = fsynd[j + 1] ^ gf_mul(x, fsynd[j])
        fsynd.pop()
    return fsynd


def correct_errors(codeword, syndromes, locator, error_pos):
    msg = codeword[:]

    for pos in error_pos:
        x = gf_exp[pos]
        err = 0

        for i in range(len(locator)):
            err ^= gf_mul(locator[i], gf_exp[(i * gf_log[x]) % 255])

        msg[pos] ^= err

    return msg


# -----------------------------
# メイン復号関数
# -----------------------------
def rs_decode(codeword: list[int], nsym: int):
    syndromes = calc_syndromes(codeword, nsym)

    if max(syndromes) == 0:
        return codeword[:-nsym]

    locator = berlekamp_massey(syndromes)
    error_pos = chien_search(locator, len(codeword))

    if not error_pos:
        raise ValueError("Too many errors to correct")

    corrected = correct_errors(codeword, syndromes, locator, error_pos)

    return corrected[:-nsym]
