import os
import zipfile
import glob
import pandas as pd
from gpx_converter import Converter
import glob
import folium
import pandas as pd
import pathlib
import shutil


# Filtered columns that will be used in the resultant .CSV file.
KEEP_COL = ["x_coord", "y_coord", "vehicle_conf"]

TRAINING_SESSION_LOCATION = "D:/Job/Byodr/__myStuff/routeAccu/trainingSession/"

# Get all the compressed files in a folder
ZIP_FILES_LOCATION = glob.glob(f"{TRAINING_SESSION_LOCATION}**/*.zip", recursive=True)

# To store the name of the day the session took place in it.
SESSION_DATE = []

# List for the location (in absolute path) of the resultant .CSVs made in a day.
MERGED_CSV_FILES_LOCATION = []

# Store the folder of sessions
CSV_FILES_LOCATION = []

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def return_absolute_path(additional_path):
    return CURRENT_DIRECTORY + "/" + additional_path


class FindCSV:
    """Find the .ZIP compressed folder and get the .CSVs from it
    then move them to a folder with the name being the date of training session "2023Apr06"
    """

    def extract_files_by_extension(self):
        global SESSION_DATE
        SESSION_DATE.clear()
        for file in ZIP_FILES_LOCATION:
            filename_only = os.path.basename(file)
            date_from_filename_only = filename_only.split("T")[0]
            # To get the date of session only, from the CSV file
            if len(SESSION_DATE) == 0:
                SESSION_DATE.append(date_from_filename_only)
            elif not date_from_filename_only in SESSION_DATE[-1]:
                SESSION_DATE.append(date_from_filename_only)

            self.create_sessions_folder(SESSION_DATE[-1])

            self.store_sessions_folder()

            with zipfile.ZipFile(file, "r") as zip_ref:
                # Get all the files in the chosen compressed file
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith(".csv"):
                        extracted_path = zip_ref.extract(
                            file_info,
                            path=os.path.join(CURRENT_DIRECTORY, SESSION_DATE[-1]),
                        )

    def store_sessions_folder(self):
        global SESSION_DATE
        """store in "CSV_FILES_LOCATION" the location for the training sessions 
        where the .CSV files are moved from the compressed file of training sessions
        """
        if len(CSV_FILES_LOCATION) == 0:
            CSV_FILES_LOCATION.append(
                "{0}\\{1}".format(
                    pathlib.Path(__file__).parent.resolve(), SESSION_DATE[-1]
                )
            )
        elif not SESSION_DATE[-1] in CSV_FILES_LOCATION[-1]:
            CSV_FILES_LOCATION.append(
                "{0}\\{1}".format(
                    pathlib.Path(__file__).parent.resolve(), SESSION_DATE[-1]
                )
            )

    def create_sessions_folder(self, session_data):
        session_directory = os.path.join(CURRENT_DIRECTORY, session_data)
        """Create a folder with the date of the sessions"""
        if not os.path.exists(session_directory):
            os.makedirs(session_directory)


class ProcessCSVtoGPX:
    """Make one (cleaned) .CSV file that will have all the data in it."""

    def __init__(self):
        self.df = ""
        self.merged_csv_files = ""
        # Main list to have all the .CSV files as their own list in the training session folder
        self.dataframe_data = []

    def create_resultant_CSV(self):
        """Create a main .CSV file that will have data from all the .CSV that are founded in a training session."""

        # keep only the coordinates columns in them
        for folder in zip(CSV_FILES_LOCATION, SESSION_DATE):
            self.dataframe_data.clear()
            CSV_files = glob.glob(f"{folder[0]}\\*.csv")
            for file in CSV_files:
                # Read every .CSV file in the folder
                read_file = pd.read_csv(file)
                new_file = read_file[KEEP_COL]
                self.dataframe_data.append(new_file)

            self.df = pd.concat(self.dataframe_data, ignore_index=True)
            self.clean_dataframe()
            self.convert_to_CSV(folder[1])
            self.convert_to_GPX(folder[1])

    def clean_dataframe(self):
        """Remove duplication from the table."""
        old_count = self.df.shape[0]
        self.df = self.df.drop_duplicates()
        print(
            f"Removed the duplicates in the data from {old_count} to {self.df.shape[0]}"
        )

    def convert_to_CSV(self, session_data):
        self.merged_csv_files = f"{session_data}\\resultant_{session_data}.csv"
        MERGED_CSV_FILES_LOCATION.append(return_absolute_path(self.merged_csv_files))
        self.df.to_csv(MERGED_CSV_FILES_LOCATION[-1], index=False)
        print(f"CSV file saved as {self.merged_csv_files}")

    def convert_to_GPX(self, session_data):
        gpx_file_name = f"{session_data}.gpx"
        Converter(input_file=MERGED_CSV_FILES_LOCATION[-1]).csv_to_gpx(
            lats_colname=KEEP_COL[0],
            longs_colname=KEEP_COL[1],
            output_file=return_absolute_path(gpx_file_name),
        )
        print(f"GPX file saved as {gpx_file_name}")


class PlotMap:
    """Create a map with the points from training sessions in it."""

    def create_marker(self, row, map_obj):
        """Add markers on top of the points that are plotted on the map

        Args:
            row (dataframe): A dataframe that is passed as row with x and y coordinates in it
        """
        folium.Marker(location=[row["x_coord"], row["y_coord"]]).add_to(map_obj)

    def plot_map(self):
        for file in zip(MERGED_CSV_FILES_LOCATION, SESSION_DATE):
            dataframe = pd.read_csv(file[0])
            latitude = dataframe[KEEP_COL[1]]
            longitude = dataframe[KEEP_COL[0]]
            # Create a map object
            map_obj = folium.Map(
                location=[longitude.mean(), latitude.mean()],
                zoom_start=12,
                max_zoom=22,
            )

            # Apply the create_marker function to each 10th row
            dataframe.iloc[::40].apply(self.create_marker, axis=1, args=(map_obj,))

            # Create a 2D list from the two columns
            coordinates = [
                [column1, column2]
                for column1, column2 in zip(longitude.tolist(), latitude.tolist())
            ]

            self.draw_map_line(map_obj, coordinates)

            # Save the map to an HTML file
            training_map_folder = CURRENT_DIRECTORY + "/training_maps"
            map_path = os.path.join(training_map_folder, f"{file[1]}.html")
            os.makedirs(os.path.dirname(map_path), exist_ok=True)
            map_obj.save(map_path)
            print(f"created the training route of session {file[1]}")

    def draw_map_line(self, map_obj, coordinates):
        """Draw line between the points that are plotted on the map

        Args:
            map_obj: A Created map with Folium and Leaflet.js
            coordinates (list [int]): 2D list with x and y coordinates for the training session
        """
        folium.PolyLine(
            locations=coordinates, color="blue", weight=2.5, opacity=1
        ).add_to(map_obj)


class MapFolder:
    def move_folder(self):
        """Copy the map .HTML file from the '/plot_training_sessions_map' folder to the static folder, to be discoverable by Flask"""
        source_dir = CURRENT_DIRECTORY + "/training_maps"
        target_dir = CURRENT_DIRECTORY + "/../static/training_maps"

        file_names = os.listdir(source_dir)
        try:
            os.makedirs(target_dir)
        except OSError:
            # The directory already existed, nothing to do
            pass
        for file_name in file_names:
            shutil.copy(os.path.join(source_dir, file_name), target_dir)
        print("moved the map folder successfully")


def main():
    FindCSV().extract_files_by_extension()
    ProcessCSVtoGPX().create_resultant_CSV()
    PlotMap().plot_map()
    MapFolder().move_folder()
    return SESSION_DATE


if __name__ == "__main__":
    main()
