from random import seed, choices

from tonsdk.crypto._mnemonic import english
from tonsdk.crypto import mnemonic_is_valid
from tonsdk.utils import Address, InvalidAddressError, from_nano, TonCurrencyEnum


PASSWORD_SALT = "AHS6#$DJS66skaaa"


def password_to_wordlist(password: str, k: int = 24):
    seed(password + PASSWORD_SALT)

    while True:
        wordlist = choices(english, k=k)

        if not mnemonic_is_valid(wordlist):
            continue

        break

    return wordlist


def validate_address(address: str) -> bool:
    try:
        Address(address)
    except InvalidAddressError as e:
        print(e)
        return False

    return True


def to_ton(nano_ton: int) -> float:
    return from_nano(nano_ton, unit=TonCurrencyEnum.ton)


def is_unbounceable_address(address: str) -> bool:
    return address[0] == "U"


def change_address(address: str, bounceable: bool = True) -> str:
    addr = Address(address)
    return addr.to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=bounceable)
