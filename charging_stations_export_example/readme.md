# Getting Insight into your Charging Infrastructure using the API

eConnect offers detailed information about each of your charging stations via the [Masterdata API V1](https://econnect.services-emobility.com/apis/mdv1.2). However, even with all the things you can get out of our web portal, there may always be a scenario that eOperate does not yet support.


Let us assume that you have more than fifty charging station in operation and you want look how many charging stations of different hardware models are either operational, non-operational or still in planned and thus not fully activated. You have multiple ways to achieve this goal. You can either look at each individual station, make some notes, and do all calculations in your head.  Or you can use the station export functionality in eOperate and do some data anylysis with your favourte tool, for example Microsoft Excel.  This would work, but it would always require some manual steps. If you want to, say, generate the same report every week, doing things by hand quickly gets boring.

What if you could automate building your reports and write a script to gather and prepare all information you need? You can.

## Script Structure
Below, you see the structure of a script to request information about charging station from the API, do some data processing, and finally use [Pandas](https://pandas.pydata.org/) to calculate some simple statistics and write the results to an Excel file.


```python
def main():
    data = get_data_from_station_masterdata_api()
    cols_to_get = ['modelInfo', 'installDate', 'type', 'state']
    entries = extract_data(data, cols_to_get)

    df = pd.DataFrame(entries)
    counts, pivot = calculate_values(cols_to_get, df)

    write_excel(counts, df, pivot)
```

## Getting the Data

As a first step, we need to get information about our charging stations from the API. With the username, password and business partner number, we can request information about all our stations. The code below will cycle through all stations and collect them in a list.

```python
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
```

The information that the eConnect API provides for every charging station is quite extensive. To simplify  working with the resulting data, the code belows extracts a small subset of the overall data from each charging station entry.


## Transforming the Data
 

```python
def extract_data(entries, cols_to_get):
    result = []

    for inentry in entries:
        outentry = {col: inentry.get(col, "") for col in cols_to_get}
        result.append(outentry)
    return result
```




Finally, we use Pandas to do some simple calcualtion and counts on our charging station data. In the example below, among other things,  we count how many stations of each model we have and prepare a pivot table of charging station model and status.

```python
def calculate_values(cols_to_get, df):
    df['installDate'] = pd.to_datetime(df['installDate'], format='ISO8601', errors='coerce')
    counts = {col: df[col].value_counts().transpose().to_frame(name='count') for col in cols_to_get}
    pivot = df.pivot_table(index='modelInfo', columns=['state'], values='installDate', aggfunc='count').fillna(0)
    return counts, pivot
```



Finally, we write all our newly created statistics to an Excel file, with one statistic per worksheet.

```python
def write_excel(counts, df, pivot):
    with pd.ExcelWriter("export.xlsx") as writer:
        df.to_excel(writer, sheet_name='values')
        for name, count_df in counts.items():
            count_df.to_excel(writer, sheet_name=f"{name}_count")
        pivot.to_excel(writer, sheet_name='Status Pivot')
 ```

