import os
import subprocess
import time

# Environment variables for MongoDB credentials
mongo_user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
mongo_pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "robot")


# Function to start MongoDB
def start_mongo(auth=False):
    try:
        # Start MongoDB with or without authentication
        command = ["mongod", "--bind_ip_all"]
        if auth:
            command.append("--auth")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"MongoDB started {'with' if auth else 'without'} authentication.")
        return process
    except Exception as e:
        print(f"Failed to start MongoDB: {e}")
        return None


# Function to initialize MongoDB (create admin user)
def init_mongo():
    time.sleep(5)  # Wait for MongoDB to start up
    try:
        # Create admin user
        subprocess.run(["mongo", "admin", "--eval", f'db.createUser({{user: "{mongo_user}", pwd: "{mongo_pass}", roles:[{{role:"root", db:"admin"}}]}});'])
        print("MongoDB initialized with admin user.")
    except Exception as e:
        print(f"Failed to initialize MongoDB: {e}")


if __name__ == "__main__":
    # Start MongoDB without authentication
    mongo_process = start_mongo(auth=False)

    if mongo_process:
        init_mongo()

        # Terminate the initial MongoDB process
        mongo_process.terminate()
        mongo_process.wait()

        # Start MongoDB with authentication enabled
        mongo_process = start_mongo(auth=True)

        if mongo_process:
            # Keep the script running to ensure MongoDB stays alive
            try:
                while True:
                    time.sleep(10)  # Adjust this as needed
            except KeyboardInterrupt:
                print("Shutting down MongoDB.")
                mongo_process.terminate()
                mongo_process.wait()
        else:
            print("MongoDB did not restart with authentication. Exiting.")
    else:
        print("MongoDB did not start initially. Exiting.")
