import os
import zipfile
import glob
import pandas as pd
from gpx_converter import Converter
import glob
import folium
import pandas as pd

df = pd.read_csv("newFile.csv")

LATI = df["y_coord"]
LONG = df["x_coord"]

# columns that will be used in the .GPX file and the resultant .CSV files
KEEP_COL = ["x_coord", "y_coord", "vehicle_conf"]
# The Resultant file with all the rows from a training session made in a day
MERGED_CSV_FILES = "newFile.csv"

GPX_FILE = "output.gpx"
# Main list to have all the .CSV files as their own list in the training session folder
L = []

# Get all the compressed files in a folder
ZIP_FILES = glob.glob(".\\usedMaterial\\**\\*.{}".format("zip"), recursive=True)

class FindCSV():
    """Find the .ZIP compressed folder and get the .CSV from it 
    then move them to a folder with the name being the date of training session "2023Apr06"
    """
    def extract_files_by_extension():
        for file in ZIP_FILES:
            # To get the date only from the CSV file
            destination_path = os.path.basename(file)[:9]
            # Create a folder with the date of the sessions
            if not os.path.exists(destination_path):
                os.makedirs(destination_path)
            with zipfile.ZipFile(file, "r") as zip_ref:
                # Get all the files in the chosen compressed file
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith(".csv"):
                        extracted_path = zip_ref.extract(file_info, path=destination_path)
                        new_file_path = os.path.join(destination_path, file_info.filename)
                        os.rename(extracted_path, new_file_path)


class ProcessCSVtoGPX:
    """Make one (cleaned) .CSV file that will have all the data in it.
    """
    def __init__(self):
        self.df = ""

    def create_resultant_CSV(self):
        """Create a main .CSV file that will have data from all the .CSV that are founded in a training session."""
        # Make a list with all the founded .CSV files
        csv_files = glob.glob(".\\usedMaterial\\*.{}".format("csv"))

        # keep only the coordinates columns in them
        for file in csv_files:
            # Read every file in the folder
            read_file = pd.read_csv(file)
            new_file = read_file[KEEP_COL]
            L.append(new_file)

        self.df = pd.concat(L, ignore_index=True)
        # self.clean_dataframe()

    def clean_dataframe(self):
        """Remove duplication from the table."""
        old_count = self.df.shape[0]
        self.df = self.df.drop_duplicates()
        print(
            f"Removed the duplicates from the data from {old_count} to {self.df.shape[0]}"
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
    """Create a map with the points from training sessions in it.
    """
    def __init__(self, map_name):
        self.map_name = map_name

    def create_marker(self, row, map_obj):
        """Add markers on top of the points that are plotted on the map

        Args:
            row (dataframe): A dataframe that is passed as row with x and y coordinates in it
        """
        folium.Marker(location=[row["x_coord"], row["y_coord"]]).add_to(map_obj)

    def plot_map(self):
        # Create a map object
        map_obj = folium.Map(
            location=[LONG.mean(), LATI.mean()], zoom_start=12, max_zoom=22
        )

        # Add markers for the points
        # Apply the create_marker function to each 10th row
        df.iloc[::10].apply(self.create_marker, axis=1, args=(map_obj,))

        # Create a 2D list from the two columns
        coordinates = [
            [column1, column2] for column1, column2 in zip(LONG.tolist(), LATI.tolist())
        ]

        # Draw line between the points
        folium.PolyLine(
            locations=coordinates, color="blue", weight=2.5, opacity=1
        ).add_to(map_obj)

        # Save the map to an HTML file
        map_obj.save(self.map_name)


FindCSV().extract_files_by_extension()

ProcessCSVtoGPX().run_all()

PlotMap().plot_map()
