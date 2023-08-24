import itertools
import csv
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth


class UserInformation:
    username = 'YOUR_USERNAME_HERE'
    password = 'YOUR_PASSWORD_HERE'
    business_partner = 'YOUR_BUSINESS_PARTNER_HERE'


def get_data_from_chargedetailrecord_api(user_info: UserInformation):
    result = []
    auth = HTTPBasicAuth(user_info.username, user_info.password)

    params = get_request_params(user_info)

    url = f'https://api.services-emobility.com/chargedataservice_v4'
    for pagenum in itertools.count():
        params['page'] = pagenum
        response = requests.get(url, auth=auth, params=params)
        response.raise_for_status()
        data = response.json()
        entries = data['content']
        emaid_euro_info = get_emaid_euro_info(entries)
        result.extend(emaid_euro_info)
        if len(entries) == 0:
            break
    return result


def get_request_params(user_info):
    strfmt = "%Y-%m-%dT%H:%M:%SZ"
    now = datetime.utcnow()
    six_month_ago = now - relativedelta(months=6)
    params = {
        'businessPartnerId': user_info.business_partner,
        'businessPartnerType': 'EMP',
        'lastUpdateFrom': six_month_ago.strftime(strfmt),
        'lastUpdateTo': now.strftime(strfmt),
        'details': 'true',
        'size': 100,
    }
    return params


def get_emaid_euro_info(cdrs):
    result = []
    for cdr in cdrs:
        entry = {
            'emaid': cdr['emaid'],
            'kwh': cdr['chargeData']['consumptionKwh'],
            'euros': sum(e['netAmount'] for e in cdr.get('pricingItems', []))
        }
        result.append(entry)
    return result


def get_sum_for_emaid(cdrs, val):
    result = {}
    for cdr in cdrs:
        emaid = cdr['emaid']
        value = cdr[val]
        result[emaid] = result.get(emaid, 0.0) + value
    return result


def prepare_date(cdrs):
    kwh_sum = get_sum_for_emaid(cdrs, 'kwh')
    euro_sum = get_sum_for_emaid(cdrs, 'euros')
    csv_rows = [{'emaid': e, 'kwh': kwh_sum[e], 'euros': euro_sum[e]} for e in kwh_sum.keys()]
    csv_rows = sorted(csv_rows, key=lambda v: v['kwh'])
    return csv_rows


def write_data(csv_rows):
    with open('revenue_per_emaid.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['emaid', 'kwh', 'euros'])
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)


def main():
    cdrs = get_data_from_chargedetailrecord_api(user_info=UserInformation)
    csv_rows = prepare_date(cdrs)
    write_data(csv_rows)


if __name__ == '__main__':
    main()
