# GF(256) 定数
# Primitive Polynomial : x^8+x^4+x^3+x^2+1
# 0x11D
PRIMITIVE_POLYNOMIAL = 0x11D

GF_EXP = [0] * 512
GF_LOG = [0] * 256

# GF(256) 初期化
# GF(256)で使用する指数表・対数表を生成する
def initialize_gf256_table():

    value = 1

    for i in range(255):
        GF_EXP[i] = value
        GF_LOG[value] = i
        value <<= 1

        if value & 0x100:
            value ^= PRIMITIVE_POLYNOMIAL

    for i in range(255, 512):
        GF_EXP[i] = GF_EXP[i - 255]

initialize_gf256_table()

# GF(256) 加算・減算

def add_gf256(a: int, b: int) -> int:
    return a ^ b


def subtract_gf256(a: int, b: int) -> int:
    return a ^ b

# GF(256) 乗算

def multiply_gf256(a: int, b: int) -> int:

    if a == 0 or b == 0:
        return 0

    return GF_EXP[
        (GF_LOG[a] + GF_LOG[b]) % 255
    ]

# GF(256) 除算

def divide_gf256(a: int, b: int):

    if b == 0:
        raise ZeroDivisionError(
            "GF256 divide by zero"
        )

    if a == 0:
        return 0

    return GF_EXP[
        (GF_LOG[a] - GF_LOG[b]) % 255
    ]

# GF(256) 累乗

def power_gf256(a: int, power: int):

    if power == 0:
        return 1

    if a == 0:
        return 0

    return GF_EXP[
        (GF_LOG[a] * power) % 255
    ]

# GF(256) 逆数

def inverse_gf256(a: int):

    if a == 0:
        raise ZeroDivisionError(
            "inverse of zero"
        )

    return GF_EXP[
        255 - GF_LOG[a]
    ]


# byte → 4bitシンボル

def convert_bytes_to_fsk_symbols(
        byte_data: list[int]
) -> list[int]:

    symbols = []

    for byte in byte_data:
        upper = (byte >> 4) & 0x0F
        lower = byte & 0x0F

        symbols.append(upper)
        symbols.append(lower)

    return symbols


# 4bitシンボル → byte

def convert_fsk_symbols_to_bytes(
        symbols: list[int]
) -> list[int]:

    if len(symbols) % 2 != 0:
        raise ValueError(
            "シンボル数が奇数です"
        )

    byte_data = []

    for i in range(0, len(symbols), 2):

        value = (
            (symbols[i] << 4)
            | symbols[i + 1]
        )

        byte_data.append(value)

    return byte_data

# 多項式演算

def polynomial_scale(poly: list[int], x: int) -> list[int]: # 多項式の各係数をx倍する
    return [multiply_gf256(c, x) for c in poly]


def polynomial_add(poly1: list[int], poly2: list[int]) -> list[int]:

    length = max(len(poly1), len(poly2))
    result = [0] * length

    for i in range(length):
        a = poly1[i] if i < len(poly1) else 0
        b = poly2[i] if i < len(poly2) else 0

        result[i] = a ^ b

    return result


def polynomial_multiply(poly1: list[int],
                        poly2: list[int]) -> list[int]: # GF(256)上での多項式乗算


    result = [0] * (len(poly1) + len(poly2) - 1)

    for i in range(len(poly1)):
        for j in range(len(poly2)):

            result[i + j] ^= multiply_gf256(
                poly1[i],
                poly2[j]
            )

    return result


def polynomial_evaluate(
        poly:list[int],
        x:int
):

    result = 0
    power = 1


    for coefficient in poly:
        result ^= multiply_gf256(
            coefficient,
            power
        )

        power = multiply_gf256(
            power,
            x
        )

    return result


# RS生成多項式

def generate_rs_generator_polynomial(
        parity_symbols
):

    generator=[1]


    for i in range(parity_symbols):

        generator = polynomial_multiply(
            generator,
            [
                GF_EXP[i],
                1
            ]
        )


    return generator


# RS符号化

def add_rs_parity(
        message_bytes: list[int],
        parity_symbols: int
) -> list[int]:


    generator = generate_rs_generator_polynomial(
        parity_symbols
    )


    encoded = (
        message_bytes
        +
        [0]*parity_symbols
    )


    generator_degree = len(generator)-1


    # 低次順多項式除算
    for i in range(len(message_bytes)):

        coefficient = encoded[i]


        if coefficient == 0:
            continue


        factor = divide_gf256(
            coefficient,
            generator[0]
        )


        for j in range(len(generator)):

            encoded[i+j] ^= multiply_gf256(
                generator[j],
                factor
            )


    parity = encoded[-parity_symbols:]


    return message_bytes + parity
    
    
# 文字列→RS符号付きbyte列
# UTF-8文字列へRSパリティを追加

def create_rs_protected_bytes(
        text: str,
        parity_symbols: int = 16
) -> list[int]:

    message_bytes = list(
        text.encode("utf-8")
    )

    return add_rs_parity(
        message_bytes,
        parity_symbols
    )


# 文字列→16FSKシンボル列

def convert_text_to_fsk_symbols(
        text: str,
        parity_symbols: int = 16
) -> list[int]:

    protected_bytes = create_rs_protected_bytes(
        text,
        parity_symbols
    )

    return convert_bytes_to_fsk_symbols(
        protected_bytes
    )


# シンドローム計算

def calculate_rs_syndromes(
        codeword:list[int],
        parity_symbols:int
):

    syndromes=[]

    for i in range(parity_symbols):
        x = GF_EXP[i]
        syndrome = 0
        power = 1

        for coefficient in codeword:
            syndrome ^= multiply_gf256(
                coefficient,
                power
            )

            power = multiply_gf256(
                power,
                x
            )

        syndromes.append(
            syndrome
        )

    return syndromes


# 誤り検出
# RS符号語に誤りがあるか判定する

def has_rs_error(
        codeword: list[int],
        parity_symbols: int
) -> bool:

    syndromes = calculate_rs_syndromes(
        codeword,
        parity_symbols
    )

    return any(s != 0 for s in syndromes)

# Berlekamp–Massey法
# シンドロームから誤り位置多項式σ(x)を求める

def berlekamp_massey(
        syndromes: list[int]
):

    sigma = [1]
    previous_sigma = [1]

    L = 0
    m = 1
    b = 1

    for n in range(len(syndromes)):

        # discrepancy計算

        discrepancy = syndromes[n]

        for i in range(1, L + 1):

            discrepancy ^= multiply_gf256(
                sigma[i],
                syndromes[n - i]
            )

        # d==0

        if discrepancy == 0:

            m += 1
            continue
          
        # σを保存

        temp_sigma = sigma[:]

        scale = divide_gf256(
            discrepancy,
            b
        )

        while len(sigma) < len(previous_sigma) + m:
            sigma.append(0)

        for i in range(len(previous_sigma)):

            sigma[i + m] ^= multiply_gf256(
                previous_sigma[i],
                scale
            )

        # 更新判定

        if 2 * L <= n:
            L = n + 1 - L
            previous_sigma = temp_sigma
            b = discrepancy
            m = 1

        else:
            m += 1

    return sigma, L


# Chien Search

def chien_search(
        error_locator,
        code_length
):

    error_positions=[]

    for i in range(code_length):
        x = GF_EXP[
            (255-i)%255
        ]

        if polynomial_evaluate(
            error_locator,
            x
        ) == 0:

            error_positions.append(i)

    return error_positions


# 誤り評価多項式

def calculate_error_evaluator(
        syndromes: list[int],
        locator: list[int],
        parity_symbols: int
):

    # S(x)=S1*x+S2*x^2+...
    syndrome_poly = [0] + syndromes

    product = polynomial_multiply(
        syndrome_poly,
        locator
    )

    # x^(2t)以上を捨てる
    omega = product[:parity_symbols]

    return omega

# 誤り位置多項式の微分
# GF(256)上の多項式微分
# GF(2^m)では偶数次数項は消える

def formal_derivative(
        polynomial: list[int]
):

    result = []

    for i in range(1, len(polynomial)):
        if i % 2 == 1:
            result.append(
                polynomial[i]
            )

        else:
            result.append(0)

    if len(result) == 0:
        return [0]

    return result


# Forney法
# 誤り値を計算する

def forney_algorithm(
        syndromes,
        error_locator,
        error_positions
):

    error_evaluator = calculate_error_evaluator(
        syndromes,
        error_locator,
        len(syndromes)
    )

    locator_derivative = formal_derivative(
        error_locator
    )

    error_values = []

    for position in error_positions:

        # X = α^position

        x = GF_EXP[
            (255-position)%255
        ]

        x_eval = inverse_gf256(x)

        numerator = polynomial_evaluate(
            error_evaluator,
            x_eval
        )

        denominator = polynomial_evaluate(
            locator_derivative,
            x_eval
        )

        magnitude = divide_gf256(
            numerator,
            denominator
        )

        error_values.append(
            magnitude
        )

    return error_values

# RS誤り訂正
# RS符号語の誤りを訂正する

def correct_rs_errors(
        codeword: list[int],
        parity_symbols: int
):

    syndromes = calculate_rs_syndromes(
        codeword,
        parity_symbols
    )

    # 誤りなし

    if not any(syndromes):

        return codeword

    locator, error_count = berlekamp_massey(
        syndromes
    )

    error_positions = chien_search(
        locator,
        len(codeword)
    )

    if len(error_positions) != error_count:

        raise ValueError(
            "誤り位置を特定できません"
        )

    error_values = forney_algorithm(
        syndromes,
        locator,
        error_positions
    )

    corrected = codeword[:]

    for pos, value in zip(
            error_positions,
            error_values
    ):

        corrected[pos] ^= value

    return corrected


# RS復号
# 受信したRS符号を復号する

def rs_decode(
        received: list[int],
        parity_symbols: int = 16
):

    corrected = correct_rs_errors(
        received,
        parity_symbols
    )

    # パリティ除去

    message = corrected[:-parity_symbols]

    return message
