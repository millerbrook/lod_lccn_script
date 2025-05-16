import pandas as pd
from get_target_persons import get_target_persons
from get_titles import process_persons_dataframe

if __name__ == "__main__":
    # Get filtered target persons DataFrame
    df_target = get_target_persons()
    # Process titles and export skeletal CSV
    process_persons_dataframe(df_target)