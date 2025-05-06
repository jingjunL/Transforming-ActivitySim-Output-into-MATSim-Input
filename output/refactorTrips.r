# change data format, and external zuid holland pt trip to ptOutside (for teleportation in matsim)
#Its also not reasonable to use network routing for bike and ebike outside, change it to teleportation as well
# Set the working directory to the current directory of the script
setwd(dirname(rstudioapi::getSourceEditorContext()$path))

# Load necessary library for working with data (if needed)
library(dplyr)
library(sf)

# Read the CSV file into a data frame
data <- read.csv("maas10PercWithoutMultimodalAdaptation_RealPOI.csv", stringsAsFactors = FALSE)

# Modify the 'purpose' column based on your requirements
data <- data %>%
  mutate(purpose = case_when(
    purpose == "atwork" ~ "work",
    purpose %in% c("othmaint", "othdiscr") ~ "others",
    TRUE ~ purpose # Keep other values unchanged
  )) %>% 
  mutate(trip_mode = case_when(
    trip_mode == "cp" ~ "ride",
    TRUE ~ trip_mode # Keep other values unchanged
  ))

areas_landuse <- st_read("areas_landuse_2016.shp")
areas_landuse <- areas_landuse %>% 
  mutate(SUBZONE0 = SUBZONE0 + 1) %>% 
  select(SUBZONE0, GEBIEDEN) %>% 
  mutate(within_rotterdam = GEBIEDEN %in% c(1, 2))

data <- data %>% 
  left_join(
    areas_landuse %>% 
      rename(origin_zone = SUBZONE0, origin_within_rotterdam = within_rotterdam) %>% 
      st_set_geometry(NULL),
    by = c("origin" = "origin_zone")
  ) %>% 
  left_join(
    areas_landuse %>% 
      rename(destination_zone = SUBZONE0, destination_within_rotterdam = within_rotterdam)%>% 
      st_set_geometry(NULL),
    by = c("destination" = "destination_zone")
  )

# origin or destination not within MRDH and transport mode is pt, change it to mode ptOutside
data <- data %>%
  mutate(
    trip_mode = case_when(
      (!origin_within_rotterdam | !destination_within_rotterdam) & trip_mode == "pt" ~ "ptOutside",
      (!origin_within_rotterdam | !destination_within_rotterdam) & trip_mode == "bike" ~ "bikeOutside",
      (!origin_within_rotterdam | !destination_within_rotterdam) & trip_mode == "ebike" ~ "ebikeOutside",
      TRUE ~ trip_mode
    )
  )

modeShareAnalysis <- data %>% 
  filter(origin_within_rotterdam == TRUE & destination_within_rotterdam == TRUE)

modeDistanceAnalysis <- modeShareAnalysis %>%
  group_by(trip_mode) %>%
  summarise(
    total_distance = sum(travel_distance, na.rm = TRUE),  # Total distance for each mode
    average_distance = mean(travel_distance, na.rm = TRUE) # Average distance for each mode
  )

modeShareAnalysis <- modeShareAnalysis %>% 
  group_by(trip_mode) %>% 
  summarise(count = n()) 

# Remove unnecessary columns
data <- data %>%
  select(-GEBIEDEN.x, -origin_within_rotterdam, -GEBIEDEN.y, -destination_within_rotterdam)

#test <- data %>% 
#  filter(trip_mode == "ptOutside")

write.csv(data, file = "maas10PercWithoutMultimodalAdaptation_RealPOI_refactored.csv", row.names = FALSE, col.names = FALSE, quote = FALSE)

# Save the modified data back to a CSV file
#write.csv(data, "agentTrip10Perc_withRealPOI.csv", row.names = FALSE)
