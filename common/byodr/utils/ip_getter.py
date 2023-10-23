# This code reads the config file located in the directory below.
# From this directory we can get the IP number of the router, and therefore, all the devices below it.
import configparser




def get_ip_number():
    config = configparser.ConfigParser()

    # Read the file that contains the IP format of the robot
    config.read("/config/config.ini")

    # Locate the line with the front camera IP of the robot
    front_camera_ip = config["camera"]["front.camera.ip"]

    # We break the string on places where it has a '.'
    parts = front_camera_ip.split('.')
    

    # We are interested in the 3rd number of the IP => 192.168.33.64, we are interested in the 33
    return parts[2]    
