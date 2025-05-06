# Open-source Code for Transforming the Output of ActivitySim Trip into MATSim Plan
Python Script for transforming the output of ActivitySim (https://github.com/ActivitySim/activitysim) into the synthetic travel demand of MATSim (https://matsim.org/)

Relevant Paper for the script (would be happy if you can cite it in the case that you find this repository useful)

An Activity-and Agent-based Co-Simulation Framework for the Metropolitan Rotterdam The Hague Region (https://www.sciencedirect.com/science/article/pii/S1877050925008609)

## How does this work?

ActivitySim is an open-source activity-based simulation software using discrete choice theory, which could provide excellent synthetic travel demand for the travel patterns of each individual within the study area during a typical day.

However, the output of ActivitySim (trip.csv) is based on Traffic Analysis Zone and hourly level,
Whereas in turn, cannot provide mesoscopic traffic assignment simulation.

MATSim is an agent-based mesoscopic traffic simulation software, whereas its input needs coordinate-second level of individual activity patterns within the study region, which is usually hard to obtain directly in real-world practice.

In addition, the "replanning" module of MATSim has only limited choice dimensions (reroute, departure time mutation and shift mode choice), which is rather limited.

As a result, we see huge potential for combining two open-source software for more comprehensive assessments of mobility interventions on the mesoscopic level.

## Step for using this repository

### Step 1: activityScheduling.py

The output of Activity trip does not fully follow the time order (as it is an activity-based software), we reorder the trip sequence for better reflection of agent daily activity pattern.

### Step 2: output/checkSchedule.py & fixDepartHourMistake.py

Check the plausibility of the scheduling outcome from Step 1, and if there are mistake in the departure time of each activity, we automatically fix them.

### Step 3: activityTimeAndLocationAssignment_basedOnPurpose.py

Based on real-world POI data, trip purpose and destination, for each trip within the ActivitySim output, we assign a coordinate and detailed second level time for each trip.

### Step 4: refactor details trip modes in the output csv (we use R for this as it is more straightforward)

Just some minor changes, for instance, change the mode "cp" from ActivitySim into "ride" for MATSim.

After these steps, you will have a csv containing every information that needed for MATSim plan.xml input :)

We also have another script for directly transforming the csv into MATSim plan, where you could find it here: https://github.com/jingjunL/MATSim-MRDH-XCARCITY
