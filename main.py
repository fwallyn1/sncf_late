import requests
import os
from datetime import datetime
from datetime import timedelta
import pandas as pd
import click 
import pandas_gbq
from google.oauth2 import service_account
import json

STOPS = {
    "Rennes": "87471003"
}

service_account_info = os.getenv("SERVICE_ACCOUNT_INFO")

@click.command()
@click.option("--token")
@click.option("--date",type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--ville")

def run(token, date, ville):
    header = {"Authorization" : token}
    start_date = date.strftime('%Y%m%dT%H%M%S')
    end_date = (date+timedelta(days=1)).strftime('%Y%m%dT%H%M%S')
    url = f"https://api.sncf.com/v1/coverage/sncf/stop_areas/stop_area%3ASNCF%3A{STOPS[ville]}/physical_modes/physical_mode%3ALongDistanceTrain/arrivals?from_datetime={start_date}&until_datetime={end_date}&count=1000"

    response = requests.get(url=url,headers=header)
    data = response.json()
    df = pd.DataFrame(data["arrivals"])

    outputs=[]
    for col in df[["display_informations","stop_date_time"]].columns:
        outputs.append(pd.json_normalize(df[col]))
    df_final = pd.concat(outputs,axis=1)
    for col in ["arrival_date_time","departure_date_time","base_arrival_date_time","base_departure_date_time"]:
        df_final[col] = pd.to_datetime(df_final[col], format='%Y%m%dT%H%M%S')
    df_final["delay"] = df_final["arrival_date_time"] - df_final["base_arrival_date_time"]
    df_final["delay"] = df_final["delay"].apply(lambda x : x.total_seconds())
    df_final["is_delayed"] = df_final["delay"] != 0
    df_final = df_final[["direction", "network","name","headsign","label","arrival_date_time","departure_date_time","base_arrival_date_time","base_departure_date_time","delay","is_delayed"]]
    print(df_final)
    credentials = service_account.Credentials.from_service_account_info(json.loads(service_account_info))
    df_final.to_gbq(destination_table=f'francois_sncf.sncf_train_table', project_id='ensai-2023-373710',credentials=credentials,location="europe-west9",if_exists="replace")

if __name__ == '__main__':
    run()