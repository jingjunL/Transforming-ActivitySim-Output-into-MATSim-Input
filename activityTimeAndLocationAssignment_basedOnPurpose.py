#this script use the real world POI based on the purpose and region of the trip (so better than another with similiar name_
#step 2: assigning activity time and location for each trip
#Next step: move to the R file (refactorTrips.r) for refactor trip details

#Outcome: 35733/812339 trips cannot find POI within TAZ and do random assignment,
# I would say this is acceptable
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import random
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("assignment_log.txt", mode='w'),
        logging.StreamHandler()
    ]
)


chained_file_location = "./output/MaaS/maas10PercDepartFixed.csv"
#chained_file_location = "./output/agentTripToyOutput1Perc.csv"
#chained_file_location = "./output/bugExample.csv"

shape_file_location = "./areas_landuse_2016.shp"
output_location = "./output/MaaS/maas10PercWithoutMultimodalAdaptation_RealPOI.csv"
#output_location = "./output/agentTripToyWithMinute1perc.csv"

df = pd.read_csv(chained_file_location)

df = df[['trip_id', 'person_id', 'household_id', 'tour_id',
        'purpose', 'origin', 'destination', 'depart',
        'trip_mode', 'travel_distance', 'travel_time']]

df.rename(columns={'depart': 'depart_hour_original'}, inplace=True)

#print(df.head())

df['travel_time'] = df['travel_time'].round(0)

#Assign detailed minute for each trip
np.random.seed(123)

df['exact_depart_hour'] = np.nan
df['exact_depart_minute'] = np.nan
df['previous_activity_duration'] = np.nan
df['next_activity_duration'] = np.nan

total_persons = df['person_id'].nunique()

#Trip time assignment
print("Starting trip time assignment...")

count = 1

for person_id, person_group in df.groupby('person_id'):

        print(f"Assigning time minute person_id: {person_id} ({count}/{total_persons})")

        for idx, row in person_group.iterrows():

                # first trip assign a random minute
                if idx == person_group.index[0]:
                        first_trip_depart_hour_original = row['depart_hour_original']

                        df.loc[idx, 'exact_depart_hour'] = row['depart_hour_original']
                        df.loc[idx, 'exact_depart_minute'] = np.random.randint(0, 60)
                        df.loc[idx, 'previous_activity_duration'] = df.loc[idx, 'exact_depart_hour'] * 60 + df.loc[idx, 'exact_depart_minute']

                        arrival_time_previous_trip = df.loc[idx, 'previous_activity_duration'] + df.loc[idx, 'travel_time']

                        travel_time_between_activities = df.loc[idx, 'travel_time']

                        trip_indices = person_group.index
                        current_trip_position = trip_indices.get_loc(idx)

                        #As in ActivitySim, people all start and end at Home, which means there should be at least 2 trips for each individual

                        next_trip_idx = trip_indices[current_trip_position + 1]
                        next_trip_depart_hour_original = df.loc[next_trip_idx, 'depart_hour_original']

                        estimated_duration = (next_trip_depart_hour_original - first_trip_depart_hour_original) * 60 - travel_time_between_activities

                        if estimated_duration <= 0:
                                # In case very short activity duration < 0, assign a duration between 1 minute and 15 minutes
                                next_activity_duration = np.random.randint(1, 16)
                        else:
                                # In case estimated duration > 0, find a random duration minute within 15 minutes interval
                                lower_bound = (estimated_duration // 15) * 15 + 1
                                upper_bound = (estimated_duration // 15 + 1) * 15
                                next_activity_duration = np.random.randint(lower_bound, upper_bound)

                        df.loc[idx, 'next_activity_duration'] = next_activity_duration

                else:
                        trip_indices = person_group.index
                        current_position = person_group.index.get_loc(idx)
                        previous_trip_idx = person_group.index[current_position - 1]

                        # Extract and print the trip_id of the previous trip
                        previous_depart_hour = df.loc[previous_trip_idx, 'exact_depart_hour']
                        previous_depart_minute = df.loc[previous_trip_idx, 'exact_depart_minute']
                        previous_travel_time = df.loc[previous_trip_idx, 'travel_time']
                        previous_original_depart_hour = df.loc[previous_trip_idx, 'depart_hour_original']
                        previous_trip_next_activity_duration = df.loc[previous_trip_idx, 'next_activity_duration']

                        current_trip_depart_time = (previous_depart_hour * 60 + previous_depart_minute + previous_travel_time + previous_trip_next_activity_duration)

                        df.loc[idx, 'exact_depart_hour'] = current_trip_depart_time // 60
                        df.loc[idx, 'exact_depart_minute'] = current_trip_depart_time % 60
                        df.loc[idx, 'previous_activity_duration'] = previous_trip_next_activity_duration

                        current_trip_travel_time = df.loc[idx, 'travel_time']

                        # Assign duration for the next activity
                        if current_position < len(trip_indices) - 1:
                                # There is a next trip
                                next_trip_idx = trip_indices[current_position + 1]
                                current_trip_depart_hour_original = df.loc[idx, 'depart_hour_original']
                                next_trip_depart_hour_original = df.loc[next_trip_idx, 'depart_hour_original']

                                estimated_duration = (next_trip_depart_hour_original - current_trip_depart_hour_original) * 60 - current_trip_travel_time
                                if estimated_duration <= 0:
                                        next_activity_duration = np.random.randint(1, 16)
                                else:
                                        lower_bound = (estimated_duration // 15) * 15 + 1
                                        upper_bound = (estimated_duration // 15 + 1) * 15
                                        next_activity_duration = np.random.randint(lower_bound, upper_bound)
                        else:
                                #this is already the last trip of person
                                current_trip_arrival_time = current_trip_depart_time + current_trip_travel_time
                                next_activity_duration = (24 * 60) - current_trip_arrival_time

                                if next_activity_duration <= 0:
                                        # Already exceed 24 hours, so just set as 10 minutes next activity
                                        next_activity_duration = 10

                        df.loc[idx, 'next_activity_duration'] = next_activity_duration

        count += 1

#Trip origin and destination coordinate assignment

print("Starting coordinate assignment with trip purposes and the area weights of POI...")

# read the shapefile POI based on trip purpose and form a dictionary

purposes = [
    "social", "othdiscr", "shopping",
    "othmaint", "school", "eatout",
    "escort", "work", "univ", "atwork",
    "home"
]

poi_folder = "./output/POI/mappedPurpose"

poi_dict = {}

for purpose in purposes:
    shp_path = os.path.join(poi_folder, f"{purpose}.shp")
    print(f"Reading POI shapefile for {purpose}: {shp_path}")
    gdf_poi = gpd.read_file(shp_path)

    # read SUBZONE information from shp and +1 (as the information is from landuse_2016.shp)
    gdf_poi = gdf_poi.rename(columns={'SUBZONE0': 'subzone'})

    # Very tiny situation there would be NA, just drop it
    gdf_poi = gdf_poi.dropna(subset=['subzone'])
    gdf_poi['subzone']= gdf_poi['subzone'].astype(int) + 1

    for subz, group in gdf_poi.groupby('subzone'):
        # store the geo-info and the area into a dictionary, with the key as "subzone, purpose"
        key = (purpose, int(subz))
        poi_dict[key] = group[['geometry', 'oppervlakt']].copy()

gdf = gpd.read_file(shape_file_location)
gdf['SUBZONE0'] += 1
gdf = gdf.rename(columns={'SUBZONE0': 'subzone'})

# change all purposes in activitySim to lower case (Work, work... different)
df['purpose'] = df['purpose'].str.lower()

df['origin_coordinate_x'] = np.nan
df['origin_coordinate_y'] = np.nan
df['destination_coordinate_x'] = np.nan
df['destination_coordinate_y'] = np.nan

subzone_mapping = dict(zip(gdf['subzone'], gdf['geometry']))

#write a random function in case cannot find the respective POI in the subzone (so that assign a random coordinate as we did before)
def generate_random_point_in_polygon(polygon):
        minx, miny, maxx, maxy = polygon.bounds
        while True:
                random_point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
                if polygon.contains(random_point):
                        return random_point

count = 1

for person_id, person_group in df.groupby('person_id'):

        print(f"Assigning coordinates for person_id: {person_id} ({count}/{total_persons})")
        previous_destination_x = None
        previous_destination_y = None

        for idx, row in person_group.iterrows():
                current_purpose = row['purpose']
                if idx == person_group.index[0]:
                        #first trip of person, origin and destination can be assigned randomly'
                        origin_subzone = row['origin']
                        poi_key_home = ("home", origin_subzone)
                        poi_df_home = poi_dict.get(poi_key_home, None)

                        if poi_df_home is not None:
                                home_population = poi_df_home['geometry'].tolist()
                                home_weights = poi_df_home['oppervlakt'].tolist()

                                chosen_point = random.choices(population=home_population, weights=home_weights, k=1)[0]
                                df.loc[idx, 'origin_coordinate_x'] = chosen_point.x
                                df.loc[idx, 'origin_coordinate_y'] = chosen_point.y

                                # print("Found one! - Home")

                        else:
                                if origin_subzone in subzone_mapping:
                                        logging.warn(
                                                f"No Home POI found for subzone={origin_subzone}, personID={person_id}, falling back to polygon random point.")
                                        origin_polygon = subzone_mapping[origin_subzone]
                                        random_point = generate_random_point_in_polygon(origin_polygon)
                                        df.loc[idx, 'origin_coordinate_x'] = random_point.x
                                        df.loc[idx, 'origin_coordinate_y'] = random_point.y

                        destination_subzone = row['destination']

                        poi_key_destination = (current_purpose, destination_subzone)
                        poi_df_destination = poi_dict.get(poi_key_destination, None)

                        if poi_df_destination is not None:
                                population = poi_df_destination['geometry'].tolist()
                                weights = poi_df_destination['oppervlakt'].tolist()
                                chosen_point = random.choices(population=population, weights=weights, k=1)[0]
                                df.loc[idx, 'destination_coordinate_x'] = chosen_point.x
                                df.loc[idx, 'destination_coordinate_y'] = chosen_point.y

                                # print("Found one! - Destination")
                        else:
                                if destination_subzone in subzone_mapping:
                                        logging.warning(
                                                f"No POI found for activityType={current_purpose}, personID={person_id}, subzone={destination_subzone}. Falling back to polygon random point."
                                        )
                                        destination_polygon = subzone_mapping[destination_subzone]
                                        random_point = generate_random_point_in_polygon(destination_polygon)
                                        df.loc[idx, 'destination_coordinate_x'] = random_point.x
                                        df.loc[idx, 'destination_coordinate_y'] = random_point.y

                        previous_destination_x = df.loc[idx, 'destination_coordinate_x']
                        previous_destination_y = df.loc[idx, 'destination_coordinate_y']

                else:
                        df.loc[idx, 'origin_coordinate_x'] = previous_destination_x
                        df.loc[idx, 'origin_coordinate_y'] = previous_destination_y
                        destination_subzone = row['destination']

                        poi_key_dest = (current_purpose, destination_subzone)
                        poi_df_dest = poi_dict.get(poi_key_dest, None)

                        if poi_df_dest is not None:
                                population = poi_df_dest['geometry'].tolist()
                                weights = poi_df_dest['oppervlakt'].tolist()
                                chosen_point = random.choices(population=population, weights=weights, k=1)[0]
                                df.loc[idx, 'destination_coordinate_x'] = chosen_point.x
                                df.loc[idx, 'destination_coordinate_y'] = chosen_point.y

                                # print("Found one! - Destination")

                        else:

                                logging.warning(
                                        f"No POI found for activityType={current_purpose}, personID={person_id}, subzone={destination_subzone}. Falling back to polygon random point."
                                )

                                if destination_subzone in subzone_mapping:
                                        destination_polygon = subzone_mapping[destination_subzone]
                                        random_point = generate_random_point_in_polygon(destination_polygon)
                                        df.loc[idx, 'destination_coordinate_x'] = random_point.x
                                        df.loc[idx, 'destination_coordinate_y'] = random_point.y

                                previous_destination_x = df.loc[idx, 'destination_coordinate_x']
                                previous_destination_y = df.loc[idx, 'destination_coordinate_y']

        count += 1

#pd.set_option('display.max_columns', None)
#print(pd.concat([df.head(10), df.tail(5)]))

df.to_csv(output_location, index=False)




