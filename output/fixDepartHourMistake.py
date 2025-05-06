#Step 1.5.B: for unrealistic plan, fix the plan

# We have 3 primary mistakes from the @checkSchedule.py, primarily due to the bug
# the origin ==  destination and last activity == home (2 and 3 mistakes) can only be fixed manually, but the depart time should be fixed with script (otherwise too many)
from logging import fatal

import pandas as pd

# Load the dataset
file_path = r'C:\Users\jingjunli\OneDrive - Delft University of Technology\Documents\matsim\activitySimData\output\Maas\processedMaaS10PercTrip.csv'
fixed_path = r'C:\Users\jingjunli\OneDrive - Delft University of Technology\Documents\matsim\activitySimData\output\MaaS\maas10PercDepartFixed.csv'
data = pd.read_csv(file_path)

print("---------------------------")

def fix_depart_time(df):
    total_persons = df['person_id'].nunique()
    print(f"Total unique persons to process: {total_persons}")

    for person_id, group in df.groupby('person_id'):
        previous_depart = None

        for idx in group.index:
            current_depart = df.loc[idx, 'depart']

            if previous_depart is not None and current_depart < previous_depart:
                df.loc[idx, 'depart'] = previous_depart
            else:
                previous_depart = current_depart


    return df

fix_depart_time(data).to_csv(fixed_path, index=False)