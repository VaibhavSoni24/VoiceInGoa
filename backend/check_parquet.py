import pandas as pd
df = pd.read_parquet("data/hinval.parquet", engine="fastparquet")
print(df.columns.tolist())
print(df.head())
