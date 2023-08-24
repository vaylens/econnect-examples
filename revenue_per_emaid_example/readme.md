

# Using the Charge Data Record API to find the most active EMAIDs

For this example, we will look at using the [Charge Data Record (CDR) API V4](https://econnect.services-emobility.com/apis/cdrv4.2) 
to build a table with the kwh charged and the revenue generated for each EMAID. The example will be in Python, but the usage of 
the API does not differ between programming languages.

In the following we will look at the whole script and explain each individual step. You can find the whole program in the 
`revenue_per_emaid.py` file. To execute the script yourself, you need access to the CDR API and to the business partner for which you wand
to request the data. You will also need a Python 3.x installation with the `request` and `python-dateutil` packages

## Script Structure und User Information

In order to access the API, you need to know your username and password. You also need the business partner number for the 
EMP that you are interested in.

The high-level structure of the script is simple: We first access the CDR API to get information for all charging session that 
are potentially of interest. Then, we do some data transformation to bring the data into the format that we are interested in. 
Finally, we write the data to a file.

```python

class UserInformation:
    username = 'YOUR_USERNAME'
    password = 'YOUR_PASSWORD'
    business_partner = 'YOUR_BUSINESSPARTNER'
...
def main():
    cdrs = get_data_from_chargedetailrecord_api(user_info=UserInformation)
    csv_rows = prepare_date(cdrs)
    write_data(csv_rows)
```

## Requesting the Data

Use the `requests` package to make the HTTP request to the API more comfortable. We use `HTTPBasicAuth` to perform a HTTP
Basic Authentication against the API. 

Then, we gather all parameters that the API requires for an request into the `params` variable. You will find details
on these variables below. We request all available CDRs for the business partner in blocks of 100 and gather them into a list.
To save some memory, and also to make debugging easier, we use the `get_emaid_euro_info` function to select only the relevant 
information for our use case, the emaid, the kwh charged and the net Euros to be billed to the customer from each returned cdr.

Any error during a HTTP request lead to a Python Exception and the termination of the script.

```python
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
```

The CDR API requires a number of parameters to work. The API provides information on CDRs for the last six months.

```python
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
```

We are only interested into three items from each of the CDR objects we receive, so we create a new, small Python objects with
just the required information. Since the `pricingItems` are optional in the CDR, we will return 0 Euros for CDRs without cost 
information.

```python
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
```

## Preparing the Data

We are interested in the total kwh charged and the total Euros of revenue per EMAID, so we iterate over all CDRs and aggregate
the kwh and euro values for each EMAID. We also sort the resulting list, from the lowest Euro number per EMAID to the 
highest.

```python
def prepare_date(cdrs):
    kwh_sum = get_sum_for_emaid(cdrs, 'kwh')
    euro_sum = get_sum_for_emaid(cdrs, 'euros')
    csv_rows = [{'emaid': e, 'kwh': kwh_sum[e], 'euros': euro_sum[e]} for e in kwh_sum.keys()]
    csv_rows = sorted(csv_rows, key=lambda v: v['kwh'])
    return csv_rows
```

The function `get_sum_for_emaid` is a simple helper to aggregate values for the same EAMID. We use it for kwh as well
as Euros.

```python
def get_sum_for_emaid(cdrs, val):
    result = {}
    for cdr in cdrs:
        emaid = cdr['emaid']
        value = cdr[val]
        result[emaid] = result.get(emaid, 0.0) + value
    return result
```

## Writing the Data 

There are many possible ways to store and/or present the information produced by the script. To keep things simple, 
we use the `csv` package that comes with Python to export and store the Data in an CSV File

```python
def write_data(csv_rows):
    with open('revenue_per_emaid.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['emaid', 'kwh', 'euros'])
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
```

And that's it 😀.

