"""密码哈希（bcrypt，passlib）。"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt 只使用口令前 72 字节（bcrypt 5.x 对超长输入直接报错）
BCRYPT_MAX_BYTES = 72


def _to_bcrypt_input(plain: str) -> bytes:
    """统一的 bcrypt 输入归一化。

    哈希与校验必须走同一切片：多字节字符在 72 字节边界被切断时，
    两侧得到相同的字节前缀，验证才能与哈希一致。
    """
    return plain.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    return pwd_context.hash(_to_bcrypt_input(plain))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(_to_bcrypt_input(plain), hashed)
    except ValueError:
        return False
