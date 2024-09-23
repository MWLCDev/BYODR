import os
import subprocess
import time
import json

# Environment variables for MongoDB credentials
mongo_user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
mongo_pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "robot")


# Function to start MongoDB and filter logs
def start_mongo(auth=False):
    try:
        command = ["mongod", "--bind_ip_all"]
        if auth:
            command.append("--auth")

        # Use Popen to capture output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        print(f"MongoDB started {'with' if auth else 'without'} authentication.")

        # Continuously read and filter the output
        for line in process.stdout:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get("s") in ["W", "E"]:  # 'W' for warnings, 'E' for errors
                    print(f"[{log_entry['s']}] {log_entry['msg']}")
            except json.JSONDecodeError:
                # If it's not JSON, print if it looks like a warning or error
                if "warning" in line.lower() or "error" in line.lower():
                    print(line.strip())

        return process
    except Exception as e:
        print(f"Failed to start MongoDB: {e}")
        return None


# Function to initialize MongoDB (create admin user)
def init_mongo():
    time.sleep(10)  # Wait for MongoDB to start up
    try:
        # Create admin user
        subprocess.run(["mongo", "admin", "--eval", f'db.createUser({{user: "{mongo_user}", pwd: "{mongo_pass}", roles:[{{role:"root", db:"admin"}}]}});'])
        print("MongoDB initialized with admin user.")
    except Exception as e:
        print(f"Failed to initialize MongoDB: {e}")


if __name__ == "__main__":
    # Start MongoDB with authentication enabled from the beginning
    mongo_process = start_mongo(auth=True)
    if mongo_process:
        init_mongo()
        # Keep the script running to ensure MongoDB stays alive
        try:
            mongo_process.wait()
        except KeyboardInterrupt:
            print("Shutting down MongoDB.")
            mongo_process.terminate()
