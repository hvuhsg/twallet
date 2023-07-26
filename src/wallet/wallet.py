import os
from typing import List

from tonsdk.utils import to_nano
from tonsdk.contract.wallet import WalletVersionEnum, Wallets, WalletContract, SendModeEnum

from src.wallet.client import TonCenterTonClient, ToncenterClient, ToncenterWrongResult
from src.wallet.utils import password_to_wordlist


class Wallet:
    workchain: int = 0
    version = WalletVersionEnum.v3r2
    send_mode = SendModeEnum.pay_gas_separately.value
    toncenter_base_url = "https://toncenter.com/api/v2/"
    toncenter_api_key = os.environ["TONCENTER_API_KEY"]

    def __init__(self, private_key: bytes, public_key: bytes, wallet_contract: WalletContract, wordlist: list):
        self.private_key = private_key
        self.public_key = public_key
        self.wallet = wallet_contract
        self.wordlist = wordlist

        toncenter_client = ToncenterClient(base_url=self.toncenter_base_url, api_key=self.toncenter_api_key)
        self.client = TonCenterTonClient(toncenter_client)

    @property
    def address(self):
        return self.wallet.address.to_string(is_bounceable=True, is_url_safe=True, is_user_friendly=True)

    @property
    def unbounceable_address(self):
        return self.wallet.address.to_string(is_bounceable=False, is_url_safe=True, is_user_friendly=True)

    @property
    def initialized(self):
        return self.state != "uninitialized"

    @classmethod
    def from_password(cls, password: str):
        wordlist = password_to_wordlist(password=password)
        return cls.from_wordlist(wordlist)

    @classmethod
    def from_wordlist(cls, wordlist: List[str]):
        _, pub_key, priv_key, wallet = Wallets.from_mnemonics(mnemonics=wordlist, version=cls.version, workchain=cls.workchain)
        return Wallet(priv_key, pub_key, wallet, wordlist)

    async def load_state(self):
        # Load wallet state
        information = await self.client.get_address_information(self.address)
        self.balance = float(information["balance"])
        self.state = information["state"]
        if self.balance > 0 and not self.initialized:
            await self.initialize()

    async def initialize(self):
        result = self.wallet.create_init_external_message()
        boc = result["message"].to_boc(False)
        try:
            return await self.client.send_boc(boc)
        except ToncenterWrongResult as e:
            print("Initialization error", e)

    async def transfer(self, amount: float, address: str, comment: str):
        await self.load_state()

        nano_amount = to_nano(number=amount, unit="TON")
        result = self.wallet.create_transfer_message(
            address,
            nano_amount,
            payload=comment,
            seqno=int((await self.client.seqno(self.address))[0]["stack"][0][1], 16)
        )
        boc = result["message"].to_boc(False)
        result = await self.client.send_boc(boc)
        return result
