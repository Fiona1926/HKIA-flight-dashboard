import pandas as pd

df_1= pd.read_csv("/Users/fionaleong/cargo_flight_monitor/past_data/current_flights_2026-07-27.csv")
df_filtered_1=df_1[df_1['airline']=='CPA']
dest_list=df_filtered_1['destination'].tolist()
df_filtered_2=df_1[(df_1['airline']!='CPA') & (df_1['destination'].isin(dest_list))]
print(df_filtered_1)
print(df_filtered_2)
