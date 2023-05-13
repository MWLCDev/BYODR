import os
import zipfile
import glob
import pandas as pd
from gpx_converter import Converter
import glob
import folium
import pandas as pd
import pathlib


# To store the name of the day the session took place in it.
SESSION_DATE = ""

# The Resultant file with all the rows from a training session made in a day
MERGED_CSV_FILES = f"resultant_{SESSION_DATE}.csv"

GPX_FILE = f"{SESSION_DATE}.gpx"

# Main list to have all the .CSV files as their own list in the training session folder
L = []

# Filtered columns that will be used in the resultant .CSV file.
KEEP_COL = ["x_coord", "y_coord", "vehicle_conf"]

TRAINING_SESSION_LOCATION = "D:/Job/Byodr/__myStuff/routeAccu/trainingSession/"

# Get all the compressed files in a folder
ZIP_FILES_LOCATION = glob.glob(f"{TRAINING_SESSION_LOCATION}**/*.zip", recursive=True)

# Store the folder of sessions
CSV_FILES_LOCATION = []

TRAINING_SESSIONS_DATE = []


class FindCSV:
    """Find the .ZIP compressed folder and get the .CSVs from it
    then move them to a folder with the name being the date of training session "2023Apr06"
    """

    def store_sessions_folder(self):
        global MERGED_CSV_FILES, GPX_FILE
        """store in "CSV_FILES_LOCATION" the location for the training sessions 
        where the .CSV files are moved from the compressed file of training sessions
        """
        if len(CSV_FILES_LOCATION) == 0:
            CSV_FILES_LOCATION.append(
                "{0}\\{1}".format(pathlib.Path(__file__).parent.resolve(), SESSION_DATE)
            )
        elif not SESSION_DATE in CSV_FILES_LOCATION[-1]:
            CSV_FILES_LOCATION.append(
                "{0}\\{1}".format(pathlib.Path(__file__).parent.resolve(), SESSION_DATE)
            )
        MERGED_CSV_FILES = f"resultant_{SESSION_DATE}.csv"
        GPX_FILE = f"{SESSION_DATE}.gpx"

    def extract_files_by_extension(self):
        global SESSION_DATE
        for file in ZIP_FILES_LOCATION:
            # To get the date of session only, from the CSV file
            SESSION_DATE = os.path.basename(file)[:9]

            self.create_sessions_folder()

            self.store_sessions_folder()

            with zipfile.ZipFile(file, "r") as zip_ref:
                # Get all the files in the chosen compressed file
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith(".csv"):
                        extracted_path = zip_ref.extract(file_info, path=SESSION_DATE)
                        new_file_path = os.path.join(SESSION_DATE, file_info.filename)
                        os.rename(extracted_path, new_file_path)

    def create_sessions_folder(self):
        """Create a folder with the date of the sessions"""
        if not os.path.exists(SESSION_DATE):
            os.makedirs(SESSION_DATE)


class ProcessCSVtoGPX:
    """Make one (cleaned) .CSV file that will have all the data in it."""

    def __init__(self):
        self.df = ""

    def create_resultant_CSV(self):
        """Create a main .CSV file that will have data from all the .CSV that are founded in a training session."""

        # keep only the coordinates columns in them
        for folder in CSV_FILES_LOCATION:
            L.clear()

            CSV_files = glob.glob(f"{folder}\\*.csv")
            for file in CSV_files:
                # Read every file in the folder
                read_file = pd.read_csv(file)
                new_file = read_file[KEEP_COL]
                L.append(new_file)

            self.df = pd.concat(L, ignore_index=True)
            self.clean_dataframe()
            self.convert_to_CSV()
            self.convert_to_GPX()

    def clean_dataframe(self):
        """Remove duplication from the table."""
        old_count = self.df.shape[0]
        self.df = self.df.drop_duplicates()
        print(
            f"Removed the duplicates in the data from {old_count} to {self.df.shape[0]}"
        )

    def convert_to_CSV(self):
        self.df.to_csv(MERGED_CSV_FILES, index=False)
        print(f"CSV file saved as {MERGED_CSV_FILES}")

    def convert_to_GPX(self):
        Converter(input_file=MERGED_CSV_FILES).csv_to_gpx(
            lats_colname=KEEP_COL[0],
            longs_colname=KEEP_COL[1],
            output_file=GPX_FILE,
        )
        print(f"GPX file saved as {GPX_FILE}")

    def run_all(self):
        """Will run "create_resultant_CSV()", "clean_dataframe()", "convert_to_CSV()" and "convert_to_GPX()" """
        self.create_resultant_CSV()
        self.clean_dataframe()
        self.convert_to_CSV()
        self.convert_to_GPX()


class PlotMap:
    """Create a map with the points from training sessions in it."""

    def __init__(self):
        self.dataframe = pd.read_csv(MERGED_CSV_FILES)
        self.SESSION_DATE = SESSION_DATE
        self.latitude = self.dataframe[KEEP_COL[1]]
        self.longitude = self.dataframe[KEEP_COL[0]]

    def create_marker(self, row, map_obj):
        """Add markers on top of the points that are plotted on the map

        Args:
            row (dataframe): A dataframe that is passed as row with x and y coordinates in it
        """
        folium.Marker(location=[row["x_coord"], row["y_coord"]]).add_to(map_obj)

    def plot_map(self):
        # Create a map object
        map_obj = folium.Map(
            location=[self.longitude.mean(), self.latitude.mean()],
            zoom_start=12,
            max_zoom=22,
        )

        # Apply the create_marker function to each 10th row
        self.dataframe.iloc[::40].apply(self.create_marker, axis=1, args=(map_obj,))

        # Create a 2D list from the two columns
        coordinates = [
            [column1, column2]
            for column1, column2 in zip(self.longitude.tolist(), self.latitude.tolist())
        ]

        # Draw line between the points
        folium.PolyLine(
            locations=coordinates, color="blue", weight=2.5, opacity=1
        ).add_to(map_obj)

        # Save the map to an HTML file
        map_obj.save(f"{self.SESSION_DATE}.html")
        print(f"created the training route of session {self.SESSION_DATE}")


FindCSV().extract_files_by_extension()

ProcessCSVtoGPX().create_resultant_CSV()

PlotMap().plot_map()
