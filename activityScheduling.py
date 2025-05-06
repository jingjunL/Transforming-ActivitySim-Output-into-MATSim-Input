import pandas as pd
import sys
import os

#step 1: summarise the location chainning of activitySim
#print output into a log file
#log_file_path = os.path.join("output", "output.log")
#sys.stdout = open(log_file_path, 'w')

# read ActivitySim simpled csv
file_path = "./maasTrip10Perc.csv"
#file_path = "./bugExample.csv"

output_file_path = "./output/MaaS/processedMaaS10PercTrip.csv"
#output_file_path = "./output/fullTrips/MRDHFullTrips.csv"
#output_file_path = "./output/bugExample.csv"

df = pd.read_csv(file_path)

# sort first based on person_id and depart time
df_sorted = df.sort_values(by=['person_id', 'depart'])

def adjust_sequence_for_user(df):
    trips = df.copy()
    ordered_trips = []

    # sort by the departure time
    trips_for_sort = trips.sort_values(by='depart')

    #find the home Address of the agent and its first trip
    home_trip = trips_for_sort[trips_for_sort['purpose'] == "Home"].iloc[0]
    home_address = home_trip['destination']

    #process for situation where two tours depart at home at the same depart time
    first_trip_candidates = trips_for_sort[(trips_for_sort['origin'] == home_address) & (trips_for_sort['depart'] == trips_for_sort['depart'].min())]
    if len(first_trip_candidates) ==1:
        first_trip = first_trip_candidates.iloc[0]
        ordered_trips.append(first_trip)
        trips_for_sort = trips_for_sort.drop(first_trip.name)
    else:
        for _, candidate in first_trip_candidates.iterrows():
            candidate_tour_trips = trips_for_sort[trips_for_sort['tour_id'] == candidate['tour_id']]
            if candidate_tour_trips['depart'].max() == candidate['depart']:
                first_trip = candidate
                ordered_trips.append(first_trip)
                trips_for_sort = trips_for_sort.drop(first_trip.name)
                break
        else:
            first_trip = first_trip_candidates.loc[first_trip_candidates['trip_id'].idxmin()]
            ordered_trips.append(first_trip)
            trips_for_sort = trips_for_sort.drop(first_trip.name)
  #          print(f"Bug found: cannot find first trip, person_id is {first_trip_candidates.iloc[0]['person_id']}")
  #          return pd.DataFrame()

    #find the first trip, so the loop can start finding the next trip
    current_trip = first_trip

    while not trips_for_sort.empty:
        # the destination of the next trip should be the origin of the incoming trip
        next_trip_candidates = trips_for_sort[trips_for_sort['origin'] == current_trip['destination']]

        if next_trip_candidates.empty:
            # if we cannot find the next trip
            if len(trips_for_sort) == 1:  #we are now in the last trip
                ordered_trips.append(trips_for_sort.iloc[0])  # add it to the last trip
                trips_for_sort = trips_for_sort.drop(trips_for_sort.iloc[0].name)
                break
            else:
                # if there are trips still not sorted, it is a bug and we should report
                print(f"Bug found: cannot find the coming trips, person_id is {first_trip['person_id']}")
                return pd.DataFrame()

        # find the respective next trip among candidates

        next_trip_candidates = next_trip_candidates.sort_values(by='depart')

        min_depart_candidates = next_trip_candidates[next_trip_candidates['depart'] == next_trip_candidates['depart'].min()]
        if len(next_trip_candidates) == 1:
            current_trip = next_trip_candidates.iloc[0]
            ordered_trips.append(current_trip)
            trips_for_sort = trips_for_sort.drop(current_trip.name)
        elif len(min_depart_candidates) > 1:
            #person_id == 511 may cause problem that have multiple candidates with same depart (so need to go back to the tour to exclude tours that depart is higher than current depart)
            for _, candidate in min_depart_candidates.iterrows():
                candidate_tour_trips = trips_for_sort[trips_for_sort['tour_id'] == candidate['tour_id']]
                if candidate_tour_trips['depart'].max() == candidate['depart']:
                    current_trip = candidate
                    ordered_trips.append(current_trip)
                    trips_for_sort = trips_for_sort.drop(current_trip.name)
                    break
            else:
                # person_id == 49094, for trip == 16093025 & 16093027, all belong to the same tour, but tour depart max (14) all does not equal 11. As a result, without this else, it will go into dead loop
                # print("Warning: cannot find candidate within all next_trip_candidates, will use the trip with minimum depart and trip_id")
                current_trip = min_depart_candidates.loc[min_depart_candidates['trip_id'].idxmin()]
                ordered_trips.append(current_trip)
                trips_for_sort = trips_for_sort.drop(current_trip.name)
        else:
            current_trip = min_depart_candidates.iloc[0]
            ordered_trips.append(current_trip)
            trips_for_sort = trips_for_sort.drop(current_trip.name)

    return pd.DataFrame(ordered_trips)

sorted_df = pd.DataFrame()

total_users = df_sorted['person_id'].nunique()
print(f"Overall {total_users} Users...")

for idx, (person_id, user_data) in enumerate(df_sorted.groupby('person_id'), start=1):
    print(f"Processing {idx}/{total_users} (person_id={person_id})...")
    user_sorted = adjust_sequence_for_user(user_data)
    if not user_sorted.empty:
        sorted_df = pd.concat([sorted_df, user_sorted])


sorted_df.reset_index(drop=True, inplace=True)
sorted_df.to_csv(output_file_path, index=False)

print(f"Output in the path: {output_file_path}")