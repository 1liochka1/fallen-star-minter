import random
from eth_abi import encode
from eth_utils import to_hex
from tqdm import tqdm
from web3 import Web3
from loguru import logger
from moralis import evm_api
import time

from info import abi, scans, balances, gas_holo, lzEndpointABI, holo_abi, holograph_ids, Lz_ids
from config import rpcs

class Help:
    def check_status_tx(self, tx_hash):
        logger.info(f'{self.address} - жду подтверждения транзакции  {scans[self.chain]}{self.w3.to_hex(tx_hash)}...')

        start_time = int(time.time())
        while True:
            current_time = int(time.time())
            if current_time >= start_time + 100:
                logger.info(
                    f'{self.address} - транзакция не подтвердилась за 100 cекунд, начинаю повторную отправку...')
                return 0
            try:
                status = self.w3.eth.get_transaction_receipt(tx_hash)['status']
                if status == 1:
                    return status
                time.sleep(1)
            except Exception as error:
                time.sleep(1)

    def sleep_indicator(self, sec):
        for i in tqdm(range(sec), desc='жду', bar_format="{desc}: {n_fmt}c /{total_fmt}c {bar}", colour='green'):
            time.sleep(1)

class Minter(Help):
    def __init__(self, privatekey, chain, count, delay, mode):
        self.privatekey = privatekey
        self.chain = chain if chain else ''
        self.drop_address = Web3.to_checksum_address('0xe5325804d68033edf65a86403b2592a99e1f06de')
        self.mode = mode
        self.count = random.randint(count[0], count[1]) if type(count) == list else count
        self.w3 = ''
        self.delay = random.randint(delay[0], delay[1])
        self.account = ''
        self.address = ''

    def balance(self):
        chainss = ['avax', 'polygon', 'bsc', 'opti', 'mantle']
        random.shuffle(chainss)
        for i in chainss:
            w3 = Web3(Web3.HTTPProvider(rpcs[i]))
            acc = w3.eth.account.from_key(self.privatekey)
            address = acc.address
            balance = w3.eth.get_balance(address)
            if balance / 10 ** 18 > balances[i]:
                return i

        return False

    def mint(self):
        if self.mode == 1:
            chain = self.balance()
            if chain:
                self.chain = chain
            else:
                return self.privatekey, self.address, 'error'

        self.w3 = Web3(Web3.HTTPProvider(rpcs[self.chain]))
        self.account = self.w3.eth.account.from_key(self.privatekey)
        self.address = self.account.address
        while True:
            try:
                nonce = self.w3.eth.get_transaction_count(self.address)
                contract = self.w3.eth.contract(address=self.drop_address, abi=abi)
                tx = contract.functions.purchase(self.count).build_transaction({
                    'from': self.address,
                    'gas': contract.functions.purchase(self.count).estimate_gas(
                        {'from': self.address, 'nonce': nonce}),
                    'nonce': nonce,
                    'maxFeePerGas': int(self.w3.eth.gas_price),
                    'maxPriorityFeePerGas': int(self.w3.eth.gas_price * 0.8)
                })
                if self.chain == 'bsc':
                    del tx['maxFeePerGas']
                    del tx['maxPriorityFeePerGas']
                    tx['gasPrice'] = self.w3.eth.gas_price
                sign = self.account.sign_transaction(tx)
                hash_ = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                status = self.check_status_tx(hash_)
                if status == 1:
                    logger.info(
                        f'{self.address}:{self.chain} - успешно заминтил {self.count} Fallen Star {scans[self.chain]}{self.w3.to_hex(hash_)}...')
                    self.sleep_indicator(self.delay)
                    return self.privatekey, self.address, 'success'
            except Exception as e:
                error = str(e)
                if "insufficient funds for gas * price + value" in error:
                    logger.error(f'{self.address}:{self.chain} - нет баланса нативного токена')
                    return self.privatekey, self.address, 'error'
                elif 'nonce too low' in error or 'already known' in error:
                    logger.info(f'{self.address}:{self.chain} - пробую еще раз...')
                    self.mint()
                else:
                    logger.error(f'{self.address}:{self.chain}  - {e}')
                    return self.privatekey, self.address, 'error'


class Bridger(Help):
    def __init__(self, privatekey, chain, to, delay, api, mode):
        self.privatekey = privatekey
        self.chain = chain
        self.to = random.choice(to) if type(to) == list else to
        self.w3 = ''
        self.scan = ''
        self.account = ''
        self.address = ''
        self.mode = mode
        self.delay = random.randint(delay[0], delay[1])
        self.moralisapi = api
        self.HolographBridgeAddress = Web3.to_checksum_address('0xD85b5E176A30EdD1915D6728FaeBD25669b60d8b')
        self.LzEndAddress = Web3.to_checksum_address('0x3c2269811836af69497E5F486A85D7316753cf62' if self.chain != 'mantle' else '0xb6319cC6c8c27A8F5dAF0dD3DF91EA35C4720dd7')
        self.nft_address = Web3.to_checksum_address('0xe5325804d68033edf65a86403b2592a99e1f06de')

    def check_nft(self):
        if self.mode == 0 and self.chain not in ['opti', 'mantle']:
            cc = {'avax': 'avalanche',
                  'polygon': 'polygon',
                  'bsc': 'bsc'}
            api_key = self.moralisapi
            params = {
                "chain": cc[self.chain],
                "format": "decimal",
                "token_addresses": [
                    self.nft_address
                ],
                "media_items": False,
                "address": self.address}
            try:
                result = evm_api.nft.get_wallet_nfts(api_key=api_key, params=params)
                id_ = int(result['result'][0]['token_id'])
                if id_:
                    logger.success(f'{self.address} - Fallen Star {id_} nft founded on {self.chain}...')
                    return id_
            except Exception as e:
                logger.error(f'{self.address} - Fallen Star nft not in wallet...')
                return False

        elif self.mode == 0 and self.chain in ['opti', 'mantle']:
            contract_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "tokensOfOwner",
                    "outputs": [{"name": "tokenIds", "type": "uint256[]"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            contract = self.w3.eth.contract(address=self.nft_address, abi=contract_abi)
            try:
                bal = contract.functions.balanceOf(self.address).call()
                if bal:
                    id_ = contract.functions.tokensOfOwner(self.address).call()[0]
                    logger.success(f'{self.address} - Fallen Star {id_} nft founded on {self.chain}...')
                    return id_
                else:
                    logger.error(f'{self.address} - Fallen Star nft not in wallet...')
                    return False
            except Exception as e:
                time.sleep(1)

        elif self.mode == 1:
            for chain in ['avalanche', 'polygon', 'bsc']:

                api_key = self.moralisapi
                params = {
                    "chain": chain,
                    "format": "decimal",
                    "token_addresses": [
                        self.nft_address
                    ],
                    "media_items": False,
                    "address": self.address}
                try:
                    result = evm_api.nft.get_wallet_nfts(api_key=api_key, params=params)
                    id_ = int(result['result'][0]['token_id'])
                    if id_:
                        logger.success(f'{self.address} - Fallen Star {id_} nft founded on {chain}...')
                        if chain == 'avalanche': chain = 'avax'
                        return chain, id_

                except Exception as e:
                    if 'list index out of range' in str(e):
                        continue

            if self.chain in ['opti', 'mantle']:
                contract_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "tokensOfOwner",
                    "outputs": [{"name": "tokenIds", "type": "uint256[]"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
                contract = self.w3.eth.contract(address=self.nft_address, abi=contract_abi)
                try:
                    bal = contract.functions.balanceOf(self.address).call()
                    if bal:
                        id_ = contract.functions.tokensOfOwner(self.address).call()[0]
                        logger.success(f'{self.address} - Fallen Star {id_} nft founded on {self.chain}...')
                        return id_
                    else:
                        logger.error(f'{self.address} - Fallen Star nft not in wallet...')
                        return False
                except Exception as e:
                    time.sleep(1)

            logger.error(f'{self.address} - Fallen Star nft not in wallet...')
            return False

    def bridge(self):
        if self.mode == 0:
            self.w3 = Web3(Web3.HTTPProvider(rpcs[self.chain]))
            self.scan = scans[self.chain]
            self.account = self.w3.eth.account.from_key(self.privatekey)
            self.address = self.account.address
            data = self.check_nft()
            if data:
                nft_id = data
            else:
                return self.privatekey, self.address, 'Fallen Star nft not in wallet'

        elif self.mode == 1:
            self.w3 = Web3(Web3.HTTPProvider(rpcs['bsc']))
            self.address = self.w3.eth.account.from_key(self.privatekey).address
            data = self.check_nft()

            if data:
                chain, nft_id = data
                self.chain = chain
                self.w3 = Web3(Web3.HTTPProvider(rpcs[self.chain]))
                self.scan = scans[self.chain]
                self.account = self.w3.eth.account.from_key(self.privatekey)
                self.address = self.account.address
                if chain == self.to:
                    chains = ['avax', 'polygon', 'bsc']
                    chains.remove(self.to)
                    self.to = random.choice(chains)
            else:
                return self.privatekey, self.address, 'Fallen Star nft not in wallet'

        payload = to_hex(encode(['address', 'address', 'uint256'], [self.address, self.address, nft_id]))
        gas_price = gas_holo[self.to]
        gas_lim = random.randint(450000, 500000)

        holograph = self.w3.eth.contract(address=self.HolographBridgeAddress, abi=holo_abi)
        lzEndpoint = self.w3.eth.contract(address=self.LzEndAddress, abi=lzEndpointABI)

        lzFee = lzEndpoint.functions.estimateFees(Lz_ids[self.to], self.HolographBridgeAddress, '0x', False, '0x').call()[0]
        lzFee = int(lzFee * 2.5)
        to = holograph_ids[self.to]

        while True:
            logger.info(f'{self.address}:{self.chain} - trying to bridge... ')
            try:
                tx = holograph.functions.bridgeOutRequest(to, self.nft_address, gas_lim, gas_price,
                                                          payload).build_transaction({
                    'from': self.address,
                    'value': lzFee,
                    'gas': holograph.functions.bridgeOutRequest(to, self.nft_address, gas_lim, gas_price,
                                                                payload).estimate_gas(
                        {'from': self.address, 'value': lzFee,
                         'nonce': self.w3.eth.get_transaction_count(self.address)}),
                    'nonce': self.w3.eth.get_transaction_count(self.address),
                    'maxFeePerGas': int(self.w3.eth.gas_price),
                    'maxPriorityFeePerGas': int(self.w3.eth.gas_price * 0.8)
                })
                if self.chain == 'bsc':
                    del tx['maxFeePerGas']
                    del tx['maxPriorityFeePerGas']
                    tx['gasPrice'] = self.w3.eth.gas_price
                sign = self.account.sign_transaction(tx)
                hash_ = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                status = self.check_status_tx(hash_)
                if status == 1:
                    logger.success(
                        f'{self.address}:{self.chain} - successfully bridged Fallen Star {nft_id} to {self.to} : {self.scan}{self.w3.to_hex(hash_)}...')
                    self.sleep_indicator(self.delay)
                    return self.privatekey, self.address, 'success'
            except Exception as e:
                error = str(e)
                if "insufficient funds for gas * price + value" in error:
                    logger.error(f'{self.address}:{self.chain} - нет баланса нативного токена')
                    return self.privatekey, self.address, 'error'
                elif 'nonce too low' in error or 'already known' in error:
                    logger.info(f'{self.address}:{self.chain} - пробую еще раз...')
                    self.bridge()
                else:
                    logger.error(f'{self.address}:{self.chain}  - {e}')
                    return self.privatekey, self.address, 'error'

