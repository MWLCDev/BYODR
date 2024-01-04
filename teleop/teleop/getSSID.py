import paramiko


def fetch_ssid(host, port, username, password, command):
    # Create an SSH client instance
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Connect to the SSH server
    client.connect(host, port, username, password)
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode("utf-8")
    client.close()
    return output
