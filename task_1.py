import argparse
import asyncio
from datetime import date, timedelta

from aiohttp import ClientSession, ClientError

EXCHANGE_API_URL = 'https://api.privatbank.ua/p24api/exchange_rates'
PB_API_DATE_FORMAT = '%d.%m.%Y'

DEFAULT_CURRENCY_LIST = ['USD', 'EUR']


class PBRequestError(Exception):
    pass


async def get_request_to_pb(url: str, params: dict):
    async with ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise PBRequestError(
                        f'Request status: {response.status}. Url: {url}, params: {params}'
                    )

                return await response.json()
        except ClientError as error:
            raise PBRequestError(f'Connection error: {url}', str(error))


def filter_exchange_info_by_currency(currency_exchange_info: dict, additional_currency_list: list):
    currency_list = DEFAULT_CURRENCY_LIST.copy()
    if additional_currency_list:
        currency_list.extend(additional_currency_list)

    currency_exchange_info['exchangeRate'] = [
        value for value in currency_exchange_info['exchangeRate']
        if value['currency'] in currency_list
    ]

    return currency_exchange_info


def reformat_currency_exchange_info(currency_exchange_info: dict):
    info_by_date = {}

    for value in currency_exchange_info['exchangeRate']:
        info_by_date[value['currency']] = {
            'sale': value.get('saleRate', 'unknown'),
            'purchase': value.get('purchaseRate', 'unknown')
        }

    return {currency_exchange_info['date']: info_by_date}


async def get_currency_exchange_info_for_period(days_offset: int, currency_list: list):
    if days_offset > 10 or days_offset <= 0:
        raise ValueError("Incorrect offset value. Please choose value from 1 to 10.")

    date_range = [date.today() - timedelta(days=i) for i in range(1, days_offset + 1)]
    date_range.reverse()  # to retrieve dates in chronological order

    currency_exchange_info = []

    for date_to_retrieve in date_range:
        params = {'date': date_to_retrieve.strftime(PB_API_DATE_FORMAT)}
        info_per_day = await get_request_to_pb(EXCHANGE_API_URL, params)

        filtered_info = filter_exchange_info_by_currency(info_per_day, currency_list)
        currency_exchange_info.append(reformat_currency_exchange_info(filtered_info))

    return currency_exchange_info


async def main():
    try:
        parser = argparse.ArgumentParser('PB currency exchange')

        parser.add_argument('days_offset', type=int)
        parser.add_argument('--currency', type=str, help='List of currency names separated with a comma,'
                                                         'e.g., "USD,EUR"')

        arguments = parser.parse_args()
        currency_list = arguments.currency.split(',') if arguments.currency else None

        result = await get_currency_exchange_info_for_period(arguments.days_offset, currency_list)
        print(result)
    except ValueError as error:
        print(error)
    except PBRequestError as error:
        print(f'Oops, something went wrong. Error: {error}.')


if __name__ == '__main__':
    asyncio.run(main())
