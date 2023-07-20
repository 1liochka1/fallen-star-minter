import random
import csv
from loguru import logger

from utils import Minter, Bridger
from info import keys
from config import shuffle, MODE, chain, to_chain, moralis_api, delay, count
from config import minter_mode, bridger_mode



def write_to_csv(key, address, result):
    with open('result.csv', 'a', newline='') as file:
        writer = csv.writer(file)

        if file.tell() == 0:
            writer.writerow(['key', 'address', 'result'])

        writer.writerow([key, address, result])

def main():
    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')
    if shuffle:
        random.shuffle(keys)

    if MODE == 'minter':
        logger.info('Запущен минтер azure...')
        for key in keys:
            mint_ = Minter(key, chain, count, delay, minter_mode)
            res = mint_.mint()
            write_to_csv(*res)
    if MODE == 'bridger':
        logger.info('Запущен бриджер azure...')
        for key in keys:
            bridge_ = Bridger(key, chain, to_chain, delay, moralis_api, bridger_mode)
            res = bridge_.bridge()
            write_to_csv(*res)


    if MODE == 'minter':
        logger.success('mинетинг закончен...')
    else:
        logger.success('бриджетинг закончен...')

    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')
    print(f'\n{" " * 32}donate - EVM 0xFD6594D11b13C6b1756E328cc13aC26742dBa868{" " * 32}\n')
    print(f'\n{" " * 32}donate - trc20 TMmL915TX2CAPkh9SgF31U4Trr32NStRBp{" " * 32}\n')


if __name__ == '__main__':
    main()
