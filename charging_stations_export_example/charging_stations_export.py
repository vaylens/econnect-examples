import itertools

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth


def get_data_from_station_masterdata_api():
    username = 'USERNAME'
    password = 'PASSWORD'
    business_partner = 'BUSINESS_PARTNER'

    result = []
    url = f'https://api.services-emobility.com/masterdata/cpos/{business_partner}/chargingstations'

    auth = HTTPBasicAuth(username, password)
    for pagenum in itertools.count():
        response = requests.get(url, auth=auth, params=dict(page=pagenum, size=100))
        response.raise_for_status()
        data = response.json()
        entries = data['content']
        result.extend(entries)
        if len(entries) == 0:
            break
    return result


def extract_data(entries, cols_to_get):
    result = []

    for inentry in entries:
        outentry = {col: inentry.get(col, "") for col in cols_to_get}
        result.append(outentry)
    return result


def write_excel(counts, df, pivot):
    with pd.ExcelWriter("export.xlsx") as writer:
        df.to_excel(writer, sheet_name='values')
        for name, count_df in counts.items():
            count_df.to_excel(writer, sheet_name=f"{name}_count")
        pivot.to_excel(writer, sheet_name='Status Pivot')


def calculate_values(cols_to_get, df):
    df['installDate'] = pd.to_datetime(df['installDate'], format='ISO8601', errors='coerce')
    counts = {col: df[col].value_counts().transpose().to_frame(name='count') for col in cols_to_get}
    pivot = df.pivot_table(index='modelInfo', columns=['state'], values='installDate', aggfunc='count').fillna(0)
    return counts, pivot


def main():
    data = get_data_from_station_masterdata_api()
    cols_to_get = ['modelInfo', 'installDate', 'type', 'state']
    entries = extract_data(data, cols_to_get)

    df = pd.DataFrame(entries)
    counts, pivot = calculate_values(cols_to_get, df)

    write_excel(counts, df, pivot)


if __name__ == '__main__':
    main()
