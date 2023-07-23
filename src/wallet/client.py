from abc import ABC, abstractmethod
import asyncio

import aiohttp
from tvm_valuetypes import serialize_tvm_stack
from tonsdk.provider import ToncenterClient, ToncenterWrongResult, prepare_address, address_state
from tonsdk.utils import TonCurrencyEnum, from_nano
from tonsdk.boc import Cell


class AbstractTonClient(ABC):
    @abstractmethod
    async def _run(self, to_run, *, single_query=True):
        raise NotImplemented

    async def get_address_information(self, address: str,
                                currency_to_show: TonCurrencyEnum = TonCurrencyEnum.ton):
        return (await self.get_addresses_information([address], currency_to_show))[0]

    async def get_addresses_information(self, addresses,
                                  currency_to_show: TonCurrencyEnum = TonCurrencyEnum.ton):
        if not addresses:
            return []

        tasks = []
        for address in addresses:
            address = prepare_address(address)
            tasks.append(self.provider.raw_get_account_state(address))

        results = await self._run(tasks, single_query=False)

        for result in results:
            result["state"] = address_state(result)
            if "balance" in result:
                if int(result["balance"]) < 0:
                    result["balance"] = 0
                else:
                    result["balance"] = from_nano(
                        int(result["balance"]), currency_to_show)

        return results

    async def seqno(self, addr: str):
        addr = prepare_address(addr)
        result = await self._run(self.provider.raw_run_method(addr, "seqno", []))

        if 'stack' in result and ('@type' in result and result['@type'] == 'smc.runResult'):
            result['stack'] = serialize_tvm_stack(result['stack'])

        return result

    async def send_boc(self, boc: Cell):
        return await self._run(self.provider.raw_send_message(boc))


class TonCenterTonClient(AbstractTonClient):
    def __init__(self, toncenter_client: ToncenterClient):
        self.provider = toncenter_client

    async def _run(self, to_run, *, single_query=True):
        try:
            return await self.__execute(to_run, single_query)

        except (ToncenterWrongResult, asyncio.exceptions.TimeoutError, aiohttp.client_exceptions.ClientConnectorError):
            raise

    async def __execute(self, to_run, single_query):
        timeout = aiohttp.ClientTimeout(total=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            if single_query:
                to_run = [to_run]

            tasks = []
            for task in to_run:
                tasks.append(task["func"](
                    session, *task["args"], **task["kwargs"]))

            return await asyncio.gather(*tasks)